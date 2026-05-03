from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LadderOrder:
    level: str
    limit_price: float
    allocation_fraction: float
    reason: str


def build_tqqq_ladder(
    current_price: float,
    max_tqqq_allocation: float,
    action: str,
) -> list[LadderOrder]:
    """Build a simple traded-symbol dip-buy ladder from current price and max allocation.

    allocation_fraction is fraction of total account value, not fraction of cash.
    """

    if max_tqqq_allocation <= 0 or action in {"DEFENSIVE_OR_CASH"}:
        return []

    if action == "WAIT_FOR_PULLBACK":
        levels = [
            ("shallow_pullback", 0.97, 0.25, "Small starter only after a normal pullback."),
            ("medium_pullback", 0.94, 0.35, "Better risk/reward pullback."),
            ("deep_pullback", 0.90, 0.40, "Only allocate remaining capital on deeper weakness."),
        ]
    elif action == "TACTICAL_TQQQ_BUY_ALLOWED":
        levels = [
            ("starter", 0.995, 0.30, "Setup is strong enough for near-current entry."),
            ("pullback_add", 0.97, 0.35, "Add on normal pullback."),
            ("deep_add", 0.94, 0.35, "Add on stronger pullback."),
        ]
    else:
        levels = [
            ("small_watch_entry", 0.96, 0.40, "Only small exposure because signal is not clean."),
            ("better_pullback", 0.92, 0.60, "Reserve most allocation for a better price."),
        ]

    orders = []
    for name, price_mult, alloc_share, reason in levels:
        orders.append(
            LadderOrder(
                level=name,
                limit_price=round(current_price * price_mult, 2),
                allocation_fraction=round(max_tqqq_allocation * alloc_share, 4),
                reason=reason,
            )
        )

    return orders
