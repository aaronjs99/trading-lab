import pandas as pd

from trading_lab.models.zoo import ModelConfig, safe_roc_auc


def test_model_config_defaults_are_trade_ready():
    cfg = ModelConfig("random_forest")

    assert cfg.threshold == 0.50
    assert cfg.take_profit == 0.04
    assert cfg.stop_loss == 0.04
    assert cfg.max_hold == 3
    assert cfg.require_trend is True


def test_safe_roc_auc_returns_nan_for_single_class():
    y = pd.Series([1, 1, 1])
    score = safe_roc_auc(y, [0.7, 0.8, 0.9])

    assert pd.isna(score)
