from __future__ import annotations

from trading_lab.portfolio.review import review_holdings, review_open_orders
from trading_lab.portfolio.state import OpenOrder, PortfolioState, SymbolPortfolioState


def test_non_traded_holdings_review_statuses():
    state = PortfolioState(
        symbols={
            "TQQQ": SymbolPortfolioState(symbol="TQQQ", quantity=4, allocation_pct=0.05),
            "META": SymbolPortfolioState(
                symbol="META",
                quantity=0.04,
                latest_price=600,
                market_value=24,
                allocation_pct=0.0048,
            ),
            "BIG": SymbolPortfolioState(
                symbol="BIG",
                quantity=10,
                latest_price=50,
                market_value=500,
                allocation_pct=0.10,
            ),
            "MISS": SymbolPortfolioState(symbol="MISS", quantity=1),
        }
    )

    reviews = {row.symbol: row for row in review_holdings(state, "TQQQ")}

    assert reviews["META"].status == "OK_SMALL"
    assert reviews["BIG"].status == "REVIEW_SIZE"
    assert reviews["MISS"].status == "PRICE_MISSING"


def test_order_review_marks_over_capacity_buys_cancel_or_reduce_and_sell_not_aggressive():
    state = PortfolioState(
        account_value=5000,
        symbols={
            "TQQQ": SymbolPortfolioState(
                symbol="TQQQ",
                quantity=4,
                latest_price=60,
                market_value=240,
            )
        },
        open_orders=(
            OpenOrder("TQQQ", "buy", "limit", 10, 58, "GTC", "placed", "2026-05-04"),
            OpenOrder("TQQQ", "sell", "limit", 4, 68.50, "GTC", "placed", "2026-05-04"),
        ),
    )

    reviews = review_open_orders(
        state,
        "TQQQ",
        account_value=5000,
        max_allocation=0.05,
        suggested_action="WAIT_FOR_PULLBACK",
        strategy_eligible=False,
        ladder=("shallow_pullback: limit $58.20, allocation 1.2%, synthetic.",),
    )

    buy = [row for row in reviews if row.side == "buy"][0]
    sell = [row for row in reviews if row.side == "sell"][0]

    assert buy.recommended_action in {"CANCEL", "REDUCE"}
    assert sell.recommended_action in {"KEEP", "REVIEW"}
    assert sell.recommended_action not in {"CANCEL", "REDUCE", "MOVE_LOWER"}
