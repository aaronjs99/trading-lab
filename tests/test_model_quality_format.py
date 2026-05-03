from pathlib import Path

from trading_lab.models.quality import ModelQualityGate, write_model_quality_gate


def test_model_quality_gate_writes_real_newlines(tmp_path: Path):
    out = tmp_path / "gate.txt"
    gate = ModelQualityGate(
        status="CAUTION_MODEL_WEAK",
        reason="test reason",
        model="rf",
        probability=0.44,
        mean_roc_auc=0.51,
        mean_profit_factor=1.57,
        worst_drawdown=-0.28,
    )

    write_model_quality_gate(gate, out)
    text = out.read_text(encoding="utf-8")

    assert "\\nstatus:" not in text
    assert "status: CAUTION_MODEL_WEAK" in text
    assert text.splitlines()[0] == "== Model quality gate =="
