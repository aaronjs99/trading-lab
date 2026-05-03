from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from trading_lab.config import TradingConfig, load_trading_config
from trading_lab.config.targets import PredictionTarget, default_prediction_targets
from trading_lab.models.dataset import primary_prediction_target, target_column


CSV_PATH = Path("data/reports/model_experiment_report.csv")

@dataclass(frozen=True)
class SelectedTarget:
    target: PredictionTarget
    target_name: str
    target_mode: str
    target_col: str
    model: str | None
    mean_roc_auc: float | None
    mean_profit_factor: float | None
    worst_fold_drawdown: float | None
    score: float | None
    source: str
    fallback_reason: str | None = None


def load_experiment_report(path: Path = CSV_PATH) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def select_best_target(report_df: pd.DataFrame) -> pd.Series | None:
    if report_df.empty:
        return None

    required = {"target_name", "target_mode", "target_col"}
    if not required.issubset(report_df.columns):
        return None

    ranked = report_df.copy()
    pf = pd.to_numeric(ranked.get("mean_profit_factor"), errors="coerce")
    ranked["_finite_profit_factor"] = pf.notna() & (~pf.isin([float("inf"), float("-inf")]))
    ranked["_roc_auc_sort"] = pd.to_numeric(ranked.get("mean_roc_auc"), errors="coerce").fillna(-1.0)
    ranked["_score_sort"] = pd.to_numeric(ranked.get("score"), errors="coerce").fillna(-1.0)
    ranked["_profit_factor_sort"] = pf.where(ranked["_finite_profit_factor"], -1.0).fillna(-1.0)
    ranked["_drawdown_sort"] = pd.to_numeric(ranked.get("worst_fold_drawdown"), errors="coerce").fillna(-1.0)
    ranked = ranked.sort_values(
        [
            "_finite_profit_factor",
            "_roc_auc_sort",
            "_score_sort",
            "_profit_factor_sort",
            "_drawdown_sort",
        ],
        ascending=[False, False, False, False, False],
    )
    return ranked.iloc[0]


def selected_prediction_target(
    config: TradingConfig | None = None,
    report_df: pd.DataFrame | None = None,
) -> SelectedTarget:
    cfg = config or load_trading_config()
    default_target = primary_prediction_target(cfg)
    if not cfg.use_experiment_selected_target:
        return _default_selection(default_target, "experiment target selection disabled")

    report = report_df if report_df is not None else load_experiment_report()
    if report.empty:
        return _default_selection(default_target, "experiment report missing or empty")

    filtered = _filter_report(report, cfg)
    row = select_best_target(filtered)
    if row is None:
        return _default_selection(default_target, "experiment report has no valid target rows")

    target = _target_from_row(cfg, row)
    if target is None:
        return _default_selection(default_target, "selected target does not match configured targets")

    return SelectedTarget(
        target=target,
        target_name=str(row["target_name"]),
        target_mode=str(row["target_mode"]),
        target_col=str(row["target_col"]),
        model=str(row["model"]) if "model" in row and pd.notna(row["model"]) else None,
        mean_roc_auc=_optional_float(row, "mean_roc_auc"),
        mean_profit_factor=_optional_float(row, "mean_profit_factor"),
        worst_fold_drawdown=_optional_float(row, "worst_fold_drawdown"),
        score=_optional_float(row, "score"),
        source="experiment_report",
    )


def _filter_report(report: pd.DataFrame, config: TradingConfig) -> pd.DataFrame:
    out = report.copy()
    if config.selected_target_mode and "target_mode" in out.columns:
        out = out[out["target_mode"].astype(str).eq(config.selected_target_mode)]
    if config.selected_target_name and "target_name" in out.columns:
        out = out[out["target_name"].astype(str).eq(config.selected_target_name)]
    return out


def _target_from_row(config: TradingConfig, row: pd.Series) -> PredictionTarget | None:
    mode = str(row["target_mode"])
    selected_name = str(row["target_name"])
    selected_col = str(row["target_col"])

    for base in default_prediction_targets(config):
        candidate = PredictionTarget(
            name=selected_name,
            symbol=base.symbol,
            horizon_days=base.horizon_days,
            up_threshold=base.up_threshold,
            down_threshold=base.down_threshold,
            mode=mode,
        )
        if selected_col == target_column(candidate) or selected_name.startswith(base.name):
            return candidate
    return None


def _default_selection(target: PredictionTarget, reason: str) -> SelectedTarget:
    return SelectedTarget(
        target=target,
        target_name=target.name,
        target_mode=target.mode,
        target_col=target_column(target),
        model=None,
        mean_roc_auc=None,
        mean_profit_factor=None,
        worst_fold_drawdown=None,
        score=None,
        source="default_config",
        fallback_reason=reason,
    )


def _optional_float(row: pd.Series, column: str) -> float | None:
    if column not in row or pd.isna(row[column]):
        return None
    return float(row[column])


def format_selected_target(selection: SelectedTarget) -> str:
    lines = [
        "== Selected model target ==",
        f"target_name: {selection.target_name}",
        f"target_mode: {selection.target_mode}",
        f"target_col: {selection.target_col}",
        f"model: {selection.model or 'n/a'}",
        f"mean_roc_auc: {_fmt(selection.mean_roc_auc)}",
        f"mean_profit_factor: {_fmt(selection.mean_profit_factor)}",
        f"worst_fold_drawdown: {_fmt(selection.worst_fold_drawdown)}",
        f"score: {_fmt(selection.score)}",
        f"source: {selection.source}",
    ]
    if selection.fallback_reason:
        lines.append(f"fallback_reason: {selection.fallback_reason}")
    return "\n".join(lines) + "\n"


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.6g}"


def main() -> None:
    print(format_selected_target(selected_prediction_target()))


if __name__ == "__main__":
    main()
