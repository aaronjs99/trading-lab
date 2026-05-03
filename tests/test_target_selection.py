import pandas as pd

from trading_lab.config import TradingConfig
from trading_lab.models.target_selection import select_best_target, selected_prediction_target


def _report():
    return pd.DataFrame(
        [
            {
                "target_name": "soxl_5d_up5_before_down5_barrier_first_hit",
                "target_mode": "barrier_first_hit",
                "target_col": "SOXL_hit_up_before_down_5d",
                "model": "random_forest",
                "mean_roc_auc": 0.60,
                "mean_profit_factor": float("inf"),
                "worst_fold_drawdown": -0.01,
                "score": 0.9,
            },
            {
                "target_name": "soxl_5d_up5_before_down5_threshold_horizon_return",
                "target_mode": "threshold_horizon_return",
                "target_col": "SOXL_threshold_horizon_return_up5pct_5d",
                "model": "logistic_regression",
                "mean_roc_auc": 0.70,
                "mean_profit_factor": 1.5,
                "worst_fold_drawdown": -0.10,
                "score": 0.5,
            },
            {
                "target_name": "soxl_5d_up5_before_down5_horizon_return",
                "target_mode": "horizon_return",
                "target_col": "SOXL_horizon_return_5d",
                "model": "random_forest_deeper",
                "mean_roc_auc": 0.65,
                "mean_profit_factor": 2.0,
                "worst_fold_drawdown": -0.05,
                "score": 0.8,
            },
        ]
    )


def test_default_config_keeps_primary_target():
    selection = selected_prediction_target(
        TradingConfig(traded_symbol="SOXL", benchmark_symbol="XLK"),
        report_df=_report(),
    )

    assert selection.source == "default_config"
    assert selection.target_mode == "barrier_first_hit"
    assert selection.target_col == "SOXL_hit_up_before_down_5d"


def test_experiment_selected_config_picks_best_finite_candidate():
    config = TradingConfig(
        traded_symbol="SOXL",
        benchmark_symbol="XLK",
        use_experiment_selected_target=True,
    )

    selection = selected_prediction_target(config, report_df=_report())

    assert selection.source == "experiment_report"
    assert selection.target_mode == "threshold_horizon_return"
    assert selection.target_col == "SOXL_threshold_horizon_return_up5pct_5d"
    assert selection.model == "logistic_regression"


def test_missing_report_falls_back_cleanly():
    config = TradingConfig(
        traded_symbol="SOXL",
        benchmark_symbol="XLK",
        use_experiment_selected_target=True,
    )

    selection = selected_prediction_target(config, report_df=pd.DataFrame())

    assert selection.source == "default_config"
    assert selection.fallback_reason == "experiment report missing or empty"


def test_select_best_target_prefers_finite_profit_factor_before_inf():
    row = select_best_target(_report())

    assert row is not None
    assert row["model"] == "logistic_regression"
