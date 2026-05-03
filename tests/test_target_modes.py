import pandas as pd

from trading_lab.config.targets import PredictionTarget
from trading_lab.features.targets import add_prediction_target, target_column


def test_horizon_return_target_marks_positive_forward_return():
    target = PredictionTarget(
        name="abc_positive_2d",
        symbol="ABC",
        horizon_days=2,
        up_threshold=0.05,
        down_threshold=-0.05,
        mode="horizon_return",
    )
    df = pd.DataFrame({"ABC": [100.0, 95.0, 101.0, 90.0]})

    out = add_prediction_target(df, target)

    assert target_column(target) == "ABC_horizon_return_2d"
    assert out.loc[0, target_column(target)] == 1
    assert out.loc[1, target_column(target)] == 0


def test_threshold_horizon_return_uses_configured_up_threshold():
    target = PredictionTarget(
        name="abc_up5_2d",
        symbol="ABC",
        horizon_days=2,
        up_threshold=0.05,
        down_threshold=-0.05,
        mode="threshold_horizon_return",
    )
    df = pd.DataFrame({"ABC": [100.0, 103.0, 104.0, 109.0]})

    out = add_prediction_target(df, target)

    assert target_column(target) == "ABC_threshold_horizon_return_up5pct_2d"
    assert out.loc[0, target_column(target)] == 0
    assert out.loc[1, target_column(target)] == 1


def test_default_barrier_target_column_remains_backward_compatible():
    target = PredictionTarget(
        name="abc_3d_up5_before_down5",
        symbol="ABC",
        horizon_days=3,
        up_threshold=0.05,
        down_threshold=-0.05,
    )

    assert target_column(target) == "ABC_hit_up_before_down_3d"
