from __future__ import annotations

from pathlib import Path

import inspect
import pytest

from trading_lab.portfolio import state
from trading_lab.portfolio.state import (
    build_portfolio_state,
    latest_market_prices,
    read_open_orders,
    read_positions,
)


def test_read_positions_csv_without_prices_stored(tmp_path: Path):
    path = tmp_path / "positions.csv"
    path.write_text(
        "symbol,quantity,notes,updated_at\n"
        "TQQQ,4,current_position,2026-05-04\n",
        encoding="utf-8",
    )

    positions = read_positions(path)

    assert positions[0].symbol == "TQQQ"
    assert positions[0].quantity == 4
    assert not hasattr(positions[0], "price")


def test_read_open_orders_csv(tmp_path: Path):
    path = tmp_path / "open_orders.csv"
    path.write_text(
        "symbol,side,type,quantity,limit_price,time_in_force,status,submitted_at,notes\n"
        "TQQQ,buy,limit,10,58.00,GTC,placed,2026-04-29,current_open_order\n",
        encoding="utf-8",
    )

    orders = read_open_orders(path)

    assert orders[0].symbol == "TQQQ"
    assert orders[0].side == "buy"
    assert orders[0].exposure == 580


def test_calculates_values_from_synthetic_market_csvs(tmp_path: Path):
    portfolio_dir = tmp_path / "portfolio"
    market_dir = tmp_path / "market"
    portfolio_dir.mkdir()
    market_dir.mkdir()
    (portfolio_dir / "positions.csv").write_text(
        "symbol,quantity,notes,updated_at\nTQQQ,4,current_position,2026-05-04\n",
        encoding="utf-8",
    )
    (portfolio_dir / "open_orders.csv").write_text(
        "symbol,side,type,quantity,limit_price,time_in_force,status,submitted_at,notes\n",
        encoding="utf-8",
    )
    (market_dir / "TQQQ.csv").write_text(
        "date,close\n2026-05-01,60.00\n2026-05-04,62.50\n",
        encoding="utf-8",
    )

    prices = latest_market_prices(market_dir)
    result = build_portfolio_state(
        positions_path=portfolio_dir / "positions.csv",
        open_orders_path=portfolio_dir / "open_orders.csv",
        market_dir=market_dir,
        account_value=5000,
    )

    assert prices["TQQQ"] == 62.5
    assert result.symbols["TQQQ"].market_value == 250
    assert result.symbols["TQQQ"].allocation_pct == pytest.approx(0.05)


def test_pending_tqqq_buy_and_sell_exposure_are_included(tmp_path: Path):
    portfolio_dir = tmp_path / "portfolio"
    market_dir = tmp_path / "market"
    portfolio_dir.mkdir()
    market_dir.mkdir()
    (portfolio_dir / "positions.csv").write_text(
        "symbol,quantity,notes,updated_at\nTQQQ,4,current_position,2026-05-04\n",
        encoding="utf-8",
    )
    (portfolio_dir / "open_orders.csv").write_text(
        "symbol,side,type,quantity,limit_price,time_in_force,status,submitted_at,notes\n"
        "TQQQ,buy,limit,10,58.00,GTC,placed,2026-04-29,current_open_order\n"
        "TQQQ,sell,limit,4,68.50,GTC,placed,2026-04-29,current_open_order\n",
        encoding="utf-8",
    )
    (market_dir / "TQQQ.csv").write_text("date,close\n2026-05-04,60.00\n", encoding="utf-8")

    result = build_portfolio_state(
        positions_path=portfolio_dir / "positions.csv",
        open_orders_path=portfolio_dir / "open_orders.csv",
        market_dir=market_dir,
        account_value=5000,
    )
    tqqq = result.symbols["TQQQ"]

    assert tqqq.pending_buy_quantity == 10
    assert tqqq.pending_buy_value == 580
    assert tqqq.pending_sell_quantity == 4
    assert tqqq.pending_sell_value == 274
    assert tqqq.post_fill_quantity == 10


def test_missing_portfolio_files_produce_empty_state(tmp_path: Path):
    result = build_portfolio_state(
        positions_path=tmp_path / "missing_positions.csv",
        open_orders_path=tmp_path / "missing_orders.csv",
        market_dir=tmp_path / "market",
    )

    assert result.positions == ()
    assert result.open_orders == ()
    assert result.symbols == {}


def test_invalid_required_columns_raise_clear_value_error(tmp_path: Path):
    path = tmp_path / "positions.csv"
    path.write_text("symbol,notes\nTQQQ,current_position\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Missing required columns"):
        read_positions(path)


def test_portfolio_module_has_no_broker_or_order_placement_functions():
    source = inspect.getsource(state).lower()

    assert "robinhood" not in source
    assert "broker" not in source
    assert "place_order" not in source
    assert "submit_order" not in source
