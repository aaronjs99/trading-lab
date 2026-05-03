from pathlib import Path

import pytest

from trading_lab.dashboard.daily import build_daily_decision_summary


REQUIRED_REPORTS = [
    Path("data/processed/market/market_features.csv"),
    Path("data/reports/latest_regime_signal.csv"),
    Path("data/reports/selected_model_latest_signal.csv"),
    Path("data/reports/walk_forward_strategy_ranking.csv"),
]


def test_daily_summary_builds_when_reports_exist():
    missing = [path for path in REQUIRED_REPORTS if not path.exists()]
    if missing:
        pytest.skip(f"reports not available in test environment: {missing}")

    text = build_daily_decision_summary()

    assert "Suggested action:" in text
    assert "Selected walk-forward strategy:" in text
    assert "Personal trading edge:" in text
