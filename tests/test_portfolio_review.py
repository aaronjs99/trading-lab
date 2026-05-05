from __future__ import annotations

from pathlib import Path

import pytest

from trading_lab.portfolio.review import review_holdings, review_open_orders
from trading_lab.portfolio.state import OpenOrder, PortfolioState, SymbolPortfolioState


def _write_market(path: Path, symbol: str, prices: list[float], start_day: int = 1) -> None:
    rows = ["date,close"]
    for index, price in enumerate(prices, start=start_day):
        rows.append(f"2026-04-{index:02d},{price:.2f}" if index <= 30 else f"2026-05-{index - 30:02d},{price:.2f}")
    (path / f"{symbol}.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")


def _state_for(symbol: str, price: float = 100.0) -> PortfolioState:
    return PortfolioState(
        symbols={
            "TQQQ": SymbolPortfolioState(symbol="TQQQ", quantity=4, latest_price=60),
            symbol: SymbolPortfolioState(
                symbol=symbol,
                quantity=1,
                latest_price=price,
                market_value=price,
                allocation_pct=0.01,
            ),
        }
    )


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


def test_non_traded_holding_strong_uptrend_from_local_market_csv(tmp_path: Path):
    _write_market(tmp_path, "TQQQ", [60 + i for i in range(60)])
    _write_market(tmp_path, "META", [50 + i for i in range(60)])

    review = review_holdings(_state_for("META", 109), "TQQQ", market_dir=tmp_path)[0]

    assert review.trend_status == "STRONG_UPTREND"
    assert review.return_20d is not None and review.return_20d > 0
    assert review.distance_20dma is not None and review.distance_20dma > 0
    assert "no model-backed trade signal" in review.trend_note


def test_non_traded_holding_downtrend_from_local_market_csv(tmp_path: Path):
    _write_market(tmp_path, "TQQQ", [60 + i for i in range(60)])
    _write_market(tmp_path, "META", [120 - i for i in range(60)])

    review = review_holdings(_state_for("META", 61), "TQQQ", market_dir=tmp_path)[0]

    assert review.trend_status == "DOWNTREND"
    assert "below 20DMA and 50DMA" in review.trend_note


def test_non_traded_holding_pullback_from_local_market_csv(tmp_path: Path):
    _write_market(tmp_path, "TQQQ", [60 + i for i in range(60)])
    pullback = list(range(45, 85)) + list(range(85, 101)) + [94, 94, 94, 94]
    _write_market(tmp_path, "META", [float(value) for value in pullback])

    review = review_holdings(_state_for("META", 94), "TQQQ", market_dir=tmp_path)[0]

    assert review.trend_status == "PULLBACK"
    assert review.drawdown_20d_high == pytest.approx(-0.06)
    assert "pullback from recent high" in review.trend_note


def test_non_traded_holding_missing_and_stale_price_statuses(tmp_path: Path):
    _write_market(tmp_path, "TQQQ", [60 + i for i in range(60)])
    _write_market(tmp_path, "OLD", [50 + i for i in range(57)])
    state = PortfolioState(
        symbols={
            "TQQQ": SymbolPortfolioState(symbol="TQQQ", quantity=4, latest_price=60),
            "MISS": SymbolPortfolioState(symbol="MISS", quantity=1),
            "OLD": SymbolPortfolioState(
                symbol="OLD",
                quantity=1,
                latest_price=106,
                market_value=106,
                allocation_pct=0.01,
            ),
        }
    )

    reviews = {row.symbol: row for row in review_holdings(state, "TQQQ", market_dir=tmp_path)}

    assert reviews["MISS"].trend_status == "PRICE_MISSING"
    assert "Price data missing" in reviews["MISS"].trend_note
    assert reviews["OLD"].trend_status == "PRICE_STALE"
    assert "Price data stale" in reviews["OLD"].trend_note


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
    assert "order notional $580.00 exceeds remaining buy capacity $10.00" in buy.reason
    assert "projected exposure would be $820.00" in buy.reason
    assert sell.recommended_action in {"KEEP", "REVIEW"}
    assert sell.recommended_action not in {"CANCEL", "REDUCE", "MOVE_LOWER"}


def test_balanced_mode_cancels_shallow_buys_but_reviews_deeper_buys():
    state = PortfolioState(
        account_value=5000,
        symbols={
            "TQQQ": SymbolPortfolioState(
                symbol="TQQQ",
                quantity=4,
                latest_price=60,
                market_value=260,
            )
        },
        open_orders=(
            OpenOrder("TQQQ", "buy", "limit", 1, 60, "GTC", "placed", "2026-05-04"),
            OpenOrder("TQQQ", "buy", "limit", 1, 52, "GTC", "placed", "2026-05-04"),
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
        risk_mode="balanced",
    )

    assert reviews[0].recommended_action in {"CANCEL", "REDUCE"}
    assert reviews[1].recommended_action == "REVIEW"


def test_aggressive_mode_reviews_deep_buys_while_warning_about_exposure():
    state = PortfolioState(
        account_value=5000,
        symbols={
            "TQQQ": SymbolPortfolioState(
                symbol="TQQQ",
                quantity=4,
                latest_price=60,
                market_value=260,
            )
        },
        open_orders=(
            OpenOrder("TQQQ", "buy", "limit", 1, 60, "GTC", "placed", "2026-05-04"),
            OpenOrder("TQQQ", "buy", "limit", 1, 52, "GTC", "placed", "2026-05-04"),
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
        risk_mode="aggressive",
    )

    assert reviews[0].recommended_action in {"REDUCE", "MOVE_LOWER"}
    assert reviews[1].recommended_action == "REVIEW"
    assert "Aggressive mode accepts higher drawdown risk" in reviews[1].reason
    assert "Exposure warning" in reviews[1].reason
