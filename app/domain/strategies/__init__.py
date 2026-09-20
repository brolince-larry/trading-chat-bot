from app.domain.strategies.base import Direction, SetupStatus, Strategy, TakeProfitLevel, TradeSetup
from app.domain.strategies.breakout_retest import BreakoutRetestStrategy
from app.domain.strategies.range_reversion import RangeReversionStrategy
from app.domain.strategies.trend_pullback import TrendPullbackStrategy

ALL_STRATEGIES: list[Strategy] = [
    TrendPullbackStrategy(),
    BreakoutRetestStrategy(),
    RangeReversionStrategy(),
]

__all__ = [
    "ALL_STRATEGIES",
    "BreakoutRetestStrategy",
    "Direction",
    "RangeReversionStrategy",
    "SetupStatus",
    "Strategy",
    "TakeProfitLevel",
    "TradeSetup",
    "TrendPullbackStrategy",
]
