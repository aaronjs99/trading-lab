from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AllocationSignal:
    action: str
    max_tqqq_allocation: float
    max_spy_allocation: float
    reason: str


def display_action(action: str, traded_symbol: str = "TQQQ", core_symbol: str = "SPY") -> str:
    traded = traded_symbol.upper()
    core = core_symbol.upper()
    return (
        action.replace("TQQQ", traded)
        .replace("SPY_CORE", f"{core}_CORE")
    )


def recommend_allocation(
    rf_probability: float,
    qqq_uptrend: bool,
    qqq_dist_ma20: float,
    qqq_dist_ma50: float,
    tqqq_drawdown_20d: float,
    traded_symbol: str = "TQQQ",
    benchmark_symbol: str = "QQQ",
    core_symbol: str = "SPY",
) -> AllocationSignal:
    """Convert market/model state into simple max allocation guidance.

    This is not live trading advice. It is a deterministic research rule for
    translating model outputs into a constrained sizing recommendation.
    """

    traded = traded_symbol.upper()
    benchmark = benchmark_symbol.upper()
    core = core_symbol.upper()

    if not qqq_uptrend:
        return AllocationSignal(
            action="DEFENSIVE_OR_CASH",
            max_tqqq_allocation=0.0,
            max_spy_allocation=0.25,
            reason=f"{benchmark} is not in 20/50 uptrend.",
        )

    if qqq_dist_ma20 > 0.05 or qqq_dist_ma50 > 0.10:
        return AllocationSignal(
            action="WAIT_FOR_PULLBACK",
            max_tqqq_allocation=0.05,
            max_spy_allocation=0.50,
            reason=f"Uptrend exists, but {benchmark} is extended above moving averages.",
        )

    if rf_probability >= 0.65 and tqqq_drawdown_20d <= -0.03:
        return AllocationSignal(
            action="TACTICAL_TQQQ_BUY_ALLOWED",
            max_tqqq_allocation=0.30,
            max_spy_allocation=0.60,
            reason=f"Model probability is strong and {traded} has pulled back from recent high.",
        )

    if rf_probability >= 0.60:
        return AllocationSignal(
            action="SMALL_TQQQ_ALLOWED",
            max_tqqq_allocation=0.15,
            max_spy_allocation=0.60,
            reason="Model probability is moderately positive.",
        )

    return AllocationSignal(
        action="SPY_CORE_ONLY_OR_WAIT",
        max_tqqq_allocation=0.05,
        max_spy_allocation=0.60,
        reason=f"{core} core only or wait: trend may be positive, but model probability is weak or setup is not clean.",
    )
