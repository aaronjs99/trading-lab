from pathlib import Path

import pandas as pd

from trading_lab.models.compare import compare_model_performance, write_model_comparison


def test_model_compare_reports_no_baseline(tmp_path: Path):
    current = tmp_path / "model_zoo.csv"
    baseline = tmp_path / "missing.csv"

    pd.DataFrame(
        [{"model": "rf", "mean_roc_auc": 0.51, "mean_profit_factor": 1.57}]
    ).to_csv(current, index=False)

    comparison = compare_model_performance(current, baseline)

    assert comparison.status == "NO_BASELINE"
    assert comparison.baseline_roc_auc is None


def test_model_compare_detects_degradation(tmp_path: Path):
    current = tmp_path / "model_zoo.csv"
    baseline = tmp_path / "baseline.csv"

    pd.DataFrame(
        [{"model": "rf", "mean_roc_auc": 0.51, "mean_profit_factor": 1.57}]
    ).to_csv(current, index=False)

    pd.DataFrame(
        [{"model": "old_rf", "mean_roc_auc": 0.60, "mean_profit_factor": 2.30}]
    ).to_csv(baseline, index=False)

    comparison = compare_model_performance(current, baseline)

    assert comparison.status == "DEGRADED"


def test_write_model_comparison_outputs_markdown(tmp_path: Path):
    current = tmp_path / "model_zoo.csv"
    baseline = tmp_path / "baseline.csv"
    out = tmp_path / "comparison.md"

    pd.DataFrame(
        [{"model": "rf", "mean_roc_auc": 0.61, "mean_profit_factor": 2.10}]
    ).to_csv(current, index=False)

    pd.DataFrame(
        [{"model": "old_rf", "mean_roc_auc": 0.60, "mean_profit_factor": 2.00}]
    ).to_csv(baseline, index=False)

    comparison = compare_model_performance(current, baseline)
    write_model_comparison(comparison, out)

    text = out.read_text(encoding="utf-8")
    assert "# Model Comparison" in text
    assert "current_roc_auc" in text
