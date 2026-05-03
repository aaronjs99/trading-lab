import pandas as pd

from trading_lab.config.targets import PredictionTarget
from trading_lab.features.targets import add_hit_up_before_down_target, target_column


def test_target_column_is_symbol_generic():
    target = PredictionTarget(
        name="soxl_5d_up5_before_down5",
        symbol="SOXL",
        horizon_days=5,
        up_threshold=0.05,
        down_threshold=-0.05,
    )

    assert target_column(target) == "SOXL_hit_up_before_down_5d"


def test_add_hit_up_before_down_target_marks_first_hit():
    target = PredictionTarget(
        name="abc_3d_up5_before_down5",
        symbol="ABC",
        horizon_days=3,
        up_threshold=0.05,
        down_threshold=-0.05,
    )
    df = pd.DataFrame({"ABC": [100, 103, 106, 90]})

    out = add_hit_up_before_down_target(df, target)

    assert out.loc[0, "ABC_hit_up_before_down_3d"] == 1


def test_add_hit_up_before_down_target_marks_down_first():
    target = PredictionTarget(
        name="abc_3d_up5_before_down5",
        symbol="ABC",
        horizon_days=3,
        up_threshold=0.05,
        down_threshold=-0.05,
    )
    df = pd.DataFrame({"ABC": [100, 96, 94, 110]})

    out = add_hit_up_before_down_target(df, target)

    assert out.loc[0, "ABC_hit_up_before_down_3d"] == 0
