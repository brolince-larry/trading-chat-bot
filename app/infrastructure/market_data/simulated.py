"""Deterministic synthetic market data for local development and tests.

This is NOT a market simulator or backtesting price model — it produces
plausible-looking OHLC series (seeded per symbol, so results are
reproducible) so the API, scanner, and UI can be exercised end to end
without a live broker connection. Swap in ``OandaMarketDataProvider`` (or an
MT5 equivalent) for real prices.

Every timeframe and ``get_price()`` read from one shared per-symbol,
minute-resolution random walk, instead of each being regenerated
independently from scratch on every call (which — an earlier version of
this module did — produces a value that's a deterministic function of the
call's arguments alone and so never actually changes over time, defeating
the whole point of a "live" price feed). Each 1-minute step's increment is
seeded by its absolute minute number, so:

- The value at any given minute is always the same however/whenever it's
  queried (deterministic, reproducible for tests).
- Because real wall-clock time keeps advancing, the *current* minute keeps
  changing, so prices genuinely move between calls.
- Every timeframe for a symbol reads off the same underlying walk, so e.g.
  an H4 candle's close and the "live" price agree with each other instead
  of being two unrelated random sequences.
- Unlike sampling each point's marginal distribution independently (which
  is tempting via the random-walk reparameterization trick, but gives two
  nearby minutes almost as much variance as two far-apart ones), each
  minute's value is the running sum of correlated per-minute increments, so
  nearby points move by realistically small amounts and only drift further
  apart over longer spans.

The per-symbol walk is cached on the instance and extended incrementally
(only the newly-elapsed minutes are computed), so repeated calls stay cheap
even though the walk conceptually stretches back arbitrarily far.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from random import Random

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

# Standard deviation, in pips, of one minute's price change.
_VOLATILITY_PIPS_PER_MINUTE = 0.35
# Fixed-per-symbol directional bias applied to every minute's increment, so
# trends can form; kept small relative to volatility so it doesn't dominate
# over very long spans.
_MAX_DRIFT_PIPS_PER_MINUTE = 0.01


class SimulatedMarketDataProvider:
    """Implements :class:`app.domain.market.data_provider.MarketDataProvider`."""

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed
        self._walks: dict[str, dict[int, float]] = {}
        # A persistent per-symbol generator makes extending the walk forward
        # (the overwhelmingly common case) a single cheap .gauss() call per
        # new minute, instead of constructing a freshly-seeded Random per
        # minute — ~25x faster, which matters since a cold cache can need to
        # fill tens of thousands of minutes for a single request.
        self._forward_rngs: dict[str, Random] = {}

    def get_candles(self, symbol: str, timeframe: Timeframe, count: int) -> list[Candle]:
        spec = get_symbol(symbol)
        precision = self._decimal_places(spec)
        now_minute = self._minute_index(datetime.now(UTC))
        start_minute = now_minute - timeframe.minutes * count

        candles: list[Candle] = []
        prior_close = self._price_at_minute(spec, start_minute)

        for i in range(count):
            minute = start_minute + timeframe.minutes * (i + 1)
            open_ = prior_close
            close = self._price_at_minute(spec, minute)

            wick_rng = self._rng(spec.name, "wick", minute)
            bar_vol_pips = _VOLATILITY_PIPS_PER_MINUTE * timeframe.minutes**0.5
            wick_up = abs(wick_rng.gauss(0, bar_vol_pips * 0.4))
            wick_down = abs(wick_rng.gauss(0, bar_vol_pips * 0.4))
            high = max(open_, close) + Decimal(str(wick_up)) * spec.pip_size
            low = min(open_, close) - Decimal(str(wick_down)) * spec.pip_size

            candles.append(
                Candle(
                    symbol=spec.name,
                    timeframe=timeframe,
                    timestamp=datetime.fromtimestamp(minute * 60, tz=UTC),
                    open=self._quantize(open_, precision),
                    high=self._quantize(high, precision),
                    low=self._quantize(low, precision),
                    close=self._quantize(close, precision),
                    volume=Decimal(str(wick_rng.randint(50, 500))),
                )
            )
            prior_close = close

        return candles

    def get_price(self, symbol: str) -> Price:
        spec = get_symbol(symbol)
        mid = self._price_at_minute(spec, self._minute_index(datetime.now(UTC)))
        spread = _TYPICAL_SPREAD_PIPS[spec.name] * spec.pip_size
        half_spread = spread / 2
        precision = self._decimal_places(spec)
        return Price(
            symbol=spec.name,
            bid=self._quantize(mid - half_spread, precision),
            ask=self._quantize(mid + half_spread, precision),
            timestamp=datetime.now(UTC),
        )

    def _price_at_minute(self, spec: SymbolSpec, minute: int) -> Decimal:
        displacement_pips = self._walk_value(spec.name, minute)
        return _BASE_PRICES[spec.name] + Decimal(str(displacement_pips)) * spec.pip_size

    def _walk_value(self, symbol: str, minute: int) -> float:
        """Cumulative pip displacement of ``symbol``'s walk at ``minute``,
        computed as the running sum of per-minute increments. Extends the
        cached walk forward or backward from whichever end is closer,
        computing only the newly-needed steps.
        """
        walk = self._walks.get(symbol)
        if walk is None:
            walk = {minute: 0.0}
            self._walks[symbol] = walk
            return 0.0
        if minute in walk:
            return walk[minute]

        drift = self._drift_per_minute(symbol)
        latest = max(walk)
        earliest = min(walk)

        if minute > latest:
            rng = self._forward_rngs.setdefault(symbol, self._rng(symbol, "walk", 0))
            cumulative = walk[latest]
            for m in range(latest + 1, minute + 1):
                cumulative += rng.gauss(drift, _VOLATILITY_PIPS_PER_MINUTE)
                walk[m] = cumulative
        else:
            # Extending backward from an already-established point is rare
            # in practice (see module docstring on access order) and can't
            # reuse the forward generator's stream, so it falls back to a
            # slower but still-deterministic per-step seed.
            cumulative = walk[earliest]
            for m in range(earliest - 1, minute - 1, -1):
                cumulative -= self._rng(symbol, "step", m + 1).gauss(drift, _VOLATILITY_PIPS_PER_MINUTE)
                walk[m] = cumulative

        return walk[minute]

    def _drift_per_minute(self, symbol: str) -> float:
        return self._rng(symbol, "drift", 0).uniform(-_MAX_DRIFT_PIPS_PER_MINUTE, _MAX_DRIFT_PIPS_PER_MINUTE)

    def _rng(self, symbol: str, purpose: str, key: int) -> Random:
        return Random(f"{self._seed}:{symbol}:{purpose}:{key}")

    @staticmethod
    def _minute_index(timestamp: datetime) -> int:
        return int(timestamp.timestamp() // 60)

    @staticmethod
    def _decimal_places(spec: SymbolSpec) -> int:
        return 3 if spec.is_jpy_quote else 5

    @staticmethod
    def _quantize(value: Decimal, places: int) -> Decimal:
        exponent = Decimal(1).scaleb(-places)
        return value.quantize(exponent, rounding=ROUND_HALF_UP)
