import pandas as pd

from trading_lab.models.live import OUT_PATH


def test_selected_model_signal_output_path_name():
    assert OUT_PATH.name == "selected_model_latest_signal.csv"


def test_selected_model_signal_schema_example():
    df = pd.DataFrame(
        [
            {
                "date": "2026-05-01",
                "model": "random_forest_deeper",
                "probability": 0.42,
                "train_rows": 100,
                "target_positive_rate": 0.36,
                "selected_model_profit_factor": 2.5,
                "selected_model_worst_drawdown": -0.34,
            }
        ]
    )

    assert set(df.columns) == {
        "date",
        "model",
        "probability",
        "train_rows",
        "target_positive_rate",
        "selected_model_profit_factor",
        "selected_model_worst_drawdown",
    }
