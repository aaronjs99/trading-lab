from __future__ import annotations

from pathlib import Path

from trading_lab.portfolio.gui import apply_form_action, render_status_page
from trading_lab.portfolio.state import read_account, read_open_orders, read_positions


def test_gui_render_includes_local_status_and_forms(tmp_path: Path, monkeypatch):
    portfolio_dir = tmp_path / "data" / "raw" / "portfolio"
    market_dir = tmp_path / "data" / "raw" / "market"
    portfolio_dir.mkdir(parents=True)
    market_dir.mkdir(parents=True)
    (portfolio_dir / "positions.csv").write_text(
        "symbol,quantity,notes,updated_at\nTQQQ,4,current_position,2026-05-04\n",
        encoding="utf-8",
    )
    (market_dir / "TQQQ.csv").write_text("date,close\n2026-05-04,60\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    html = render_status_page()

    assert "Local portfolio" in html
    assert "TQQQ" in html
    assert "/position/set" in html
    assert "/order/add" in html


def test_gui_apply_form_actions_edit_local_csvs(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert apply_form_action("/account", {"cash": "1000", "account_value": "5000"})
    assert apply_form_action("/position/set", {"symbol": "TQQQ", "quantity": "4"})
    assert apply_form_action(
        "/position/update",
        {"side": "buy", "symbol": "TQQQ", "quantity": "1"},
    )
    assert apply_form_action(
        "/order/add",
        {"side": "buy", "symbol": "TQQQ", "quantity": "10", "limit_price": "58"},
    )
    assert apply_form_action("/order/clear", {"symbol": "TQQQ"})

    assert read_account().cash == 1000
    assert read_account().account_value == 5000
    assert read_positions()[0].quantity == 5
    assert read_open_orders()[0].status == "canceled"
