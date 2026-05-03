import pandas as pd

from trading_lab.config import TradingConfig
from trading_lab.config.targets import PredictionTarget
from trading_lab.models.live import score_selected_model_latest
from trading_lab.models.target_selection import SelectedTarget


def test_selected_model_latest_accepts_selected_target_without_tqqq_assumptions(tmp_path, monkeypatch):
    feature_path = tmp_path / "features.csv"
    out_path = tmp_path / "signal.csv"
    prices = [100, 106, 98, 109, 101, 112, 103, 115, 104, 118, 106, 121]
    pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=len(prices)),
            "SOXL": prices,
            "SOXL_ret_1d": pd.Series(prices).pct_change().fillna(0.0),
            "SOXL_dist_ma_20": [0.01] * len(prices),
            "SOXL_vol_5d": [0.2] * len(prices),
            "XLK_ret_1d": [0.01, -0.01] * 6,
            "XLK_uptrend_20_50": [True] * len(prices),
            "SPY_ret_1d": [0.005, -0.005] * 6,
        }
    ).to_csv(feature_path, index=False)

    class Winner:
        model = "logistic_regression"
        mean_profit_factor = 1.2
        worst_fold_drawdown = -0.2

    monkeypatch.setattr("trading_lab.models.live.select_model_zoo_winner", lambda: Winner())
    target = PredictionTarget(
        name="soxl_threshold",
        symbol="SOXL",
        horizon_days=1,
        up_threshold=0.05,
        down_threshold=-0.05,
        mode="threshold_horizon_return",
    )
    selected = SelectedTarget(
        target=target,
        target_name=target.name,
        target_mode=target.mode,
        target_col="SOXL_threshold_horizon_return_up5pct_1d",
        model="logistic_regression",
        mean_roc_auc=0.7,
        mean_profit_factor=1.5,
        worst_fold_drawdown=-0.1,
        score=0.4,
        source="experiment_report",
    )

    out = score_selected_model_latest(
        feature_path=feature_path,
        out_path=out_path,
        config=TradingConfig(
            traded_symbol="SOXL",
            benchmark_symbol="XLK",
            use_experiment_selected_target=True,
        ),
        selected_target=selected,
    )

    assert out.loc[0, "active_target_mode"] == "threshold_horizon_return"
    assert out.loc[0, "active_target_col"] == "SOXL_threshold_horizon_return_up5pct_1d"
    assert {
        "date",
        "model",
        "probability",
        "train_rows",
        "target_positive_rate",
        "selected_model_profit_factor",
        "selected_model_worst_drawdown",
        "configured_target_mode",
        "active_target_mode",
        "active_target_col",
        "target_source",
    }.issubset(out.columns)
    assert out_path.exists()
