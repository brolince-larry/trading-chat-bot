"""Multi-pair scanner: runs every strategy against every configured symbol
and returns a ranked list of candidates. This is the module that answers
"which pairs currently have valid setups?" — the chatbot never picks a pair
on its own, it calls this and explains the result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from app.domain.analysis.timeframe_analysis import compute_timeframe_analysis
from app.domain.market.data_provider import MarketDataProvider
from app.domain.market.models import Timeframe
from app.domain.market.symbols import get_symbol
from app.domain.risk.exposure import CurrencyExposure, PositionExposure, calculate_currency_exposure
from app.domain.scanner.scoring import score_setup
from app.domain.strategies import ALL_STRATEGIES
from app.domain.strategies.base import SetupStatus, Strategy, TradeSetup

DEFAULT_HIGHER_TIMEFRAME = Timeframe.H4
DEFAULT_ENTRY_TIMEFRAME = Timeframe.H1
DEFAULT_LOOKBACK_CANDLES = 260


@dataclass(frozen=True, slots=True)
class ScannedCandidate:
    setup: TradeSetup
    quality_score: int
    higher_timeframe: Timeframe
    entry_timeframe: Timeframe
    spread_pips: Decimal | None


@dataclass(frozen=True, slots=True)
class SkippedSymbol:
    symbol: str
    reason: str


@dataclass(frozen=True, slots=True)
class ScanResult:
    scanned_at: datetime
    symbols_scanned: int
    candidates: list[ScannedCandidate] = field(default_factory=list)
    skipped: list[SkippedSymbol] = field(default_factory=list)
    currency_exposure: list[CurrencyExposure] = field(default_factory=list)


class PairScanner:
    def __init__(
        self,
        market_data_provider: MarketDataProvider,
        strategies: list[Strategy] | None = None,
        higher_timeframe: Timeframe = DEFAULT_HIGHER_TIMEFRAME,
        entry_timeframe: Timeframe = DEFAULT_ENTRY_TIMEFRAME,
        lookback_candles: int = DEFAULT_LOOKBACK_CANDLES,
        min_quality_score: int = 0,
    ) -> None:
        self._provider = market_data_provider
        self._strategies = strategies or ALL_STRATEGIES
        self._higher_timeframe = higher_timeframe
        self._entry_timeframe = entry_timeframe
        self._lookback_candles = lookback_candles
        self._min_quality_score = min_quality_score

    def scan(self, symbols: list[str]) -> ScanResult:
        candidates: list[ScannedCandidate] = []
        skipped: list[SkippedSymbol] = []

        for symbol in symbols:
            try:
                symbol_candidates = self._scan_symbol(symbol)
            except ValueError as exc:
                skipped.append(SkippedSymbol(symbol=symbol, reason=str(exc)))
                continue
            candidates.extend(symbol_candidates)

        candidates.sort(key=lambda c: c.quality_score, reverse=True)

        exposure_inputs = [
            PositionExposure(symbol=c.setup.symbol, direction=c.setup.direction)
            for c in candidates
            if c.setup.status is SetupStatus.CONFIRMED
        ]

        return ScanResult(
            scanned_at=datetime.now(UTC),
            symbols_scanned=len(symbols),
            candidates=candidates,
            skipped=skipped,
            currency_exposure=calculate_currency_exposure(exposure_inputs),
        )

    def _scan_symbol(self, symbol: str) -> list[ScannedCandidate]:
        higher_candles = self._provider.get_candles(symbol, self._higher_timeframe, self._lookback_candles)
        entry_candles = self._provider.get_candles(symbol, self._entry_timeframe, self._lookback_candles)

        higher_analysis = compute_timeframe_analysis(symbol, self._higher_timeframe, higher_candles)
        entry_analysis = compute_timeframe_analysis(symbol, self._entry_timeframe, entry_candles)

        spread_pips: Decimal | None = None
        try:
            price = self._provider.get_price(symbol)
            spread_pips = self._spread_in_pips(symbol, price.spread)
        except Exception:  # noqa: BLE001 - a missing live price must never abort a scan
            spread_pips = None

        results: list[ScannedCandidate] = []
        for strategy in self._strategies:
            setup = strategy.analyze(higher_analysis, entry_analysis)
            if not setup.is_actionable:
                continue
            score = score_setup(setup, higher_analysis, entry_analysis, spread_pips)
            if score < self._min_quality_score:
                continue
            results.append(
                ScannedCandidate(
                    setup=setup,
                    quality_score=score,
                    higher_timeframe=self._higher_timeframe,
                    entry_timeframe=self._entry_timeframe,
                    spread_pips=spread_pips,
                )
            )
        return results

    @staticmethod
    def _spread_in_pips(symbol: str, spread: Decimal) -> Decimal:
        return spread / get_symbol(symbol).pip_size
