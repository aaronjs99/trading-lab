from pathlib import Path

import pandas as pd

from trading_lab.models.quality import evaluate_model_quality, write_model_quality_gate


def test_model_quality_gate_flags_weak_model(tmp_path: Path):
    zoo = tmp_path / "zoo.csv"
    signal = tmp_path / "signal.csv"

    pd.DataFrame(
        [
            {
                "model": "rf",
                "mean_roc_auc": 0.51,
                "mean_profit_factor": 1.2,
                "worst_fold_drawdown": -0.30,
            }
        ]
    ).to_csv(zoo, index=False)

    pd.DataFrame([{"model": "rf", "probability": 0.44}]).to_csv(signal, index=False)

    gate = evaluate_model_quality(zoo, signal)

    assert gate.status == "CAUTION_MODEL_WEAK"
    assert "ROC AUC" in gate.reason


def test_model_quality_gate_accepts_good_model(tmp_path: Path):
    zoo = tmp_path / "zoo.csv"
    signal = tmp_path / "signal.csv"

    pd.DataFrame(
        [
            {
                "model": "rf",
                "mean_roc_auc": 0.61,
                "mean_profit_factor": 2.1,
                "worst_fold_drawdown": -0.30,
            }
        ]
    ).to_csv(zoo, index=False)

    pd.DataFrame([{"model": "rf", "probability": 0.62}]).to_csv(signal, index=False)

    gate = evaluate_model_quality(zoo, signal)
    out = tmp_path / "gate.txt"
    write_model_quality_gate(gate, out)
    text = out.read_text(encoding="utf-8")

    assert gate.status == "MODEL_OK"
    assert "\\nstatus:" not in text
    assert "status: MODEL_OK" in text
