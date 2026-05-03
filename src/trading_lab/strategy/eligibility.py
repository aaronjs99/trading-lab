from __future__ import annotations

from dataclasses import dataclass

from trading_lab.strategy.select import StrategySelection


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    reasons: list[str]


def check_strategy_eligibility(
    selection: StrategySelection,
    rf_probability: float,
    qqq_uptrend: bool,
    qqq_dist_ma20: float,
) -> EligibilityResult:
    reasons: list[str] = []

    if rf_probability >= selection.threshold:
        reasons.append(f"OK: RF probability {rf_probability:.3f} >= threshold {selection.threshold:.2f}")
    else:
        reasons.append(f"NO: RF probability {rf_probability:.3f} < threshold {selection.threshold:.2f}")

    if selection.require_trend:
        if qqq_uptrend:
            reasons.append("OK: QQQ trend required and current trend is true")
        else:
            reasons.append("NO: QQQ trend required but current trend is false")
    else:
        reasons.append("OK: QQQ trend not required")

    if selection.max_ext20 is None:
        reasons.append("OK: no QQQ 20DMA extension cap")
    elif qqq_dist_ma20 <= selection.max_ext20:
        reasons.append(
            f"OK: QQQ 20DMA extension {qqq_dist_ma20:.2%} <= cap {selection.max_ext20:.2%}"
        )
    else:
        reasons.append(
            f"NO: QQQ 20DMA extension {qqq_dist_ma20:.2%} > cap {selection.max_ext20:.2%}"
        )

    eligible = all(reason.startswith("OK:") for reason in reasons)
    return EligibilityResult(eligible=eligible, reasons=reasons)
