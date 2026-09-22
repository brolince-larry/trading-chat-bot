"""OANDA v20 REST API market data adapter.

Implements :class:`app.domain.market.data_provider.MarketDataProvider`
against OANDA's practice/live REST API. Requires ``OANDA_API_KEY`` (and,
implicitly, network access to OANDA) to actually serve data — see
``app/config.py`` for how the API key is loaded. Credentials are read only
from settings/environment and are never logged or exposed to callers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import httpx

from app.domain.market.data_provider import MarketDataProvider
from app.domain.market.models import Candle, Price, Timeframe

_GRANULARITY_MAP: dict[Timeframe, str] = {
    Timeframe.M1: "M1",
    Timeframe.M5: "M5",
    Timeframe.M15: "M15",
    Timeframe.M30: "M30",
    Timeframe.H1: "H1",
    Timeframe.H4: "H4",
    Timeframe.D1: "D",
}

def _parse_oanda_timestamp(value: str) -> datetime:
    """OANDA timestamps are RFC3339 with up to nanosecond precision and a
    trailing 'Z' (e.g. ``2024-01-01T00:00:00.123456789Z``).
    ``datetime.fromisoformat`` handles 'Z' natively since Python 3.11 but
    only up to microsecond precision, so the fractional part is truncated
    first.
    """
    if "." in value:
        head, _, fraction_and_zone = value.partition(".")
        fraction = fraction_and_zone.rstrip("Z")[:6].ljust(6, "0")
        value = f"{head}.{fraction}Z"
    return datetime.fromisoformat(value)


_PRACTICE_BASE_URL = "https://api-fxpractice.oanda.com"
_LIVE_BASE_URL = "https://api-fxtrade.oanda.com"


class OandaMarketDataProvider(MarketDataProvider):
    def __init__(self, api_key: str, use_practice: bool = True, timeout_seconds: float = 10.0) -> None:
        if not api_key:
            raise ValueError("An OANDA API key is required to construct this provider.")
        self._client = httpx.Client(
            base_url=_PRACTICE_BASE_URL if use_practice else _LIVE_BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout_seconds,
        )

    def get_candles(self, symbol: str, timeframe: Timeframe, count: int) -> list[Candle]:
        granularity = _GRANULARITY_MAP[timeframe]
        response = self._client.get(
            f"/v3/instruments/{symbol}/candles",
            params={"granularity": granularity, "count": count, "price": "M"},
        )
        response.raise_for_status()
        payload = response.json()

        candles: list[Candle] = []
        for raw in payload.get("candles", []):
            if not raw.get("complete", False):
                continue
            mid = raw["mid"]
            candles.append(
                Candle(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=_parse_oanda_timestamp(raw["time"]),
                    open=Decimal(mid["o"]),
                    high=Decimal(mid["h"]),
                    low=Decimal(mid["l"]),
                    close=Decimal(mid["c"]),
                    volume=Decimal(str(raw.get("volume", 0))),
                )
            )
        return candles

    def get_price(self, symbol: str) -> Price:
        response = self._client.get("/v3/pricing", params={"instruments": symbol})
        response.raise_for_status()
        payload = response.json()
        prices = payload.get("prices", [])
        if not prices:
            raise ValueError(f"OANDA returned no pricing data for {symbol}")

        quote = prices[0]
        bid = Decimal(quote["closeoutBid"])
        ask = Decimal(quote["closeoutAsk"])
        return Price(symbol=symbol, bid=bid, ask=ask, timestamp=datetime.now(UTC))

    def close(self) -> None:
        self._client.close()
