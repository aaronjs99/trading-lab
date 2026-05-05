from __future__ import annotations

from datetime import datetime
from pathlib import Path

from trading_lab.portfolio.outcomes import (
    append_outcome,
    build_outcome_row,
    format_outcomes,
    read_outcomes,
    update_outcomes,
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

Suggested TQQQ ladder:
- better_pullback: limit $58.20, allocation 1.2%, synthetic.
"""


def _write_outcome_fixture(tmp_path: Path, *, future_days: int = 10) -> tuple[Path, Path, Path, Path, Path]:
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
    prices = ["date,close\n", "2026-05-04,60\n"]
    for index in range(1, future_days + 1):
        prices.append(f"2026-05-{4 + index:02d},{60 + index}\n")
    (market_dir / "TQQQ.csv").write_text("".join(prices), encoding="utf-8")
    (reports_dir / "daily_decision_summary.txt").write_text(SUMMARY, encoding="utf-8")
    (reports_dir / "selected_model_latest_signal.csv").write_text(
        "date,model,probability\n2026-05-04,demo,0.58\n",
        encoding="utf-8",
    )
    return positions, orders, account, market_dir, reports_dir


def test_record_outcome_writes_local_row_from_synthetic_files(tmp_path: Path):
    positions, orders, account, market_dir, reports_dir = _write_outcome_fixture(tmp_path)
    path = tmp_path / "data" / "processed" / "portfolio" / "decision_outcomes.csv"

    result = append_outcome(
        path=path,
        risk_mode="balanced",
        notes="unit",
        reports_dir=reports_dir,
        positions_path=positions,
        open_orders_path=orders,
        account_path=account,
        market_dir=market_dir,
        now=datetime(2026, 5, 4, 9, 30),
    )

    assert result.path == path
    rows = read_outcomes(path, limit=10)
    assert rows[-1]["risk_mode"] == "balanced"
    assert rows[-1]["action"] == "HOLD"
    assert rows[-1]["traded_symbol"] == "TQQQ"
    assert rows[-1]["traded_price_at_decision"] == "60"
    assert rows[-1]["model_probability"] == "0.58"
    assert rows[-1]["active_target_mode"] == "barrier_first_hit"
    assert rows[-1]["active_target_column"] == "TQQQ_hit_up_before_down_5d"
    assert rows[-1]["suggested_report_action"] == "WAIT_FOR_PULLBACK"
    assert rows[-1]["strategy_eligible_today"] == "NO"
    assert rows[-1]["max_exposure"] == "250"
    assert rows[-1]["current_exposure"] == "240"
    assert rows[-1]["pending_buy_notional"] == "580"
    assert rows[-1]["pending_sell_notional"] == "274"
    assert rows[-1]["outcome_status"] == "PENDING"
    assert "Cancel/reduce current pending TQQQ buys" in rows[-1]["suggested_order_summary"]
    assert rows[-1]["notes"] == "unit"


def test_outcome_appends_instead_of_overwriting(tmp_path: Path):
    positions, orders, account, market_dir, reports_dir = _write_outcome_fixture(tmp_path)
    path = tmp_path / "data" / "processed" / "portfolio" / "decision_outcomes.csv"

    for note in ("first", "second"):
        append_outcome(
            path=path,
            notes=note,
            reports_dir=reports_dir,
            positions_path=positions,
            open_orders_path=orders,
            account_path=account,
            market_dir=market_dir,
            now=datetime(2026, 5, 4, 9, 30),
        )

    assert [row["notes"] for row in read_outcomes(path, limit=10)] == ["first", "second"]


def test_outcome_update_fills_future_prices_and_returns(tmp_path: Path):
    positions, orders, account, market_dir, reports_dir = _write_outcome_fixture(tmp_path, future_days=10)
    path = tmp_path / "data" / "processed" / "portfolio" / "decision_outcomes.csv"
    append_outcome(
        path=path,
        reports_dir=reports_dir,
        positions_path=positions,
        open_orders_path=orders,
        account_path=account,
        market_dir=market_dir,
        now=datetime(2026, 5, 4, 9, 30),
    )

    assert update_outcomes(path=path, market_dir=market_dir) == 1
    row = read_outcomes(path, limit=1)[0]
    assert row["future_price_1d"] == "61"
    assert row["future_price_3d"] == "63"
    assert row["future_price_5d"] == "65"
    assert row["future_price_10d"] == "70"
    assert row["return_1d"] == "0.0166667"
    assert row["return_10d"] == "0.166667"
    assert row["outcome_status"] == "UPDATED"


def test_outcome_update_insufficient_future_data_remains_pendingish(tmp_path: Path):
    positions, orders, account, market_dir, reports_dir = _write_outcome_fixture(tmp_path, future_days=3)
    path = tmp_path / "data" / "processed" / "portfolio" / "decision_outcomes.csv"
    append_outcome(
        path=path,
        reports_dir=reports_dir,
        positions_path=positions,
        open_orders_path=orders,
        account_path=account,
        market_dir=market_dir,
        now=datetime(2026, 5, 4, 9, 30),
    )

    update_outcomes(path=path, market_dir=market_dir)
    row = read_outcomes(path, limit=1)[0]
    assert row["future_price_3d"] == "63"
    assert row["future_price_5d"] == ""
    assert row["outcome_status"] == "INSUFFICIENT_FUTURE_DATA"


def test_outcome_missing_price_handled_cleanly(tmp_path: Path):
    positions, orders, account, market_dir, reports_dir = _write_outcome_fixture(tmp_path)
    path = tmp_path / "data" / "processed" / "portfolio" / "decision_outcomes.csv"
    append_outcome(
        path=path,
        reports_dir=reports_dir,
        positions_path=positions,
        open_orders_path=orders,
        account_path=account,
        market_dir=market_dir,
        now=datetime(2026, 5, 4, 9, 30),
    )
    (market_dir / "TQQQ.csv").unlink()

    update_outcomes(path=path, market_dir=market_dir)
    row = read_outcomes(path, limit=1)[0]

    assert row["outcome_status"] == "PRICE_MISSING"
    assert row["current_price"] == "60"


def test_cli_outcome_commands_and_decide_record_do_not_run_workflow(tmp_path, monkeypatch, capsys):
    _write_outcome_fixture(tmp_path)
    monkeypatch.chdir(tmp_path)

    import trading_lab.cli.main as cli_main

    def fail_run(command):
        raise AssertionError(f"unexpected command run: {command}")

    monkeypatch.setattr(cli_main, "_run", fail_run)
    monkeypatch.setattr(
        "sys.argv",
        ["tl", "portfolio", "outcome-record", "--risk-mode", "balanced", "--notes", "cli"],
    )
    cli_main.main()
    assert "Recorded local-only decision outcome row" in capsys.readouterr().out

    monkeypatch.setattr("sys.argv", ["tl", "portfolio", "outcomes", "--limit", "1"])
    cli_main.main()
    out = capsys.readouterr().out
    assert "Recent decision outcomes:" in out
    assert "notes=cli" in out

    monkeypatch.setattr("sys.argv", ["tl", "portfolio", "outcome-update"])
    cli_main.main()
    assert "Updated" in capsys.readouterr().out

    monkeypatch.setattr(
        "sys.argv",
        ["tl", "decide", "--risk-mode", "balanced", "--record-outcome", "--outcome-notes", "decide"],
    )
    cli_main.main()
    out = capsys.readouterr().out
    assert "ACTION:" in out
    assert "Recorded local-only decision outcome row" in out
    assert read_outcomes(tmp_path / "data" / "processed" / "portfolio" / "decision_outcomes.csv")[-1][
        "notes"
    ] == "decide"


def test_top_level_outcome_aliases(tmp_path, monkeypatch, capsys):
    _write_outcome_fixture(tmp_path)
    monkeypatch.chdir(tmp_path)

    import trading_lab.cli.main as cli_main

    monkeypatch.setattr("sys.argv", ["tl", "outcome", "record", "--notes", "alias"])
    cli_main.main()
    assert "Recorded local-only decision outcome row" in capsys.readouterr().out

    monkeypatch.setattr("sys.argv", ["tl", "outcome", "list", "--limit", "1"])
    cli_main.main()
    assert "notes=alias" in capsys.readouterr().out

    monkeypatch.setattr("sys.argv", ["tl", "outcome", "update"])
    cli_main.main()
    assert "Updated" in capsys.readouterr().out


def test_format_outcomes_handles_empty_and_recent_rows():
    assert format_outcomes([]) == "No local decision outcomes found."
    text = format_outcomes(
        [
            {
                "decision_timestamp": "2026-05-04T09:30:00",
                "risk_mode": "balanced",
                "action": "HOLD",
                "traded_symbol": "TQQQ",
                "traded_price_at_decision": "60",
                "return_5d": "0.05",
                "outcome_status": "UPDATED",
                "notes": "x",
            }
        ]
    )
    assert "$60.00" in text
    assert "5.0%" in text
    assert "notes=x" in text
