from __future__ import annotations

from pathlib import Path

import inspect
import pytest

from trading_lab.portfolio import state
from trading_lab.portfolio.state import (
    ACCOUNT_PATH,
    OPEN_ORDERS_PATH,
    POSITIONS_PATH,
    append_open_order,
    build_portfolio_state,
    clear_open_orders,
    latest_market_prices,
    read_account,
    read_open_orders,
    read_positions,
    update_position_quantity,
    write_account_value,
    write_position,
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


def test_update_buy_sell_set_modifies_positions(tmp_path: Path):
    path = tmp_path / "positions.csv"

    write_position(path, "TQQQ", 4)
    before, after = update_position_quantity(path, "TQQQ", 1)
    assert (before, after) == (4, 5)
    before, after = update_position_quantity(path, "TQQQ", -1)
    assert (before, after) == (5, 4)
    write_position(path, "TQQQ", 7)

    assert read_positions(path)[0].quantity == 7


def test_sell_cannot_make_position_negative_by_default(tmp_path: Path):
    path = tmp_path / "positions.csv"
    write_position(path, "TQQQ", 1)

    with pytest.raises(ValueError, match="negative"):
        update_position_quantity(path, "TQQQ", -2)

    assert read_positions(path)[0].quantity == 1
    update_position_quantity(path, "TQQQ", -2, allow_negative=True)
    assert read_positions(path)[0].quantity == -1


def test_account_csv_cash_and_account_value_are_read_and_overridden(tmp_path: Path):
    account_path = tmp_path / "account.csv"
    positions_path = tmp_path / "positions.csv"
    market_dir = tmp_path / "market"
    market_dir.mkdir()
    write_account_value(account_path, "cash", 1000)
    write_account_value(account_path, "account_value", 5000)
    write_position(positions_path, "TQQQ", 4)
    (market_dir / "TQQQ.csv").write_text("date,close\n2026-05-04,50\n", encoding="utf-8")

    account = read_account(account_path)
    state_from_csv = build_portfolio_state(
        positions_path=positions_path,
        open_orders_path=tmp_path / "orders.csv",
        account_path=account_path,
        market_dir=market_dir,
    )
    overridden = build_portfolio_state(
        positions_path=positions_path,
        open_orders_path=tmp_path / "orders.csv",
        account_path=account_path,
        market_dir=market_dir,
        account_value=10000,
        cash=250,
    )

    assert account.cash == 1000
    assert account.account_value == 5000
    assert state_from_csv.cash == 1000
    assert state_from_csv.account_value == 5000
    assert state_from_csv.symbols["TQQQ"].allocation_pct == pytest.approx(0.04)
    assert overridden.cash == 250
    assert overridden.account_value == 10000
    assert overridden.symbols["TQQQ"].allocation_pct == pytest.approx(0.02)


def test_order_clear_and_clear_all_mark_orders_canceled(tmp_path: Path):
    path = tmp_path / "open_orders.csv"
    append_open_order(path, side="buy", symbol="TQQQ", quantity=1, limit_price=58)
    append_open_order(path, side="sell", symbol="TQQQ", quantity=1, limit_price=68)
    append_open_order(path, side="buy", symbol="APP", quantity=1, limit_price=10)

    assert clear_open_orders(path, "TQQQ") == 2
    orders = read_open_orders(path)
    assert [order.status for order in orders if order.symbol == "TQQQ"] == ["canceled", "canceled"]
    assert [order.status for order in orders if order.symbol == "APP"] == ["placed"]

    assert clear_open_orders(path) == 1
    assert all(order.status == "canceled" for order in read_open_orders(path))


def test_cli_update_commands_modify_local_csvs(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    import trading_lab.cli.main as cli_main

    commands = [
        ["tl", "update", "set", "TQQQ", "4"],
        ["tl", "update", "buy", "TQQQ", "1"],
        ["tl", "update", "sell", "TQQQ", "1"],
        ["tl", "update", "cash", "1000"],
        ["tl", "update", "account-value", "5000"],
        ["tl", "update", "order", "buy", "TQQQ", "10", "58"],
        ["tl", "update", "order", "sell", "TQQQ", "4", "68.50"],
        ["tl", "update", "order", "clear", "TQQQ"],
    ]
    for argv in commands:
        monkeypatch.setattr("sys.argv", argv)
        cli_main.main()

    assert read_positions(POSITIONS_PATH)[0].quantity == 4
    assert read_account(ACCOUNT_PATH).cash == 1000
    assert read_account(ACCOUNT_PATH).account_value == 5000
    assert all(order.status == "canceled" for order in read_open_orders(OPEN_ORDERS_PATH))
    assert "Local-only update" in capsys.readouterr().out


def test_cli_portfolio_status_includes_non_traded_trend_review(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    portfolio_dir = tmp_path / "data" / "raw" / "portfolio"
    market_dir = tmp_path / "data" / "raw" / "market"
    portfolio_dir.mkdir(parents=True)
    market_dir.mkdir(parents=True)
    (portfolio_dir / "positions.csv").write_text(
        "symbol,quantity,notes,updated_at\n"
        "TQQQ,4,current_position,2026-05-04\n"
        "META,1,current_position,2026-05-04\n",
        encoding="utf-8",
    )
    (portfolio_dir / "open_orders.csv").write_text(
        "symbol,side,type,quantity,limit_price,time_in_force,status,submitted_at,notes\n",
        encoding="utf-8",
    )
    rows = ["date,close"] + [f"2026-05-{day:02d},{100 + day:.2f}" for day in range(1, 22)]
    (market_dir / "TQQQ.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (market_dir / "META.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")

    import trading_lab.cli.main as cli_main

    monkeypatch.setattr("sys.argv", ["tl", "portfolio", "status", "--account-value", "5000"])
    cli_main.main()

    out = capsys.readouterr().out
    assert "Non-traded holdings trend review:" in out
    assert "META: size REVIEW, trend" in out
    assert "No model-backed predictions are claimed for non-traded holdings." in out
