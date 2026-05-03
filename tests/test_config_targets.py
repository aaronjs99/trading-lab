from trading_lab.config import TradingConfig
from trading_lab.config.targets import PredictionTarget, default_prediction_targets


def test_prediction_target_description_is_symbol_generic():
    target = PredictionTarget(
        name="soxl_5d",
        symbol="SOXL",
        horizon_days=5,
        up_threshold=0.05,
        down_threshold=-0.05,
    )

    assert "SOXL hits +5%" in target.description
    assert "within 5 trading days" in target.description


def test_default_prediction_targets_follow_config_symbol():
    cfg = TradingConfig(traded_symbol="SOXL", benchmark_symbol="SOXX")
    targets = default_prediction_targets(cfg)

    assert [target.symbol for target in targets] == ["SOXL", "SOXL"]
    assert targets[0].name.startswith("soxl_")
