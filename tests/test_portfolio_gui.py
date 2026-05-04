from __future__ import annotations

from pathlib import Path

from trading_lab.portfolio.gui import apply_form_action, render_status_page
from trading_lab.portfolio.state import read_account, read_open_orders, read_positions


SUMMARY = """Date: 2026-05-04
QQQ: 420.00
TQQQ: 60.00
Profile: default
Active target column: TQQQ_target_5d_threshold_horizon_return
Suggested action: WAIT_FOR_PULLBACK
Max TQQQ allocation: 5%
Selected strategy eligible today: NO
- NO: selected model probability 0.580 < threshold 0.65

Suggested TQQQ ladder:
- shallow_pullback: limit $58.20, allocation 1.2%, synthetic.
"""


def _write_dashboard_fixture(tmp_path: Path) -> None:
    portfolio_dir = tmp_path / "data" / "raw" / "portfolio"
    market_dir = tmp_path / "data" / "raw" / "market"
    reports_dir = tmp_path / "data" / "reports"
    portfolio_dir.mkdir(parents=True)
    market_dir.mkdir(parents=True)
    reports_dir.mkdir(parents=True)
    (portfolio_dir / "positions.csv").write_text(
        "symbol,quantity,notes,updated_at\nTQQQ,4,current_position,2026-05-04\n",
        encoding="utf-8",
    )
    (portfolio_dir / "open_orders.csv").write_text(
        "symbol,side,type,quantity,limit_price,time_in_force,status,submitted_at,notes\n"
        "TQQQ,buy,limit,10,58.00,GTC,placed,2026-04-29,current_open_order\n",
        encoding="utf-8",
    )
    (portfolio_dir / "account.csv").write_text(
        "key,value,updated_at\ncash,1624.35,2026-05-04\naccount_value,5000,2026-05-04\n",
        encoding="utf-8",
    )
    (market_dir / "TQQQ.csv").write_text("date,close\n2026-05-04,60\n", encoding="utf-8")
    (reports_dir / "daily_decision_summary.txt").write_text(SUMMARY, encoding="utf-8")
    (reports_dir / "selected_model_latest_signal.csv").write_text(
        "date,model,probability\n2026-05-04,demo,0.58\n",
        encoding="utf-8",
    )


def test_gui_render_includes_local_status_and_forms(tmp_path: Path, monkeypatch):
    _write_dashboard_fixture(tmp_path)
    monkeypatch.chdir(tmp_path)

    html = render_status_page()

    assert "Trading Lab" in html
    assert "TQQQ" in html
    assert "/position/set" in html
    assert "/order/add" in html


def test_gui_contains_daily_decision_dark_css_dates_and_saved_account(tmp_path, monkeypatch):
    _write_dashboard_fixture(tmp_path)
    monkeypatch.chdir(tmp_path)

    html = render_status_page()

    assert "Daily decision" in html
    assert "ACTION" not in html
    assert "HOLD" in html
    assert "background: radial-gradient" in html
    assert "color-scheme: dark" in html
    assert "href=" not in html
    assert "src=" not in html
    assert "positions.csv modified" in html
    assert "open_orders.csv modified" in html
    assert "account.csv modified" in html
    assert "Market CSV date" in html
    assert "2026-05-04" in html
    assert "$1,624.35" in html
    assert "$5,000.00" in html
    assert "Local CSV update only" in html


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
