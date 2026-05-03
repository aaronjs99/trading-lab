from trading_lab.config.targets import PredictionTarget
from trading_lab.signals.multi_regime import _target_column


def test_target_column_is_symbol_generic():
    target = PredictionTarget(
        name="soxl_5d_up5_before_down5",
        symbol="SOXL",
        horizon_days=5,
        up_threshold=0.05,
        down_threshold=-0.05,
    )

    assert _target_column(target) == "SOXL_hit_up_before_down_5d"
