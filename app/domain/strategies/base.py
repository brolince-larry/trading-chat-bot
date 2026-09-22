"""Strategy contract and the trade-setup value object every strategy returns.

Strategies are deterministic rule engines, not the LLM: given structured
market analysis, they either reject the pair, flag a developing setup that
still needs confirmation, or confirm one — always with an explicit
invalidation condition. Nothing here claims certainty; "confirmed" means
"this strategy's precise entry rule has fired," not "this will win."
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from app.domain.analysis.timeframe_analysis import TimeframeAnalysis


class SetupStatus(str, Enum):
    REJECTED = "rejected"
    WATCHING = "watching"
    CONFIRMED = "confirmed"
    INVALIDATED = "invalidated"


class Direction(str, Enum):
    LONG = "long"
    SHORT = "short"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class TakeProfitLevel:
    price: float
    r_multiple: float


@dataclass(frozen=True, slots=True)
class TradeSetup:
    symbol: str
    strategy_name: str
    direction: Direction
    status: SetupStatus
    reason: str
    invalidation: str
    entry_price: float | None = None
    entry_trigger: str | None = None
    stop_loss: float | None = None
    take_profits: list[TakeProfitLevel] = field(default_factory=list)
    risk_reward: float | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def is_actionable(self) -> bool:
        return self.status in (SetupStatus.WATCHING, SetupStatus.CONFIRMED)

    @classmethod
    def rejected(cls, symbol: str, strategy_name: str, reason: str) -> TradeSetup:
        return cls(
            symbol=symbol,
            strategy_name=strategy_name,
            direction=Direction.NONE,
            status=SetupStatus.REJECTED,
            reason=reason,
            invalidation="n/a",
        )


class Strategy(ABC):
    """Base class for a deterministic strategy module.

    Implementations receive already-computed :class:`TimeframeAnalysis`
    snapshots — they never touch raw broker data or call the LLM.
    """

    name: str

    @abstractmethod
    def analyze(
        self, higher_tf: TimeframeAnalysis, entry_tf: TimeframeAnalysis
    ) -> TradeSetup:
        """Evaluate one symbol using a higher (context) and entry timeframe."""
        raise NotImplementedError

    @staticmethod
    def build_take_profits(entry: float, stop_loss: float, direction: Direction) -> list[TakeProfitLevel]:
        risk = abs(entry - stop_loss)
        if risk <= 0:
            return []
        sign = 1 if direction is Direction.LONG else -1
        return [
            TakeProfitLevel(price=entry + sign * risk * 1.5, r_multiple=1.5),
            TakeProfitLevel(price=entry + sign * risk * 2.5, r_multiple=2.5),
        ]
