from __future__ import annotations

import sys
from pathlib import Path

import pytest

from trading_lab.decision import render_daily_decision


SUMMARY = """Date: 2026-05-01
QQQ: 420.00
TQQQ: 60.00
Selected model probability (logistic_regression): 0.580
Profile: default
Configured target mode: barrier_first_hit
Active target mode: threshold_horizon_return
Active target column: TQQQ_target_5d_threshold_horizon_return
Target source: experiment_report
Suggested action: WAIT_FOR_PULLBACK
Max TQQQ allocation: 5%
Reason: Signal is constructive, but entry risk is not clean.

Selected strategy eligible today: NO
- NO: selected model probability 0.580 < threshold 0.65
- OK: QQQ trend required and current trend is true

Suggested TQQQ ladder:
- shallow_pullback: limit $58.20, allocation 1.2%, Small starter only after a normal pullback.
- medium_pullback: limit $56.40, allocation 1.8%, Better risk/reward pullback.
"""


def _write_reports(tmp_path: Path, summary: str = SUMMARY) -> Path:
    reports = tmp_path / "data" / "reports"
    reports.mkdir(parents=True)
    (reports / "daily_decision_summary.txt").write_text(summary, encoding="utf-8")
    (reports / "selected_model_latest_signal.csv").write_text(
        "date,model,probability\n2026-05-01,logistic_regression,0.58\n",
        encoding="utf-8",
    )
    return reports


def test_decision_missing_reports_message(tmp_path):
    text = render_daily_decision(reports_dir=tmp_path / "data" / "reports")

    assert "Missing reports" in text
    assert "tl_full_daily" in text


def test_decision_renders_from_synthetic_report_fixtures(tmp_path):
    reports = _write_reports(tmp_path)

    text = render_daily_decision(
        reports_dir=reports,
        account_value=5000,
        cash=1200,
    )

    assert text.startswith("ACTION: WAIT")
    assert "Buy capacity now: $250.00" in text
    assert "shallow_pullback: limit $58.20" in text
    assert "selected model probability 0.580 < threshold 0.65" in text
    assert "Already holding:" in text
    assert "In cash:" in text


def test_decision_accepts_research_profile_override(tmp_path):
    reports = _write_reports(tmp_path)

    text = render_daily_decision(reports_dir=reports, profile="research")

    assert text.startswith("ACTION: WAIT")
    assert "Profile: research" in text


def test_decision_prefers_profile_environment_over_report(tmp_path, monkeypatch):
    reports = _write_reports(tmp_path)
    monkeypatch.setenv("TRADING_LAB_PROFILE", "research")

    text = render_daily_decision(reports_dir=reports)

    assert "Profile: research" in text


def test_decision_accounts_for_existing_position(tmp_path):
    reports = _write_reports(tmp_path)

    text = render_daily_decision(
        reports_dir=reports,
        account_value=5000,
        positions=["TQQQ:2"],
    )

    assert text.startswith("ACTION: HOLD")
    assert "Already holding: yes, 2 shares of TQQQ, about $120.00." in text


def test_decision_warns_when_local_portfolio_pending_exceeds_max_allocation(tmp_path):
    reports = _write_reports(tmp_path)
    portfolio_dir = tmp_path / "data" / "raw" / "portfolio"
    market_dir = tmp_path / "data" / "raw" / "market"
    portfolio_dir.mkdir(parents=True)
    market_dir.mkdir(parents=True)
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

    text = render_daily_decision(
        reports_dir=reports,
        positions_path=portfolio_dir / "positions.csv",
        open_orders_path=portfolio_dir / "open_orders.csv",
        market_dir=market_dir,
        account_value=5000,
    )

    assert "Current TQQQ position: 4 shares." in text
    assert "Current TQQQ market value: $240.00 (4.8%)." in text
    assert "Pending buy orders: 10 shares, $580.00." in text
    assert "Pending sell orders: 4 shares, $274.00." in text
    assert "Worst-case if all buys fill: $820.00 (16.4%)." in text
    assert "Pending orders exceed max recommended allocation: YES." in text
    assert "Portfolio action: cancel/reduce orders." in text
    assert "Portfolio holdings review:" in text
    assert "Open-order review:" in text
    assert "CANCEL TQQQ buy" in text or "REDUCE TQQQ buy" in text
    assert "REVIEW TQQQ sell" in text or "KEEP TQQQ sell" in text


def test_decision_missing_portfolio_files_do_not_break_decide(tmp_path):
    reports = _write_reports(tmp_path)

    text = render_daily_decision(
        reports_dir=reports,
        positions_path=tmp_path / "missing_positions.csv",
        open_orders_path=tmp_path / "missing_orders.csv",
        market_dir=tmp_path / "missing_market",
        account_value=5000,
    )

    assert text.startswith("ACTION: WAIT")
    assert "Portfolio state:" not in text


def test_decide_reads_saved_account_csv_and_flags_override(tmp_path):
    reports = _write_reports(tmp_path)
    portfolio_dir = tmp_path / "data" / "raw" / "portfolio"
    portfolio_dir.mkdir(parents=True)
    account_path = portfolio_dir / "account.csv"
    account_path.write_text(
        "key,value,updated_at\n"
        "cash,1624.35,2026-05-04\n"
        "account_value,5000,2026-05-04\n",
        encoding="utf-8",
    )

    saved = render_daily_decision(reports_dir=reports)
    overridden = render_daily_decision(
        reports_dir=reports,
        cash=250,
        account_value=10000,
    )

    assert "Account value: $5,000.00" in saved
    assert "Cash: $1,624.35" in saved
    assert "In cash: yes, $1,624.35 supplied." in saved
    assert "Account value: $10,000.00" in overridden
    assert "Cash: $250.00" in overridden


def test_cli_decide_does_not_invoke_workflow_commands(tmp_path, monkeypatch, capsys):
    _write_reports(tmp_path)
    monkeypatch.chdir(tmp_path)

    import trading_lab.cli.main as cli_main

    def fail_run(command):
        raise AssertionError(f"unexpected command run: {command}")

    monkeypatch.setattr(cli_main, "_run", fail_run)
    monkeypatch.setattr(
        sys,
        "argv",
        ["tl", "decide", "--account-value", "5000", "--position", "TQQQ:2", "--cash", "1200"],
    )

    cli_main.main()

    captured = capsys.readouterr()
    assert captured.out.startswith("ACTION: HOLD")
    assert "daily workflow" not in captured.out.lower()


def test_parse_position_rejects_invalid_values(tmp_path):
    reports = _write_reports(tmp_path)

    with pytest.raises(ValueError):
        render_daily_decision(reports_dir=reports, positions=["TQQQ"])
