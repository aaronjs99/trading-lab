from pathlib import Path

import pandas as pd

from trading_lab.features.market import (
    add_price_features,
    add_uptrend_feature,
    configured_feature_symbols,
    merge_price_frames,
)


def test_market_features_uses_generic_target_generation():
    source = Path("src/trading_lab/features/market.py").read_text(encoding="utf-8")

    assert "default_prediction_targets" in source
    assert "add_prediction_targets" in source
    assert "def add_forward_labels" not in source
    assert "TQQQ_hit_up_before_down_5d" not in source


def test_configured_feature_symbols_filters_available_symbols():
    symbols = configured_feature_symbols(["SPY", "QQQ", "TQQQ", "SQQQ"], {"SPY", "TQQQ"})

    assert symbols == ["SPY", "TQQQ"]


def test_add_price_features_adds_expected_columns():
    df = pd.DataFrame({"ABC": list(range(1, 121))})

    out = add_price_features(df, "ABC")

    assert "ABC_ret_5d" in out.columns
    assert "ABC_ma_20" in out.columns
    assert "ABC_dist_ma_50" in out.columns
    assert "ABC_vol_20d" in out.columns
    assert "ABC_drawdown_from_60d_high" in out.columns


def test_add_uptrend_feature_uses_existing_ma_columns():
    df = pd.DataFrame({"ABC_ma_20": [2, 3], "ABC_ma_50": [1, 4]})

    out = add_uptrend_feature(df, "ABC")

    assert list(out["ABC_uptrend_20_50"]) == [True, False]


def test_merge_price_frames_merges_by_date(tmp_path: Path):
    a = tmp_path / "AAA.csv"
    b = tmp_path / "BBB.csv"

    pd.DataFrame({"date": ["2020-01-01"], "close": [1.0]}).to_csv(a, index=False)
    pd.DataFrame({"date": ["2020-01-01"], "close": [2.0]}).to_csv(b, index=False)

    out = merge_price_frames([a, b])

    assert {"date", "AAA", "BBB"}.issubset(out.columns)
