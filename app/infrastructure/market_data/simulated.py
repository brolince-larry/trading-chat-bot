"""Deterministic synthetic market data for local development and tests.

This is NOT a market simulator or backtesting price model — it produces
plausible-looking OHLC series (seeded per symbol+timeframe, so results are
reproducible) so the API, scanner, and UI can be exercised end to end
without a live broker connection. Swap in ``OandaMarketDataProvider`` (or an
MT5 equivalent) for real prices.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.domain.market.models import Candle, Price, SymbolSpec, Timeframe
from app.domain.market.symbols import get_symbol

_BASE_PRICES: dict[str, Decimal] = {
    "EUR_USD": Decimal("1.0850"),
    "GBP_USD": Decimal("1.2650"),
    "USD_JPY": Decimal("149.50"),
    "USD_CHF": Decimal("0.8800"),
    "AUD_USD": Decimal("0.6550"),
    "USD_CAD": Decimal("1.3550"),
    "NZD_USD": Decimal("0.6050"),
    "EUR_GBP": Decimal("0.8580"),
    "EUR_JPY": Decimal("162.00"),
    "GBP_JPY": Decimal("189.00"),
    "AUD_JPY": Decimal("98.00"),
}

_TYPICAL_SPREAD_PIPS: dict[str, Decimal] = {
    "EUR_USD": Decimal("1.0"),
    "GBP_USD": Decimal("1.4"),
    "USD_JPY": Decimal("1.2"),
    "USD_CHF": Decimal("1.8"),
    "AUD_USD": Decimal("1.4"),
    "USD_CAD": Decimal("1.8"),
    "NZD_USD": Decimal("2.0"),
    "EUR_GBP": Decimal("1.6"),
    "EUR_JPY": Decimal("2.0"),
    "GBP_JPY": Decimal("2.8"),
    "AUD_JPY": Decimal("2.4"),
}


class SimulatedMarketDataProvider:
    """Implements :class:`app.domain.market.data_provider.MarketDataProvider`."""

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed

    def get_candles(self, symbol: str, timeframe: Timeframe, count: int) -> list[Candle]:
        spec = get_symbol(symbol)
        rng = random.Random(f"{self._seed}:{symbol}:{timeframe.value}")

        volatility_pips = self._volatility_pips(timeframe)
        drift_pips = rng.uniform(-0.15, 0.15) * volatility_pips
        precision = self._decimal_places(spec)

        interval = timedelta(minutes=timeframe.minutes)
        now = datetime.now(UTC).replace(second=0, microsecond=0)
        start_time = now - interval * count

        candles: list[Candle] = []
        current_open = _BASE_PRICES[spec.name]

        for i in range(count):
            timestamp = start_time + interval * i
            body_pips = rng.gauss(drift_pips, volatility_pips)
            close = current_open + Decimal(str(body_pips)) * spec.pip_size

            wick_up_pips = abs(rng.gauss(0, volatility_pips * 0.4))
            wick_down_pips = abs(rng.gauss(0, volatility_pips * 0.4))
            high = max(current_open, close) + Decimal(str(wick_up_pips)) * spec.pip_size
            low = min(current_open, close) - Decimal(str(wick_down_pips)) * spec.pip_size

            candles.append(
                Candle(
                    symbol=spec.name,
                    timeframe=timeframe,
                    timestamp=timestamp,
                    open=self._quantize(current_open, precision),
                    high=self._quantize(high, precision),
                    low=self._quantize(low, precision),
                    close=self._quantize(close, precision),
                    volume=Decimal(str(rng.randint(50, 500))),
                )
            )
            current_open = close

        return candles

    def get_price(self, symbol: str) -> Price:
        spec = get_symbol(symbol)
        last_candle = self.get_candles(symbol, Timeframe.M1, 1)[0]
        spread = _TYPICAL_SPREAD_PIPS[spec.name] * spec.pip_size
        half_spread = spread / 2
        return Price(
            symbol=spec.name,
            bid=last_candle.close - half_spread,
            ask=last_candle.close + half_spread,
            timestamp=datetime.now(UTC),
        )

    @staticmethod
    def _volatility_pips(timeframe: Timeframe) -> float:
        return {
            Timeframe.M1: 1.5,
            Timeframe.M5: 3.0,
            Timeframe.M15: 5.0,
            Timeframe.M30: 7.0,
            Timeframe.H1: 9.0,
            Timeframe.H4: 18.0,
            Timeframe.D1: 45.0,
        }[timeframe]

    @staticmethod
    def _decimal_places(spec: SymbolSpec) -> int:
        return 3 if spec.is_jpy_quote else 5

    @staticmethod
    def _quantize(value: Decimal, places: int) -> Decimal:
        exponent = Decimal("1").scaleb(-places)
        return value.quantize(exponent, rounding=ROUND_HALF_UP)
