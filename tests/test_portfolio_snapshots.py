from __future__ import annotations

from pathlib import Path

from trading_lab.portfolio.snapshots import (
    append_snapshot,
    build_snapshot_row,
    format_snapshots,
    read_snapshots,
)


SUMMARY = """Date: 2026-05-04
QQQ: 420.00
TQQQ: 60.00
Profile: default
Active target mode: barrier_first_hit
Active target column: TQQQ_hit_up_before_down_5d
Suggested action: WAIT_FOR_PULLBACK
Max TQQQ allocation: 5%
Selected strategy eligible today: NO
- NO: selected model probability 0.580 < threshold 0.65
"""


def _write_snapshot_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    portfolio_dir = tmp_path / "data" / "raw" / "portfolio"
    market_dir = tmp_path / "data" / "raw" / "market"
    reports_dir = tmp_path / "data" / "reports"
    portfolio_dir.mkdir(parents=True)
    market_dir.mkdir(parents=True)
    reports_dir.mkdir(parents=True)
    positions = portfolio_dir / "positions.csv"
    orders = portfolio_dir / "open_orders.csv"
    account = portfolio_dir / "account.csv"
    positions.write_text(
        "symbol,quantity,notes,updated_at\nTQQQ,4,current_position,2026-05-04\n",
        encoding="utf-8",
    )
    orders.write_text(
        "symbol,side,type,quantity,limit_price,time_in_force,status,submitted_at,notes\n"
        "TQQQ,buy,limit,10,58.00,GTC,placed,2026-04-29,current_open_order\n"
        "TQQQ,sell,limit,4,68.50,GTC,placed,2026-04-29,current_open_order\n",
        encoding="utf-8",
    )
    account.write_text(
        "key,value,updated_at\ncash,1000,2026-05-04\naccount_value,5000,2026-05-04\n",
        encoding="utf-8",
    )
    (market_dir / "TQQQ.csv").write_text("date,close\n2026-05-04,60\n", encoding="utf-8")
    (reports_dir / "daily_decision_summary.txt").write_text(SUMMARY, encoding="utf-8")
    (reports_dir / "selected_model_latest_signal.csv").write_text(
        "date,model,probability\n2026-05-04,demo,0.58\n",
        encoding="utf-8",
    )
    return positions, orders, account, market_dir, reports_dir


def test_snapshot_row_creation_from_synthetic_local_files(tmp_path: Path):
    positions, orders, account, market_dir, reports_dir = _write_snapshot_fixture(tmp_path)

    row = build_snapshot_row(
        risk_mode="balanced",
        notes="unit",
        reports_dir=reports_dir,
        positions_path=positions,
        open_orders_path=orders,
        account_path=account,
        market_dir=market_dir,
    )

    assert row["risk_mode"] == "balanced"
    assert row["action"] == "HOLD"
    assert row["account_value"] == "5000"
    assert row["cash"] == "1000"
    assert row["known_equity_value"] == "240"
    assert row["known_total_value"] == "1240"
    assert row["traded_symbol"] == "TQQQ"
    assert row["traded_quantity"] == "4"
    assert row["pending_buy_notional"] == "580"
    assert row["pending_sell_notional"] == "274"
    assert row["pending_buy_count"] == "1"
    assert row["pending_sell_count"] == "1"
    assert row["model_probability"] == "0.58"
    assert row["active_target_mode"] == "barrier_first_hit"
    assert row["active_target_column"] == "TQQQ_hit_up_before_down_5d"
    assert row["current_traded_price"] == "60"
    assert row["notes"] == "unit"


def test_missing_local_files_produce_best_effort_snapshot(tmp_path: Path):
    row = build_snapshot_row(
        reports_dir=tmp_path / "missing_reports",
        positions_path=tmp_path / "missing_positions.csv",
        open_orders_path=tmp_path / "missing_orders.csv",
        account_path=tmp_path / "missing_account.csv",
        market_dir=tmp_path / "missing_market",
    )

    assert row["traded_symbol"]
    assert row["positions_count"] == "0"
    assert row["open_orders_count"] == "0"
    assert row["known_equity_value"] == "0"
    assert row["action"] == ""


def test_snapshot_appends_instead_of_overwriting(tmp_path: Path):
    positions, orders, account, market_dir, reports_dir = _write_snapshot_fixture(tmp_path)
    path = tmp_path / "data" / "processed" / "portfolio" / "snapshots.csv"

    append_snapshot(
        path=path,
        notes="first",
        reports_dir=reports_dir,
        positions_path=positions,
        open_orders_path=orders,
        account_path=account,
        market_dir=market_dir,
    )
    append_snapshot(
        path=path,
        notes="second",
        reports_dir=reports_dir,
        positions_path=positions,
        open_orders_path=orders,
        account_path=account,
        market_dir=market_dir,
    )

    rows = read_snapshots(path, limit=10)
    assert [row["notes"] for row in rows] == ["first", "second"]


def test_cli_portfolio_snapshot_and_snapshots_commands(tmp_path: Path, monkeypatch, capsys):
    _write_snapshot_fixture(tmp_path)
    monkeypatch.chdir(tmp_path)

    import trading_lab.cli.main as cli_main

    monkeypatch.setattr("sys.argv", ["tl", "portfolio", "snapshot", "--risk-mode", "balanced", "--notes", "cli"])
    cli_main.main()
    assert "Recorded local-only portfolio snapshot" in capsys.readouterr().out
    assert (tmp_path / "data" / "processed" / "portfolio" / "snapshots.csv").exists()

    monkeypatch.setattr("sys.argv", ["tl", "portfolio", "snapshots", "--limit", "1"])
    cli_main.main()
    out = capsys.readouterr().out
    assert "Recent portfolio snapshots:" in out
    assert "balanced" in out
    assert "notes=cli" in out


def test_cli_decide_snapshot_writes_snapshot_without_workflow(tmp_path: Path, monkeypatch, capsys):
    _write_snapshot_fixture(tmp_path)
    monkeypatch.chdir(tmp_path)

    import trading_lab.cli.main as cli_main

    def fail_run(command):
        raise AssertionError(f"unexpected command run: {command}")

    monkeypatch.setattr(cli_main, "_run", fail_run)
    monkeypatch.setattr(
        "sys.argv",
        [
            "tl",
            "decide",
            "--risk-mode",
            "balanced",
            "--account-value",
            "6000",
            "--cash",
            "1200",
            "--snapshot",
            "--snapshot-notes",
            "decide",
        ],
    )
    cli_main.main()

    out = capsys.readouterr().out
    assert "ACTION:" in out
    assert "Recorded local-only portfolio snapshot" in out
    rows = read_snapshots(tmp_path / "data" / "processed" / "portfolio" / "snapshots.csv")
    assert rows[-1]["notes"] == "decide"
    assert rows[-1]["account_value"] == "6000"
    assert rows[-1]["cash"] == "1200"


def test_format_snapshots_handles_empty_and_recent_rows():
    assert format_snapshots([]) == "No local portfolio snapshots found."
    text = format_snapshots(
        [
            {
                "timestamp": "2026-05-04T09:30:00",
                "risk_mode": "balanced",
                "action": "HOLD",
                "traded_symbol": "TQQQ",
                "traded_value": "240",
                "pending_buy_notional": "580",
                "pending_sell_notional": "274",
                "notes": "x",
            }
        ]
    )
    assert "$240.00" in text
    assert "notes=x" in text
