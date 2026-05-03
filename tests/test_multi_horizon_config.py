from pathlib import Path

from trading_lab.config.targets import PredictionTarget
from trading_lab.signals.multi_regime import _target_column


def test_multi_regime_uses_config_targets():
    source = Path("src/trading_lab/signals/multi_regime.py").read_text(encoding="utf-8")

    assert "default_prediction_targets" in source
    assert "PredictionTarget" in source
    assert "target.name" in source
    assert "target.description" in source
    assert '"tqqq_5d_up5_before_down5"' not in source
    assert '"tqqq_10d_up8_before_down8"' not in source
    assert '"TQQQ hits +5% before -5% within 5 trading days"' not in source


def test_target_column_is_symbol_generic():
    target = PredictionTarget(
        name="soxl_5d_up5_before_down5",
        symbol="SOXL",
        horizon_days=5,
        up_threshold=0.05,
        down_threshold=-0.05,
    )

    assert _target_column(target) == "SOXL_hit_up_before_down_5d"
