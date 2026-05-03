from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pandas as pd

from trading_lab.workflows.demo import DEMO_ROOT, run_demo


def test_demo_fixtures_exist_and_are_synthetic():
    market_dir = DEMO_ROOT / "market"
    paths = sorted(market_dir.glob("*.csv"))

    assert {path.name for path in paths} >= {"SOXL.csv", "XLK.csv", "SPY.csv"}
    for path in paths:
        text = path.read_text(encoding="utf-8")
        df = pd.read_csv(path)
        assert {"date", "close"}.issubset(df.columns)
        assert len(df) >= 60
        assert not any(secret in text.lower() for secret in ["robinhood", "account", "password", "token"])


def test_demo_command_runs_without_network_or_private_data():
    out_root = run_demo()

    assert out_root.exists()
    assert out_root.name.startswith("trading_lab_demo_")
    assert (out_root / "data" / "reports" / "action_card.csv").exists()
    assert (out_root / "data" / "reports" / "daily_decision_summary.txt").exists()
    assert Path.cwd() not in out_root.parents


def test_demo_cli_command_runs():
    completed = subprocess.run(
        [sys.executable, "-B", "-m", "trading_lab.cli.main", "demo"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "== trading-lab demo ==" in completed.stdout
    assert "SOXL" in completed.stdout
