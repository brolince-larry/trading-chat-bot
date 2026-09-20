from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.domain.scanner.pair_scanner import ScannedCandidate, ScanResult
from app.domain.strategies.base import Direction, SetupStatus, TradeSetup


class TakeProfitOut(BaseModel):
    price: float
    r_multiple: float


class TradeSetupOut(BaseModel):
    symbol: str
    strategy: str
    direction: Direction
    status: SetupStatus
    reason: str
    invalidation: str
    entry_price: float | None
    entry_trigger: str | None
    stop_loss: float | None
    take_profits: list[TakeProfitOut]
    risk_reward: float | None
    warnings: list[str]

    @classmethod
    def from_domain(cls, setup: TradeSetup) -> TradeSetupOut:
        return cls(
            symbol=setup.symbol,
            strategy=setup.strategy_name,
            direction=setup.direction,
            status=setup.status,
            reason=setup.reason,
            invalidation=setup.invalidation,
            entry_price=setup.entry_price,
            entry_trigger=setup.entry_trigger,
            stop_loss=setup.stop_loss,
            take_profits=[TakeProfitOut(price=tp.price, r_multiple=tp.r_multiple) for tp in setup.take_profits],
            risk_reward=setup.risk_reward,
            warnings=setup.warnings,
        )


class ScannedCandidateOut(BaseModel):
    setup: TradeSetupOut
    quality_score: int
    higher_timeframe: str
    entry_timeframe: str
    spread_pips: Decimal | None

    @classmethod
    def from_domain(cls, candidate: ScannedCandidate) -> ScannedCandidateOut:
        return cls(
            setup=TradeSetupOut.from_domain(candidate.setup),
            quality_score=candidate.quality_score,
            higher_timeframe=candidate.higher_timeframe.value,
            entry_timeframe=candidate.entry_timeframe.value,
            spread_pips=candidate.spread_pips,
        )


class SkippedSymbolOut(BaseModel):
    symbol: str
    reason: str


class CurrencyExposureOut(BaseModel):
    currency: str
    net_position_count: int
    level: str
    contributing_symbols: list[str]


class ScanResultOut(BaseModel):
    scanned_at: datetime
    symbols_scanned: int
    candidates: list[ScannedCandidateOut]
    skipped: list[SkippedSymbolOut]
    currency_exposure: list[CurrencyExposureOut]

    @classmethod
    def from_domain(cls, result: ScanResult) -> ScanResultOut:
        return cls(
            scanned_at=result.scanned_at,
            symbols_scanned=result.symbols_scanned,
            candidates=[ScannedCandidateOut.from_domain(c) for c in result.candidates],
            skipped=[SkippedSymbolOut(symbol=s.symbol, reason=s.reason) for s in result.skipped],
            currency_exposure=[
                CurrencyExposureOut(
                    currency=e.currency,
                    net_position_count=e.net_position_count,
                    level=e.level.value,
                    contributing_symbols=e.contributing_symbols,
                )
                for e in result.currency_exposure
            ],
        )
