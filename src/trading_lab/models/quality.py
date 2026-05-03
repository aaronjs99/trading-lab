from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


MODEL_ZOO_PATH = Path("data/reports/model_zoo_ranking.csv")
SELECTED_SIGNAL_PATH = Path("data/reports/selected_model_latest_signal.csv")
OUT_PATH = Path("data/reports/model_quality_gate.txt")


@dataclass(frozen=True)
class ModelQualityGate:
    status: str
    reason: str
    model: str
    probability: float
    mean_roc_auc: float
    mean_profit_factor: float
    worst_drawdown: float


def evaluate_model_quality(
    model_zoo_path: Path = MODEL_ZOO_PATH,
    selected_signal_path: Path = SELECTED_SIGNAL_PATH,
    min_roc_auc: float = 0.55,
    min_profit_factor: float = 1.75,
    max_worst_drawdown: float = -0.50,
) -> ModelQualityGate:
    zoo = pd.read_csv(model_zoo_path)
    signal = pd.read_csv(selected_signal_path).iloc[-1]

    model_name = str(signal["model"])
    match = zoo[zoo["model"].astype(str).eq(model_name)]
    if match.empty:
        return ModelQualityGate(
            status="NO_TRADE_MODEL_UNKNOWN",
            reason=f"Selected model {model_name} not found in model zoo ranking.",
            model=model_name,
            probability=float(signal["probability"]),
            mean_roc_auc=float("nan"),
            mean_profit_factor=float("nan"),
            worst_drawdown=float("nan"),
        )

    row = match.iloc[0]
    roc_auc = float(row["mean_roc_auc"])
    profit_factor = float(row["mean_profit_factor"])
    worst_drawdown = float(row["worst_fold_drawdown"])

    failures = []
    if roc_auc < min_roc_auc:
        failures.append(f"ROC AUC {roc_auc:.3f} < {min_roc_auc:.3f}")
    if profit_factor < min_profit_factor:
        failures.append(f"profit factor {profit_factor:.2f} < {min_profit_factor:.2f}")
    if worst_drawdown < max_worst_drawdown:
        failures.append(f"worst drawdown {worst_drawdown:.2%} < {max_worst_drawdown:.2%}")

    if failures:
        return ModelQualityGate(
            status="CAUTION_MODEL_WEAK",
            reason="; ".join(failures),
            model=model_name,
            probability=float(signal["probability"]),
            mean_roc_auc=roc_auc,
            mean_profit_factor=profit_factor,
            worst_drawdown=worst_drawdown,
        )

    return ModelQualityGate(
        status="MODEL_OK",
        reason="Model quality checks passed.",
        model=model_name,
        probability=float(signal["probability"]),
        mean_roc_auc=roc_auc,
        mean_profit_factor=profit_factor,
        worst_drawdown=worst_drawdown,
    )


def write_model_quality_gate(gate: ModelQualityGate, output_path: Path = OUT_PATH) -> None:
    lines = [
        "== Model quality gate ==",
        f"status: {gate.status}",
        f"reason: {gate.reason}",
        f"model: {gate.model}",
        f"probability: {gate.probability:.3f}",
        f"mean_roc_auc: {gate.mean_roc_auc:.3f}",
        f"mean_profit_factor: {gate.mean_profit_factor:.2f}",
        f"worst_drawdown: {gate.worst_drawdown:.2%}",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    gate = evaluate_model_quality()
    write_model_quality_gate(gate)
    print(OUT_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
