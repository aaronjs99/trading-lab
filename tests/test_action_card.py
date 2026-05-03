from pathlib import Path

import pytest

from trading_lab.dashboard.action_card import build_action_card


REQUIRED = [
    Path("data/processed/market/market_features.csv"),
    Path("data/reports/selected_model_latest_signal.csv"),
]


def test_action_card_builds_when_reports_exist():
    missing = [path for path in REQUIRED if not path.exists()]
    if missing:
        pytest.skip(f"reports not available: {missing}")

    card = build_action_card()

    assert not card.empty
    assert {"section", "item", "value", "detail"}.issubset(card.columns)
    assert "action" in set(card["item"])
