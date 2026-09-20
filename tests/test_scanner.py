from __future__ import annotations

from datetime import datetime

from app.domain.market.models import Candle, Timeframe
from app.domain.scanner.pair_scanner import PairScanner
from app.infrastructure.market_data.simulated import SimulatedMarketDataProvider


def test_pair_scanner_runs_against_simulated_provider_end_to_end():
    provider = SimulatedMarketDataProvider(seed=1)
    scanner = PairScanner(market_data_provider=provider)

    result = scanner.scan(["EUR_USD", "GBP_USD", "USD_JPY"])

    assert isinstance(result.scanned_at, datetime)
    assert result.symbols_scanned == 3
    assert result.skipped == []  # simulated provider always returns enough candles
    for candidate in result.candidates:
        assert 0 <= candidate.quality_score <= 100
        assert candidate.setup.is_actionable

    # Candidates should be sorted by descending quality score.
    scores = [c.quality_score for c in result.candidates]
    assert scores == sorted(scores, reverse=True)


def test_pair_scanner_is_deterministic_for_a_fixed_seed():
    scanner_a = PairScanner(market_data_provider=SimulatedMarketDataProvider(seed=7))
    scanner_b = PairScanner(market_data_provider=SimulatedMarketDataProvider(seed=7))

    result_a = scanner_a.scan(["EUR_USD"])
    result_b = scanner_b.scan(["EUR_USD"])

    assert [(c.setup.symbol, c.setup.strategy_name, c.quality_score) for c in result_a.candidates] == [
        (c.setup.symbol, c.setup.strategy_name, c.quality_score) for c in result_b.candidates
    ]


class _FailingProvider:
    def get_candles(self, symbol: str, timeframe: Timeframe, count: int) -> list[Candle]:
        if symbol == "EUR_USD":
            raise ValueError("not enough history")
        return SimulatedMarketDataProvider(seed=3).get_candles(symbol, timeframe, count)

    def get_price(self, symbol: str):
        return SimulatedMarketDataProvider(seed=3).get_price(symbol)


def test_pair_scanner_skips_symbols_that_fail_without_aborting_the_whole_scan():
    scanner = PairScanner(market_data_provider=_FailingProvider())

    result = scanner.scan(["EUR_USD", "GBP_USD"])

    assert len(result.skipped) == 1
    assert result.skipped[0].symbol == "EUR_USD"
    assert result.symbols_scanned == 2
