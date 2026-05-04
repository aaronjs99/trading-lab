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


@dataclass(frozen=True)
class ExposureContext:
    traded_symbol: str
    current_exposure: float | None
    max_exposure: float | None
    buy_capacity: float | None


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
    risk_mode: str = "conservative",
) -> tuple[OrderReview, ...]:
    mode = normalize_risk_mode(risk_mode)
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
        if mode == "aggressive":
            action, reason = _aggressive_buy_action(
                order,
                traded,
                current_value,
                max_exposure,
                first_ladder,
                aggressive,
            )
        elif mode == "balanced":
            action, reason = _balanced_buy_action(
                order,
                traded,
                current_value,
                max_exposure,
                remaining_buy_capacity,
                first_ladder,
                aggressive,
            )
            if remaining_buy_capacity is not None and action in {"KEEP", "REVIEW"}:
                remaining_buy_capacity -= order.exposure
            elif remaining_buy_capacity is not None and action == "REDUCE":
                remaining_buy_capacity = 0.0
        elif remaining_buy_capacity is not None and remaining_buy_capacity <= 0:
            action = "CANCEL"
            reason = _zero_capacity_buy_reason(order, traded, current_value, max_exposure)
        elif remaining_buy_capacity is not None and order.exposure > remaining_buy_capacity:
            action = "REDUCE"
            reason = (
                f"Reduce this buy: order notional {_money(order.exposure)} exceeds remaining "
                f"buy capacity {_money(remaining_buy_capacity)}; projected exposure would be "
                f"{_money(current_value + order.exposure)}."
            )
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


def exposure_context(
    state: PortfolioState,
    traded_symbol: str,
    account_value: float,
    max_allocation: float | None,
) -> ExposureContext:
    traded = traded_symbol.upper()
    item = state.symbols.get(traded)
    current = item.market_value if item is not None else None
    max_exposure = account_value * max_allocation if max_allocation is not None else None
    capacity = (
        max(max_exposure - (current or 0.0), 0.0)
        if max_exposure is not None and current is not None
        else None
    )
    return ExposureContext(traded, current, max_exposure, capacity)


def advice_lines(
    state: PortfolioState,
    traded_symbol: str,
    *,
    action: str,
    max_exposure: float | None,
    order_summary: OrderReviewSummary,
    risk_mode: str = "conservative",
) -> tuple[str, ...]:
    mode = normalize_risk_mode(risk_mode)
    traded = traded_symbol.upper()
    item = state.symbols.get(traded)
    current = item.market_value if item is not None else None
    lines = [f"Risk mode: {mode}."]
    if mode == "aggressive":
        lines.append("Aggressive mode accepts higher drawdown risk.")
        lines.append("Trend-first advice: prefer deeper, ladder-aligned buys over exposure-only rules.")
    elif mode == "balanced":
        lines.append("Balanced mode blends exposure limits with trend and ladder quality.")
    else:
        lines.append("Conservative mode is exposure-first.")
    lines.append(f"Hold current {traded}." if action == "HOLD" else f"Current action is {action}.")
    if mode == "aggressive":
        lines.append(f"Do not add shallow {traded} buys now; only deep ladder-aligned orders merit review.")
    else:
        lines.append(f"Do not add new {traded} buys now.")
    if current is not None and max_exposure is not None and current > max_exposure:
        lines.append(
            f"Current {traded} exposure ({_money(current)}) is already slightly above "
            f"the model max ({_money(max_exposure)})."
        )
    if order_summary.total_pending_buy_notional > 0:
        lines.append(
            f"Pending buy orders ({_money(order_summary.total_pending_buy_notional)}) "
            "are much too large relative to the current model recommendation."
        )
    sell_orders = [
        order
        for order in state.open_orders
        if order.symbol == traded and order.side == "sell" and order.status == "placed"
    ]
    if sell_orders:
        first = sell_orders[0]
        lines.append(
            f"Sell order at {first.limit_price:g} reduces exposure and can be kept/reviewed."
        )
    lines.append(
        "Non-traded holdings are tiny portfolio dust/status, not model-backed trade signals."
    )
    return tuple(lines)


def suggested_order_ideas(
    state: PortfolioState,
    traded_symbol: str,
    *,
    context: ExposureContext,
    reviews: tuple[OrderReview, ...],
    ladder: tuple[str, ...] = (),
    risk_mode: str = "conservative",
) -> tuple[str, ...]:
    mode = normalize_risk_mode(risk_mode)
    traded = traded_symbol.upper()
    ideas: list[str] = []
    if context.buy_capacity is not None and context.buy_capacity <= 0 and mode != "aggressive":
        ideas.append("No new buy orders. Cancel/reduce existing buys first.")
    elif context.buy_capacity is not None and context.buy_capacity <= 0:
        ideas.append("No new shallow buy orders; aggressive mode may review only deep ladder-aligned buys.")
    elif context.buy_capacity is not None:
        first_ladder = _first_ladder_price(ladder)
        if first_ladder is not None and first_ladder > 0:
            size = int(context.buy_capacity // first_ladder)
            if size <= 0:
                ideas.append("No new buy orders. Cancel/reduce existing buys first.")
            else:
                ideas.append(
                    f"Possible {traded} buy idea: up to {size:g} share(s) near "
                    f"{_money(first_ladder)} from the ladder."
                )
        else:
            ideas.append(f"Possible {traded} buy idea: keep notional under {_money(context.buy_capacity)}.")
    else:
        ideas.append("No new buy idea because buy capacity is unknown.")
    if any(row.side == "buy" and row.recommended_action in {"CANCEL", "REDUCE"} for row in reviews):
        ideas.append(f"Cancel/reduce current pending {traded} buys.")
    for row in reviews:
        if row.symbol == traded and row.side == "sell" and row.recommended_action in {"KEEP", "REVIEW"}:
            ideas.append(
                f"Keep/review the {traded} sell {row.quantity:g} @ {_money(row.limit_price)} "
                "because it reduces exposure."
            )
            break
    if (
        context.current_exposure is not None
        and context.max_exposure is not None
        and context.current_exposure > context.max_exposure
    ):
        excess = context.current_exposure - context.max_exposure
        ideas.append(
            f"Over max by about {_money(excess)}; too small to justify a market sell by itself, "
            "so focus on canceling pending buys."
        )
    return tuple(ideas)


def normalize_risk_mode(value: str | None) -> str:
    mode = (value or "conservative").strip().lower()
    if mode not in {"conservative", "balanced", "aggressive"}:
        raise ValueError("risk mode must be conservative, balanced, or aggressive")
    return mode


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


def _zero_capacity_buy_reason(
    order: OpenOrder,
    traded: str,
    current_value: float,
    max_exposure: float | None,
) -> str:
    projected = current_value + order.exposure
    if max_exposure is None:
        return (
            f"Cancel this buy: buy capacity is $0, order notional is {_money(order.exposure)}, "
            f"and projected exposure after fill would be {_money(projected)}."
        )
    return (
        f"Cancel this buy: current {traded} exposure is already {_money(current_value)} "
        f"vs max {_money(max_exposure)}, order notional is {_money(order.exposure)}, "
        f"and filling this order would raise exposure to {_money(projected)}."
    )


def _balanced_buy_action(
    order: OpenOrder,
    traded: str,
    current_value: float,
    max_exposure: float | None,
    remaining_buy_capacity: float | None,
    first_ladder: float | None,
    weak_setup: bool,
) -> tuple[str, str]:
    if first_ladder is not None and order.limit_price <= first_ladder * 0.97:
        return (
            "REVIEW",
            f"Balanced mode: deep {traded} buy is below/near the deeper ladder area; "
            f"exposure warning remains because filling it projects exposure to "
            f"{_money(current_value + order.exposure)}.",
        )
    if remaining_buy_capacity is not None and remaining_buy_capacity <= 0:
        return "CANCEL", _zero_capacity_buy_reason(order, traded, current_value, max_exposure)
    if weak_setup and first_ladder is not None and order.limit_price > first_ladder:
        return (
            "REDUCE",
            "Balanced mode: model setup is weak, so shallow/high pending buys should be reduced.",
        )
    if remaining_buy_capacity is not None and order.exposure > remaining_buy_capacity:
        return (
            "REDUCE",
            f"Balanced mode: order notional {_money(order.exposure)} exceeds remaining "
            f"buy capacity {_money(remaining_buy_capacity)}.",
        )
    return "KEEP", "Balanced mode: order fits capacity or ladder context."


def _aggressive_buy_action(
    order: OpenOrder,
    traded: str,
    current_value: float,
    max_exposure: float | None,
    first_ladder: float | None,
    weak_setup: bool,
) -> tuple[str, str]:
    projected = current_value + order.exposure
    if first_ladder is not None and order.limit_price <= first_ladder * 0.97:
        return (
            "REVIEW",
            f"Aggressive mode accepts higher drawdown risk; this deeper {traded} buy is "
            f"below the first ladder area. Exposure warning: current {_money(current_value)} "
            f"vs max {_money(max_exposure)}, projected {_money(projected)}.",
        )
    if first_ladder is not None and order.limit_price <= first_ladder:
        return (
            "REVIEW",
            f"Aggressive mode: near-ladder {traded} buy can be reviewed, but exposure warning "
            f"remains because projected exposure is {_money(projected)} vs max {_money(max_exposure)}.",
        )
    action = "REDUCE" if weak_setup else "MOVE_LOWER"
    return (
        action,
        f"Aggressive mode still avoids shallow/high buys when setup is weak; move lower toward "
        f"the ladder. Projected exposure would be {_money(projected)}.",
    )


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


def _money(value: float | None) -> str:
    if value is None:
        return "unavailable"
    return f"${value:,.2f}"
