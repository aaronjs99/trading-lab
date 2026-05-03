from __future__ import annotations

from pathlib import Path

import pandas as pd

from trading_lab.config import TradingConfig, load_trading_config
from trading_lab.config.targets import PredictionTarget
from trading_lab.models.baseline import BASELINE_PATH
from trading_lab.models.dataset import (
    FEATURE_PATH,
    load_market_features,
    primary_prediction_target,
    supervised_frame,
    target_column,
)
from trading_lab.models.quality import OUT_PATH as QUALITY_PATH
from trading_lab.models.zoo import REPORT_DIR


CSV_PATH = REPORT_DIR / "model_experiment_report.csv"
MD_PATH = REPORT_DIR / "model_experiment_report.md"
MODEL_ZOO_PATH = REPORT_DIR / "model_zoo_ranking.csv"


REPORT_FIELDS = [
    "target_name",
    "target_mode",
    "target_col",
    "model",
    "train_rows",
    "test_rows",
    "positive_rate",
    "mean_roc_auc",
    "mean_brier",
    "mean_win_rate",
    "mean_profit_factor",
    "worst_fold_return",
    "worst_fold_drawdown",
    "model_quality_status",
    "baseline_status",
]


def _read_status_line(path: Path, prefix: str) -> str | None:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return None


def _baseline_status(path: Path = BASELINE_PATH) -> str:
    return "BASELINE_AVAILABLE" if path.exists() else "NO_BASELINE"


def build_model_experiment_report(
    model_zoo_path: Path = MODEL_ZOO_PATH,
    feature_path: Path = FEATURE_PATH,
    target: PredictionTarget | None = None,
    config: TradingConfig | None = None,
) -> pd.DataFrame:
    cfg = config or load_trading_config()
    selected_target = target or primary_prediction_target(cfg)
    target_col = target_column(selected_target)

    if not model_zoo_path.exists():
        return pd.DataFrame(columns=REPORT_FIELDS)

    zoo = pd.read_csv(model_zoo_path)
    if zoo.empty:
        return pd.DataFrame(columns=REPORT_FIELDS)

    train_rows = None
    positive_rate = None
    if feature_path.exists():
        features = load_market_features(feature_path)
        try:
            supervised, _, _ = supervised_frame(features, target=selected_target, config=cfg)
            train_rows = len(supervised)
            positive_rate = float(supervised["target"].mean())
        except ValueError:
            train_rows = None
            positive_rate = None

    quality_status = _read_status_line(QUALITY_PATH, "status:") or ""
    baseline_status = _baseline_status()

    rows = []
    for _, row in zoo.iterrows():
        rows.append(
            {
                "target_name": selected_target.name,
                "target_mode": selected_target.mode,
                "target_col": target_col,
                "model": row.get("model"),
                "train_rows": train_rows,
                "test_rows": row.get("test_rows"),
                "positive_rate": positive_rate,
                "mean_roc_auc": row.get("mean_roc_auc", row.get("roc_auc")),
                "mean_brier": row.get("mean_brier"),
                "mean_win_rate": row.get("mean_win_rate"),
                "mean_profit_factor": row.get("mean_profit_factor"),
                "worst_fold_return": row.get("worst_fold_return"),
                "worst_fold_drawdown": row.get("worst_fold_drawdown"),
                "model_quality_status": quality_status,
                "baseline_status": baseline_status,
            }
        )

    return pd.DataFrame(rows, columns=REPORT_FIELDS)


def write_model_experiment_report(
    csv_path: Path = CSV_PATH,
    md_path: Path = MD_PATH,
    **kwargs,
) -> pd.DataFrame:
    report = build_model_experiment_report(**kwargs)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(csv_path, index=False)
    md_path.write_text(format_model_experiment_markdown(report), encoding="utf-8")
    return report


def format_model_experiment_markdown(report: pd.DataFrame) -> str:
    lines = ["# Model Experiment Report", ""]
    if report.empty:
        lines.append("No model experiment rows available.")
        return "\n".join(lines) + "\n"

    cols = [
        "target_name",
        "target_mode",
        "model",
        "test_rows",
        "positive_rate",
        "mean_roc_auc",
        "mean_brier",
        "mean_profit_factor",
        "worst_fold_drawdown",
        "model_quality_status",
        "baseline_status",
    ]
    display = report[cols].fillna("")
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
    for _, row in display.iterrows():
        values = [str(row[col]) for col in cols]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    report = write_model_experiment_report()
    print("== Model experiment report ==")
    if report.empty:
        print("No model experiment rows available.")
    else:
        print(report.head(20).to_string(index=False))
    print()
    print(CSV_PATH)
    print(MD_PATH)


if __name__ == "__main__":
    main()
