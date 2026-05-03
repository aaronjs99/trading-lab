from __future__ import annotations

import sys
from pathlib import Path

import pytest

from trading_lab.decision import MISSING_REPORTS_MESSAGE, render_daily_decision


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

    assert text == MISSING_REPORTS_MESSAGE


def test_decision_renders_from_synthetic_report_fixtures(tmp_path):
    reports = _write_reports(tmp_path)

    text = render_daily_decision(
        reports_dir=reports,
        account_value=5000,
        cash=1200,
    )

    assert text.startswith("ACTION: WAIT")
    assert "Now: wait for the TQQQ pullback ladder" in text
    assert "Buy capacity now: $250.00" in text
    assert "shallow_pullback: limit $58.20" in text
    assert "selected model probability 0.580 < threshold 0.65" in text
    assert "Already holding: no TQQQ position supplied." in text
    assert "In cash: yes, $1,200.00 supplied." in text


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
