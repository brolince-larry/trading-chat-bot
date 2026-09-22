"""Bar-by-bar walk-forward backtest.

Walks historical entry-timeframe candles one at a time, at each step
computing the same ``TimeframeAnalysis`` a live scan would see and calling
the strategy's real ``analyze()``. A confirmed setup opens exactly one
position (sized by the real risk engine, compounding against the running
balance); subsequent bars are checked bar-range-by-bar-range against the
stop-loss/take-profit until one is hit, exactly like the live position
monitor's logic but against historical OHLC ranges instead of live ticks.

No lookahead bias: at step ``i`` only entry candles up to and including
``i``, and higher-timeframe candles up to that bar's timestamp, are ever
visible to the strategy.

Known simplification, stated plainly rather than silently assumed: no
spread or slippage is modeled (this reuses the same historical/simulated
candles the rest of the app uses, which don't carry a historical spread
series), and a bar whose range touches both the stop and the target in
the same bar is conservatively resolved as the stop being hit first.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.domain.analysis.timeframe_analysis import (
    MIN_CANDLES_REQUIRED,
    compute_timeframe_analysis,
)
from app.domain.backtest.models import (
    BacktestResult,
    BacktestTrade,
    EquityPoint,
    ExitReason,
)
from app.domain.market.data_provider import MarketDataProvider
from app.domain.market.models import Candle, SymbolSpec, Timeframe
from app.domain.market.symbols import get_symbol
from app.domain.risk.decimal_utils import to_plain
from app.domain.risk.position_sizing import calculate_position_size
from app.domain.strategies.base import Direction, SetupStatus, Strategy

ANALYSIS_WINDOW = 260
MAX_ENTRY_BARS = 3000


class BacktestError(Exception):
    pass


def run_backtest(
    *,
    provider: MarketDataProvider,
    symbol: str,
    strategy: Strategy,
    higher_timeframe: Timeframe = Timeframe.H4,
    entry_timeframe: Timeframe = Timeframe.H1,
    lookback_candles: int = 500,
    starting_balance: Decimal = Decimal(10000),
    risk_percent: Decimal = Decimal("1.0"),
    account_currency: str = "USD",
    quote_to_account_rate: Decimal | None = None,
) -> BacktestResult:
    if lookback_candles < MIN_CANDLES_REQUIRED + 10:
        raise BacktestError(f"lookback_candles must be at least {MIN_CANDLES_REQUIRED + 10}.")
    if lookback_candles > MAX_ENTRY_BARS:
        raise BacktestError(f"lookback_candles cannot exceed {MAX_ENTRY_BARS}.")

    spec = get_symbol(symbol)
    if spec.quote_currency != account_currency and quote_to_account_rate is None:
        raise BacktestError(
            f"{symbol}'s quote currency ({spec.quote_currency}) differs from the account "
            f"currency ({account_currency}) — provide quote_to_account_rate to size trades."
        )
    entry_total = lookback_candles + ANALYSIS_WINDOW
    higher_total = (
        int(entry_total * entry_timeframe.minutes / higher_timeframe.minutes) + ANALYSIS_WINDOW
    )

    entry_candles = provider.get_candles(symbol, entry_timeframe, entry_total)
    higher_candles = provider.get_candles(symbol, higher_timeframe, higher_total)
    if len(entry_candles) < MIN_CANDLES_REQUIRED or len(higher_candles) < MIN_CANDLES_REQUIRED:
        raise BacktestError("Not enough historical candles were returned to run a backtest.")

    balance = starting_balance
    peak_balance = starting_balance
    max_drawdown = Decimal(0)
    trades: list[BacktestTrade] = []
    equity_curve: list[EquityPoint] = [EquityPoint(timestamp=entry_candles[0].timestamp, balance=balance)]

    open_trade: _OpenTrade | None = None
    higher_idx = 0
    start_index = len(entry_candles) - lookback_candles

    for i in range(max(start_index, MIN_CANDLES_REQUIRED - 1), len(entry_candles)):
        bar = entry_candles[i]

        while higher_idx < len(higher_candles) and higher_candles[higher_idx].timestamp <= bar.timestamp:
            higher_idx += 1

        if open_trade is not None:
            exit_price, exit_reason = _check_exit(bar, open_trade)
            if exit_price is not None:
                trade, balance = _close_trade(open_trade, exit_price, exit_reason, bar, i, balance, spec)
                trades.append(trade)
                peak_balance = max(peak_balance, balance)
                drawdown = (peak_balance - balance) / peak_balance * 100 if peak_balance > 0 else Decimal(0)
                max_drawdown = max(max_drawdown, drawdown)
                equity_curve.append(EquityPoint(timestamp=bar.timestamp, balance=balance))
                open_trade = None
            continue

        entry_window = entry_candles[max(0, i - ANALYSIS_WINDOW + 1) : i + 1]
        higher_window = higher_candles[max(0, higher_idx - ANALYSIS_WINDOW) : higher_idx]
        if len(entry_window) < MIN_CANDLES_REQUIRED or len(higher_window) < MIN_CANDLES_REQUIRED:
            continue

        try:
            higher_analysis = compute_timeframe_analysis(symbol, higher_timeframe, higher_window)
            entry_analysis = compute_timeframe_analysis(symbol, entry_timeframe, entry_window)
        except ValueError:
            continue

        setup = strategy.analyze(higher_analysis, entry_analysis)
        if (
            setup.status is not SetupStatus.CONFIRMED
            or setup.direction is Direction.NONE
            or setup.entry_price is None
            or setup.stop_loss is None
        ):
            continue

        entry_price = Decimal(str(setup.entry_price))
        stop_loss = Decimal(str(setup.stop_loss))
        take_profit = Decimal(str(setup.take_profits[0].price)) if setup.take_profits else None

        sizing = calculate_position_size(
            account_balance=balance,
            risk_percent=risk_percent,
            entry_price=entry_price,
            stop_loss_price=stop_loss,
            symbol=spec,
            account_currency=account_currency,
            quote_to_account_rate=quote_to_account_rate,
        )
        if not sizing.meets_minimum_lot:
            continue

        open_trade = _OpenTrade(
            direction=setup.direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            units=sizing.units,
            pip_value_per_unit=sizing.pip_value_per_unit,
            entered_at=bar.timestamp,
            entered_index=i,
        )

    if open_trade is not None:
        last_bar = entry_candles[-1]
        trade, balance = _close_trade(
            open_trade,
            last_bar.close,
            ExitReason.END_OF_DATA,
            last_bar,
            len(entry_candles) - 1,
            balance,
            spec,
        )
        trades.append(trade)
        peak_balance = max(peak_balance, balance)
        drawdown = (peak_balance - balance) / peak_balance * 100 if peak_balance > 0 else Decimal(0)
        max_drawdown = max(max_drawdown, drawdown)
        equity_curve.append(EquityPoint(timestamp=last_bar.timestamp, balance=balance))

    return _summarize(
        symbol=symbol,
        strategy_name=strategy.name,
        higher_timeframe=higher_timeframe,
        entry_timeframe=entry_timeframe,
        starting_balance=starting_balance,
        ending_balance=balance,
        max_drawdown_percent=max_drawdown,
        trades=trades,
        equity_curve=equity_curve,
    )


class _OpenTrade:
    def __init__(
        self,
        *,
        direction: Direction,
        entry_price: Decimal,
        stop_loss: Decimal,
        take_profit: Decimal | None,
        units: Decimal,
        pip_value_per_unit: Decimal,
        entered_at: datetime,
        entered_index: int,
    ) -> None:
        self.direction = direction
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.units = units
        self.pip_value_per_unit = pip_value_per_unit
        self.entered_at = entered_at
        self.entered_index = entered_index


def _check_exit(bar: Candle, trade: _OpenTrade) -> tuple[Decimal | None, ExitReason | None]:
    is_long = trade.direction is Direction.LONG
    hit_stop = bar.low <= trade.stop_loss if is_long else bar.high >= trade.stop_loss
    hit_target = trade.take_profit is not None and (
        bar.high >= trade.take_profit if is_long else bar.low <= trade.take_profit
    )
    # A bar whose range spans both levels can't be resolved from OHLC alone
    # (real intrabar order is unknown) — conservatively assume the stop was
    # touched first rather than crediting the more favorable outcome.
    if hit_stop:
        return trade.stop_loss, ExitReason.STOP_LOSS
    if hit_target:
        return trade.take_profit, ExitReason.TAKE_PROFIT
    return None, None


def _close_trade(
    trade: _OpenTrade,
    exit_price: Decimal,
    reason: ExitReason,
    bar: Candle,
    exit_index: int,
    balance: Decimal,
    spec: SymbolSpec,
) -> tuple[BacktestTrade, Decimal]:
    sign = Decimal(1) if trade.direction is Direction.LONG else Decimal(-1)
    price_change_pips = (exit_price - trade.entry_price) / spec.pip_size
    pnl = to_plain(price_change_pips * sign * trade.pip_value_per_unit * trade.units)

    risk = abs(trade.entry_price - trade.stop_loss)
    r_multiple = (
        ((exit_price - trade.entry_price) * sign / risk).quantize(Decimal("0.0001"))
        if risk > 0
        else Decimal(0)
    )

    record = BacktestTrade(
        direction=trade.direction,
        entry_price=trade.entry_price,
        stop_loss=trade.stop_loss,
        take_profit=trade.take_profit,
        exit_price=exit_price,
        exit_reason=reason,
        entered_at=trade.entered_at,
        exited_at=bar.timestamp,
        bars_held=exit_index - trade.entered_index,
        units=trade.units,
        pnl=pnl,
        r_multiple=r_multiple,
    )
    return record, to_plain(balance + pnl)


def _summarize(
    *,
    symbol: str,
    strategy_name: str,
    higher_timeframe: Timeframe,
    entry_timeframe: Timeframe,
    starting_balance: Decimal,
    ending_balance: Decimal,
    max_drawdown_percent: Decimal,
    trades: list[BacktestTrade],
    equity_curve: list[EquityPoint],
) -> BacktestResult:
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    r_multiples = [float(t.r_multiple) for t in trades]

    gross_profit = sum((t.pnl for t in wins), Decimal(0))
    gross_loss = abs(sum((t.pnl for t in losses), Decimal(0)))

    win_rate = len(wins) / len(trades) if trades else None
    average_r = sum(r_multiples) / len(r_multiples) if r_multiples else None
    profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else None
    total_return_percent = (
        float(to_plain((ending_balance - starting_balance) / starting_balance * 100))
        if starting_balance > 0
        else 0.0
    )

    return BacktestResult(
        symbol=symbol,
        strategy=strategy_name,
        higher_timeframe=higher_timeframe.value,
        entry_timeframe=entry_timeframe.value,
        starting_balance=starting_balance,
        ending_balance=ending_balance,
        total_return_percent=total_return_percent,
        total_trades=len(trades),
        win_count=len(wins),
        loss_count=len(losses),
        win_rate=win_rate,
        profit_factor=profit_factor,
        expectancy_r=average_r,
        average_r_multiple=average_r,
        max_drawdown_percent=float(max_drawdown_percent),
        largest_win=max((t.pnl for t in wins), default=None),
        largest_loss=min((t.pnl for t in losses), default=None),
        trades=trades,
        equity_curve=equity_curve,
    )
