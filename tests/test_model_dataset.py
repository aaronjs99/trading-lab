import pandas as pd

from trading_lab.config import TradingConfig
from trading_lab.models.dataset import (
    feature_columns,
    latest_feature_row,
    primary_prediction_target,
    supervised_frame,
    target_column,
    train_test_split_time,
    walk_forward_folds,
)


def _frame():
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=6),
            "SOXL": [10, 11, 12, 13, 14, 15],
            "SOXL_ret_1d": [None, 0.1, 0.09, 0.08, 0.07, 0.06],
            "SOXL_dist_ma_20": [0.0, 0.01, 0.02, 0.03, 0.04, 0.05],
            "SOXL_vol_5d": [0.2] * 6,
            "SOXL_drawdown_from_20d_high": [0.0] * 6,
            "XLK_ret_1d": [None, 0.02, 0.03, 0.04, 0.05, 0.06],
            "XLK_uptrend_20_50": [True] * 6,
            "SPY_ret_1d": [None, 0.01, 0.01, 0.01, 0.01, 0.01],
            "SOXL_hit_up_before_down_5d": [1, 0, 1, 0, 1, None],
            "TQQQ_ret_1d": [0.5] * 6,
        }
    )


def test_feature_columns_use_configured_symbols_not_tqqq_defaults():
    config = TradingConfig(traded_symbol="SOXL", benchmark_symbol="XLK")

    cols = feature_columns(_frame(), config)

    assert "SOXL_ret_1d" in cols
    assert "XLK_uptrend_20_50" in cols
    assert "TQQQ_ret_1d" not in cols


def test_supervised_frame_builds_target_and_drops_incomplete_rows():
    config = TradingConfig(traded_symbol="SOXL", benchmark_symbol="XLK")
    target = primary_prediction_target(config)

    work, cols, target_col = supervised_frame(_frame(), target=target, config=config)

    assert target_column(target) == target_col
    assert target_col == "SOXL_hit_up_before_down_5d"
    assert "target" in work.columns
    assert len(work) == 4
    assert cols


def test_latest_feature_row_and_time_splits_are_chronological():
    config = TradingConfig(traded_symbol="SOXL", benchmark_symbol="XLK")
    latest, _ = latest_feature_row(_frame(), config)
    train, test = train_test_split_time(_frame(), test_fraction=0.33)
    folds = walk_forward_folds(_frame(), n_folds=2)

    assert latest.iloc[0]["date"] == pd.Timestamp("2024-01-06")
    assert train["date"].max() < test["date"].min()
    assert len(folds) == 2
