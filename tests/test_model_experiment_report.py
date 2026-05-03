from pathlib import Path

import pandas as pd

from trading_lab.config import TradingConfig
from trading_lab.models.experiment_report import build_model_experiment_report, write_model_experiment_report


def test_model_experiment_report_consolidates_zoo_and_target_metadata(tmp_path: Path):
    zoo_path = tmp_path / "model_zoo_ranking.csv"
    feature_path = tmp_path / "market_features.csv"
    csv_path = tmp_path / "report.csv"
    md_path = tmp_path / "report.md"

    pd.DataFrame(
        [
            {
                "model": "random_forest",
                "test_rows": 12,
                "mean_roc_auc": 0.61,
                "mean_brier": 0.22,
                "mean_win_rate": 0.55,
                "mean_profit_factor": 1.8,
                "worst_fold_return": -0.02,
                "worst_fold_drawdown": -0.08,
            }
        ]
    ).to_csv(zoo_path, index=False)
    pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=4),
            "SOXL_ret_1d": [0.01, 0.02, 0.03, 0.04],
            "XLK_ret_1d": [0.01, 0.02, 0.03, 0.04],
            "SPY_ret_1d": [0.01, 0.02, 0.03, 0.04],
            "XLK_uptrend_20_50": [True, True, False, True],
            "SOXL_hit_up_before_down_5d": [1, 0, 1, 0],
        }
    ).to_csv(feature_path, index=False)

    config = TradingConfig(traded_symbol="SOXL", benchmark_symbol="XLK")
    report = build_model_experiment_report(
        model_zoo_path=zoo_path,
        feature_path=feature_path,
        config=config,
    )

    assert report.loc[0, "target_mode"] == "barrier_first_hit"
    assert report.loc[0, "target_col"] == "SOXL_hit_up_before_down_5d"
    assert report.loc[0, "positive_rate"] == 0.5

    written = write_model_experiment_report(
        csv_path=csv_path,
        md_path=md_path,
        model_zoo_path=zoo_path,
        feature_path=feature_path,
        config=config,
    )

    assert len(written) == 1
    assert csv_path.exists()
    assert "random_forest" in md_path.read_text(encoding="utf-8")
