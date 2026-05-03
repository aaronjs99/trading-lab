from pathlib import Path

import pandas as pd

from trading_lab.models.diagnostics import build_model_diagnostics


def test_build_model_diagnostics_reports_counts(tmp_path: Path):
    path = tmp_path / "features.csv"
    pd.DataFrame(
        {
            "date": ["2020-01-01", "2020-01-02"],
            "SPY_ret_1d": [None, 0.01],
            "QQQ_ret_1d": [None, 0.02],
            "TQQQ_ret_1d": [None, 0.03],
            "TQQQ_hit_up_before_down_5d": [1, None],
        }
    ).to_csv(path, index=False)

    text = build_model_diagnostics(path)

    assert "# Model Diagnostics" in text
    assert "target_columns:" in text
    assert "complete_feature_rows:" in text
