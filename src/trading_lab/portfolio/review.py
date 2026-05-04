from __future__ import annotations

import re
from dataclasses import dataclass

from trading_lab.portfolio.state import OpenOrder, PortfolioState, SymbolPortfolioState


@dataclass(frozen=True)
class HoldingReview:
    symbol: str
    quantity: float
    value: float | None
    allocation: float | None
    price_status: str
    status: str


@dataclass(frozen=True)
class OrderReview:
    symbol: str
    side: str
    quantity: float
    limit_price: float
    notional: float
    status: str
    price_relation: str
    ladder_relation: str
    projected_exposure: float | None
    recommended_action: str
    reason: str


@dataclass(frozen=True)
class OrderReviewSummary:
    total_pending_buy_notional: float
    total_pending_sell_notional: float
    cancel_reduce_review_count: int
    top_actions: tuple[OrderReview, ...]


def review_holdings(
    state: PortfolioState,
    traded_symbol: str,
    small_threshold: float = 0.02,
    review_size_threshold: float = 0.05,
) -> tuple[HoldingReview, ...]:
    rows: list[HoldingReview] = []
    traded = traded_symbol.upper()
    for symbol in sorted(state.symbols):
        if symbol == traded:
            continue
        item = state.symbols[symbol]
        if item.quantity == 0:
            continue
        if item.latest_price is None:
            status = "PRICE_MISSING"
            price_status = "missing"
        elif item.allocation_pct is None:
            status = "REVIEW"
            price_status = "known"
        elif item.allocation_pct < small_threshold:
            status = "OK_SMALL"
            price_status = "known"
        elif item.allocation_pct <= review_size_threshold:
            status = "REVIEW"
            price_status = "known"
        else:
            status = "REVIEW_SIZE"
            price_status = "known"
        rows.append(
            HoldingReview(
                symbol=symbol,
                quantity=item.quantity,
                value=item.market_value,
                allocation=item.allocation_pct,
                price_status=price_status,
                status=status,
            )
        )
    return tuple(rows)


def review_open_orders(
    state: PortfolioState,
    traded_symbol: str,
    *,
    account_value: float,
    max_allocation: float | None,
    suggested_action: str,
    strategy_eligible: bool,
    ladder: tuple[str, ...] = (),
) -> tuple[OrderReview, ...]:
    traded = traded_symbol.upper()
    first_ladder = _first_ladder_price(ladder)
    current = state.symbols.get(traded)
    current_value = (current.market_value or 0.0) if current is not None else 0.0
    max_exposure = account_value * max_allocation if max_allocation is not None else None
    remaining_buy_capacity = (
        max(max_exposure - current_value, 0.0) if max_exposure is not None else None
    )

    reviews: list[OrderReview] = []
    for order in state.open_orders:
        if order.status.lower() != "placed":
            reviews.append(_order_review(order, state, "REVIEW", "Order is not placed."))
            continue
        if order.symbol != traded:
            reviews.append(_review_other_symbol_order(order, state, account_value))
            continue
        if order.side == "sell":
            reviews.append(_review_traded_sell(order, state, max_exposure, current_value))
            continue
        if order.side != "buy":
            reviews.append(_order_review(order, state, "REVIEW", "Unsupported order side."))
            continue

        aggressive = (
            suggested_action in {"WAIT_FOR_PULLBACK", "SPY_CORE_ONLY_OR_WAIT"}
            and not strategy_eligible
        )
        ladder_relation = _ladder_relation(order, first_ladder)
        if remaining_buy_capacity is not None and remaining_buy_capacity <= 0:
            action = "CANCEL"
            reason = "Buy capacity is $0 under the max recommended exposure."
        elif remaining_buy_capacity is not None and order.exposure > remaining_buy_capacity:
            action = "REDUCE"
            reason = "Order notional exceeds remaining buy capacity."
            remaining_buy_capacity = 0.0
        elif first_ladder is not None and order.limit_price > first_ladder * 1.01:
            action = "MOVE_LOWER"
            reason = "Buy limit is above the first suggested ladder price."
            if remaining_buy_capacity is not None:
                remaining_buy_capacity -= order.exposure
        elif aggressive:
            action = "REVIEW"
            reason = "Strategy is not eligible; review pending buy before adding risk."
            if remaining_buy_capacity is not None:
                remaining_buy_capacity -= order.exposure
        else:
            action = "KEEP"
            reason = "Order fits remaining buy capacity and ladder context."
            if remaining_buy_capacity is not None:
                remaining_buy_capacity -= order.exposure
        reviews.append(_order_review(order, state, action, reason, ladder_relation=ladder_relation))
    return tuple(reviews)


def summarize_order_reviews(reviews: tuple[OrderReview, ...]) -> OrderReviewSummary:
    buy_notional = sum(row.notional for row in reviews if row.side == "buy" and row.status == "placed")
    sell_notional = sum(row.notional for row in reviews if row.side == "sell" and row.status == "placed")
    flagged = [row for row in reviews if row.recommended_action in {"CANCEL", "REDUCE", "REVIEW"}]
    priority = {"CANCEL": 0, "REDUCE": 1, "MOVE_LOWER": 2, "REVIEW": 3, "KEEP": 4}
    top_actions = tuple(sorted(flagged, key=lambda row: priority[row.recommended_action])[:3])
    return OrderReviewSummary(
        total_pending_buy_notional=buy_notional,
        total_pending_sell_notional=sell_notional,
        cancel_reduce_review_count=len(flagged),
        top_actions=top_actions,
    )


def _review_other_symbol_order(
    order: OpenOrder,
    state: PortfolioState,
    account_value: float,
) -> OrderReview:
    allocation = order.exposure / account_value if account_value > 0 else 0.0
    if allocation > 0.05:
        action = "REVIEW"
        reason = "No model signal for this symbol and order exceeds 5% sizing check."
    else:
        action = "REVIEW"
        reason = "No configured model signal for this symbol; review manually."
    return _order_review(order, state, action, reason)


def _review_traded_sell(
    order: OpenOrder,
    state: PortfolioState,
    max_exposure: float | None,
    current_value: float,
) -> OrderReview:
    if max_exposure is not None and current_value > max_exposure:
        return _order_review(order, state, "KEEP", "Sell order reduces overexposure.")
    return _order_review(order, state, "REVIEW", "Sell order reduces exposure; review manually.")


def _order_review(
    order: OpenOrder,
    state: PortfolioState,
    action: str,
    reason: str,
    *,
    ladder_relation: str = "not applicable",
) -> OrderReview:
    item = state.symbols.get(order.symbol)
    projected = _projected_exposure(order, item)
    return OrderReview(
        symbol=order.symbol,
        side=order.side,
        quantity=order.quantity,
        limit_price=order.limit_price,
        notional=order.exposure,
        status=order.status,
        price_relation=_price_relation(order, item),
        ladder_relation=ladder_relation,
        projected_exposure=projected,
        recommended_action=action,
        reason=reason,
    )


def _projected_exposure(order: OpenOrder, item: SymbolPortfolioState | None) -> float | None:
    current_value = item.market_value if item is not None else None
    if current_value is None:
        return None
    if order.side == "buy":
        return current_value + order.exposure
    if order.side == "sell":
        return max(current_value - order.exposure, 0.0)
    return current_value


def _price_relation(order: OpenOrder, item: SymbolPortfolioState | None) -> str:
    if item is None or item.latest_price is None:
        return "price missing"
    diff = (order.limit_price / item.latest_price) - 1.0
    return f"{diff:+.1%} vs current"


def _ladder_relation(order: OpenOrder, first_ladder: float | None) -> str:
    if first_ladder is None:
        return "no ladder"
    diff = (order.limit_price / first_ladder) - 1.0
    return f"{diff:+.1%} vs first ladder"


def _first_ladder_price(ladder: tuple[str, ...]) -> float | None:
    for line in ladder:
        match = re.search(r"limit\s+\$?([0-9][0-9,.]*)", line, flags=re.IGNORECASE)
        if match:
            return float(match.group(1).replace(",", ""))
    return None
