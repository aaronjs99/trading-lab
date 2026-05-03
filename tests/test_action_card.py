from pathlib import Path

import pandas as pd

from trading_lab.dashboard.action_card import build_action_card


def test_action_card_builds_from_synthetic_reports(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    market_dir = tmp_path / "data" / "processed" / "market"
    reports_dir = tmp_path / "data" / "reports"
    market_dir.mkdir(parents=True)
    reports_dir.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "date": "2026-05-01",
                "TQQQ": 60.0,
                "QQQ": 420.0,
                "QQQ_uptrend_20_50": True,
                "QQQ_dist_ma_20": 0.06,
                "QQQ_dist_ma_50": 0.08,
                "TQQQ_drawdown_from_20d_high": -0.01,
            }
        ]
    ).to_csv(market_dir / "market_features.csv", index=False)
    pd.DataFrame([{"model": "logistic_regression", "probability": 0.58}]).to_csv(
        reports_dir / "selected_model_latest_signal.csv",
        index=False,
    )

    card = build_action_card()

    assert not card.empty
    assert {"section", "item", "value", "detail"}.issubset(card.columns)
    assert "action" in set(card["item"])
