from pathlib import Path

import pandas as pd

from trading_lab.config import TradingConfig
from trading_lab.models.experiment_report import (
    build_model_experiment_report,
    rank_model_experiment_report,
    write_model_experiment_report,
)


def _write_model_zoo(path: Path) -> None:
    pd.DataFrame(
        [
            {
                "model": "logistic_regression",
                "threshold": 0.50,
                "take_profit": 0.05,
                "stop_loss": 0.05,
                "max_hold": 3,
                "require_trend": True,
                "max_ext20": 0.04,
            }
        ]
    ).to_csv(path, index=False)


def _write_features(path: Path, include_only_barrier: bool = False) -> None:
    prices = [
        100,
        108,
        96,
        111,
        93,
        115,
        95,
        118,
        97,
        121,
        99,
        124,
        101,
        127,
        103,
        130,
        104,
        128,
        106,
        132,
        108,
        134,
        110,
        136,
        112,
        138,
        114,
        140,
        116,
        142,
    ]
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=len(prices)),
            "SOXL": prices,
            "SOXL_ret_1d": pd.Series(prices).pct_change().fillna(0.0),
            "SOXL_dist_ma_20": [0.01] * len(prices),
            "SOXL_vol_5d": [0.2] * len(prices),
            "SOXL_drawdown_from_20d_high": [-0.01] * len(prices),
            "XLK_ret_1d": [0.01, -0.01] * 15,
            "XLK_dist_ma_20": [0.01] * len(prices),
            "XLK_uptrend_20_50": [True] * len(prices),
            "SPY_ret_1d": [0.005, -0.005] * 15,
        }
    )
    if include_only_barrier:
        df["SOXL_hit_up_before_down_5d"] = ([1, 0] * 15)
    df.to_csv(path, index=False)


def test_model_experiment_report_includes_all_target_modes(tmp_path: Path):
    zoo_path = tmp_path / "model_zoo_ranking.csv"
    feature_path = tmp_path / "market_features.csv"
    _write_model_zoo(zoo_path)
    _write_features(feature_path)

    report = build_model_experiment_report(
        model_zoo_path=zoo_path,
        feature_path=feature_path,
        config=TradingConfig(traded_symbol="SOXL", benchmark_symbol="XLK"),
    )

    assert set(report["target_mode"]) == {
        "barrier_first_hit",
        "horizon_return",
        "threshold_horizon_return",
    }
    assert set(report["model"]) == {"logistic_regression"}


def test_model_experiment_report_generates_missing_target_columns(tmp_path: Path):
    zoo_path = tmp_path / "model_zoo_ranking.csv"
    feature_path = tmp_path / "market_features.csv"
    _write_model_zoo(zoo_path)
    _write_features(feature_path, include_only_barrier=True)

    report = build_model_experiment_report(
        model_zoo_path=zoo_path,
        feature_path=feature_path,
        config=TradingConfig(traded_symbol="SOXL", benchmark_symbol="XLK"),
    )

    assert "SOXL_horizon_return_5d" in set(report["target_col"])
    assert "SOXL_threshold_horizon_return_up5pct_5d" in set(report["target_col"])
    assert report["train_rows"].notna().all()


def test_model_experiment_report_sorts_candidates():
    report = pd.DataFrame(
        [
            {
                "target_name": "a",
                "target_mode": "barrier_first_hit",
                "target_col": "a",
                "model": "bad_inf",
                "mean_roc_auc": 0.99,
                "mean_profit_factor": float("inf"),
                "worst_fold_drawdown": -0.01,
            },
            {
                "target_name": "b",
                "target_mode": "horizon_return",
                "target_col": "b",
                "model": "best_finite",
                "mean_roc_auc": 0.70,
                "mean_profit_factor": 2.0,
                "worst_fold_drawdown": -0.05,
            },
            {
                "target_name": "c",
                "target_mode": "threshold_horizon_return",
                "target_col": "c",
                "model": "lower_auc",
                "mean_roc_auc": 0.60,
                "mean_profit_factor": 3.0,
                "worst_fold_drawdown": -0.02,
            },
        ]
    )

    ranked = rank_model_experiment_report(report)

    assert ranked.iloc[0]["model"] == "best_finite"
    assert ranked.iloc[-1]["model"] == "bad_inf"


def test_write_model_experiment_report_outputs_best_candidate_section(tmp_path: Path):
    zoo_path = tmp_path / "model_zoo_ranking.csv"
    feature_path = tmp_path / "market_features.csv"
    csv_path = tmp_path / "report.csv"
    md_path = tmp_path / "report.md"
    _write_model_zoo(zoo_path)
    _write_features(feature_path)

    written = write_model_experiment_report(
        csv_path=csv_path,
        md_path=md_path,
        model_zoo_path=zoo_path,
        feature_path=feature_path,
        config=TradingConfig(traded_symbol="SOXL", benchmark_symbol="XLK"),
    )

    assert len(written) == 6
    assert csv_path.exists()
    assert "## Best Candidate" in md_path.read_text(encoding="utf-8")
