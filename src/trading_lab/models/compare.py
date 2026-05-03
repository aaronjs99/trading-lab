from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


BASELINE_PATH = Path("data/reports/model_baseline_snapshot.csv")
CURRENT_MODEL_PATH = Path("data/reports/model_zoo_ranking.csv")
CURRENT_REGIME_PATH = Path("data/reports/regime_model_summary.csv")
OUT_PATH = Path("data/reports/model_comparison.md")


@dataclass(frozen=True)
class ModelComparison:
    status: str
    reason: str
    current_best_model: str
    current_roc_auc: float
    current_profit_factor: float
    baseline_roc_auc: float | None
    baseline_profit_factor: float | None


def _best_current_model(path: Path = CURRENT_MODEL_PATH) -> pd.Series:
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"No rows in {path}")
    return df.iloc[0]


def _load_baseline(path: Path = BASELINE_PATH) -> pd.Series | None:
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if df.empty:
        return None
    return df.iloc[-1]


def write_baseline_snapshot(
    current_model_path: Path = CURRENT_MODEL_PATH,
    baseline_path: Path = BASELINE_PATH,
) -> pd.DataFrame:
    row = _best_current_model(current_model_path).copy()
    out = pd.DataFrame(
        [
            {
                "model": row.get("model"),
                "mean_roc_auc": row.get("mean_roc_auc"),
                "mean_profit_factor": row.get("mean_profit_factor"),
                "mean_win_rate": row.get("mean_win_rate"),
                "worst_fold_drawdown": row.get("worst_fold_drawdown"),
            }
        ]
    )
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(baseline_path, index=False)
    return out


def compare_model_performance(
    current_model_path: Path = CURRENT_MODEL_PATH,
    baseline_path: Path = BASELINE_PATH,
) -> ModelComparison:
    current = _best_current_model(current_model_path)
    baseline = _load_baseline(baseline_path)

    current_roc = float(current["mean_roc_auc"])
    current_pf = float(current["mean_profit_factor"])
    current_model = str(current["model"])

    if baseline is None:
        return ModelComparison(
            status="NO_BASELINE",
            reason="No baseline snapshot exists yet. Run baseline capture only after choosing a trusted model state.",
            current_best_model=current_model,
            current_roc_auc=current_roc,
            current_profit_factor=current_pf,
            baseline_roc_auc=None,
            baseline_profit_factor=None,
        )

    baseline_roc = float(baseline["mean_roc_auc"])
    baseline_pf = float(baseline["mean_profit_factor"])

    roc_delta = current_roc - baseline_roc
    pf_delta = current_pf - baseline_pf

    if roc_delta < -0.03 or pf_delta < -0.30:
        status = "DEGRADED"
        reason = f"ROC delta {roc_delta:+.3f}, profit-factor delta {pf_delta:+.2f}."
    elif roc_delta > 0.03 or pf_delta > 0.30:
        status = "IMPROVED"
        reason = f"ROC delta {roc_delta:+.3f}, profit-factor delta {pf_delta:+.2f}."
    else:
        status = "STABLE"
        reason = f"ROC delta {roc_delta:+.3f}, profit-factor delta {pf_delta:+.2f}."

    return ModelComparison(
        status=status,
        reason=reason,
        current_best_model=current_model,
        current_roc_auc=current_roc,
        current_profit_factor=current_pf,
        baseline_roc_auc=baseline_roc,
        baseline_profit_factor=baseline_pf,
    )


def write_model_comparison(
    comparison: ModelComparison,
    output_path: Path = OUT_PATH,
) -> None:
    lines = [
        "# Model Comparison",
        "",
        f"- status: {comparison.status}",
        f"- reason: {comparison.reason}",
        f"- current_best_model: {comparison.current_best_model}",
        f"- current_roc_auc: {comparison.current_roc_auc:.3f}",
        f"- current_profit_factor: {comparison.current_profit_factor:.2f}",
        f"- baseline_roc_auc: {'n/a' if comparison.baseline_roc_auc is None else f'{comparison.baseline_roc_auc:.3f}'}",
        f"- baseline_profit_factor: {'n/a' if comparison.baseline_profit_factor is None else f'{comparison.baseline_profit_factor:.2f}'}",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    comparison = compare_model_performance()
    write_model_comparison(comparison)
    print(OUT_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
