from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.metrics import brier_score_loss

from trading_lab.backtests.walk_forward import _event_returns, _summarize
from trading_lab.config import TradingColumns, TradingConfig, load_trading_config
from trading_lab.config.targets import PredictionTarget, default_prediction_targets
from trading_lab.features.targets import add_prediction_target
from trading_lab.models.baseline import BASELINE_PATH
from trading_lab.models.dataset import (
    FEATURE_PATH,
    load_market_features,
    supervised_frame,
    target_column,
    walk_forward_folds,
)
from trading_lab.models.quality import OUT_PATH as QUALITY_PATH
from trading_lab.models.zoo import REPORT_DIR, ModelConfig, ModelFactory, default_configs, safe_roc_auc


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
    "score",
    "model_quality_status",
    "baseline_status",
]


TARGET_MODES = ["barrier_first_hit", "horizon_return", "threshold_horizon_return"]


def _read_status_line(path: Path, prefix: str) -> str | None:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return None


def _baseline_status(path: Path = BASELINE_PATH) -> str:
    return "BASELINE_AVAILABLE" if path.exists() else "NO_BASELINE"


def _target_variants(base_targets: list[PredictionTarget]) -> list[PredictionTarget]:
    variants: list[PredictionTarget] = []
    for base in base_targets:
        for mode in TARGET_MODES:
            variants.append(
                PredictionTarget(
                    name=f"{base.name}_{mode}",
                    symbol=base.symbol,
                    horizon_days=base.horizon_days,
                    up_threshold=base.up_threshold,
                    down_threshold=base.down_threshold,
                    mode=mode,
                )
            )
    return variants


def _ensure_target_column(df: pd.DataFrame, target: PredictionTarget) -> pd.DataFrame:
    col = target_column(target)
    if col in df.columns:
        return df
    return add_prediction_target(df, target)


def _model_configs(model_zoo_path: Path) -> list[ModelConfig]:
    if not model_zoo_path.exists():
        return default_configs()

    zoo = pd.read_csv(model_zoo_path)
    if zoo.empty or "model" not in zoo.columns:
        return default_configs()

    configs: list[ModelConfig] = []
    for _, row in zoo.drop_duplicates(subset=["model"]).iterrows():
        defaults = ModelConfig(str(row["model"]))
        configs.append(
            ModelConfig(
                name=str(row["model"]),
                threshold=float(row.get("threshold", defaults.threshold)),
                take_profit=float(row.get("take_profit", defaults.take_profit)),
                stop_loss=float(row.get("stop_loss", defaults.stop_loss)),
                max_hold=int(row.get("max_hold", defaults.max_hold)),
                require_trend=bool(row.get("require_trend", defaults.require_trend)),
                max_ext20=(
                    None
                    if pd.isna(row.get("max_ext20", None))
                    else float(row.get("max_ext20", defaults.max_ext20))
                ),
            )
        )
    return configs or default_configs()


def _score_summary(row: dict) -> float:
    auc = row.get("mean_roc_auc")
    profit_factor = row.get("mean_profit_factor")
    drawdown = row.get("worst_fold_drawdown")
    brier = row.get("mean_brier")

    auc_score = 0.0 if pd.isna(auc) else float(auc)
    if pd.isna(profit_factor) or profit_factor == float("inf"):
        pf_score = 0.0
    else:
        pf_score = min(float(profit_factor), 10.0) / 10.0
    dd_score = 0.0 if pd.isna(drawdown) else float(drawdown)
    brier_penalty = 0.0 if pd.isna(brier) else float(brier)
    return auc_score + pf_score + dd_score - brier_penalty


def rank_model_experiment_report(report: pd.DataFrame) -> pd.DataFrame:
    if report.empty:
        return report

    ranked = report.copy()
    pf = pd.to_numeric(ranked["mean_profit_factor"], errors="coerce")
    ranked["_finite_profit_factor"] = pf.notna() & (~pf.isin([float("inf"), float("-inf")]))
    ranked["_roc_auc_sort"] = pd.to_numeric(ranked["mean_roc_auc"], errors="coerce").fillna(-1.0)
    ranked["_profit_factor_sort"] = pf.where(ranked["_finite_profit_factor"], -1.0).fillna(-1.0)
    ranked["_drawdown_sort"] = pd.to_numeric(ranked["worst_fold_drawdown"], errors="coerce").fillna(-1.0)
    ranked = ranked.sort_values(
        [
            "_finite_profit_factor",
            "_roc_auc_sort",
            "_profit_factor_sort",
            "_drawdown_sort",
        ],
        ascending=[False, False, False, False],
    )
    return ranked.drop(
        columns=[
            "_finite_profit_factor",
            "_roc_auc_sort",
            "_profit_factor_sort",
            "_drawdown_sort",
        ]
    ).reset_index(drop=True)


def _evaluate_candidate(
    supervised: pd.DataFrame,
    feature_cols: list[str],
    model_config: ModelConfig,
    config: TradingConfig,
) -> dict:
    fold_rows: list[dict] = []
    trade_rows: list[dict] = []

    for train, test in walk_forward_folds(supervised, n_folds=4):
        if len(train) < 2 or len(test) < 1 or train["target"].nunique() < 2:
            continue

        model = ModelFactory.build(model_config.name)
        model.fit(train[feature_cols], train["target"])
        proba = model.predict_proba(test[feature_cols])[:, 1]

        fold_rows.append(
            {
                "train_rows": len(train),
                "test_rows": len(test),
                "positive_rate": float(train["target"].mean()),
                "mean_roc_auc": safe_roc_auc(test["target"], proba),
                "mean_brier": float(brier_score_loss(test["target"], proba)),
            }
        )

        scored = test.copy()
        scored["proba"] = proba
        if _has_trade_columns(scored, config):
            trades = _event_returns(
                df=scored,
                prob_col="proba",
                threshold=model_config.threshold,
                take_profit=model_config.take_profit,
                stop_loss=model_config.stop_loss,
                max_hold=model_config.max_hold,
                require_trend=model_config.require_trend,
                max_ext20=model_config.max_ext20,
                config=config,
            )
            trade_rows.append(_summarize(trades))

    if not fold_rows:
        return {
            "train_rows": len(supervised),
            "test_rows": 0,
            "positive_rate": float(supervised["target"].mean()) if len(supervised) else None,
            "mean_roc_auc": None,
            "mean_brier": None,
            "mean_win_rate": None,
            "mean_profit_factor": None,
            "worst_fold_return": None,
            "worst_fold_drawdown": None,
        }

    folds = pd.DataFrame(fold_rows)
    trades = pd.DataFrame(trade_rows)
    result = {
        "train_rows": int(folds["train_rows"].max()),
        "test_rows": int(folds["test_rows"].sum()),
        "positive_rate": float(folds["positive_rate"].mean()),
        "mean_roc_auc": float(folds["mean_roc_auc"].mean()),
        "mean_brier": float(folds["mean_brier"].mean()),
        "mean_win_rate": None,
        "mean_profit_factor": None,
        "worst_fold_return": None,
        "worst_fold_drawdown": None,
    }
    if not trades.empty:
        result.update(
            {
                "mean_win_rate": float(trades["win_rate"].mean()),
                "mean_profit_factor": float(trades["profit_factor"].mean()),
                "worst_fold_return": float(trades["total_return"].min()),
                "worst_fold_drawdown": float(trades["max_drawdown"].min()),
            }
        )
    return result


def _has_trade_columns(df: pd.DataFrame, config: TradingConfig) -> bool:
    cols = TradingColumns(config)
    required = [
        "date",
        cols.traded_price,
        cols.benchmark_uptrend,
        cols.benchmark_dist_ma_20,
    ]
    return all(col in df.columns for col in required)


def build_model_experiment_report(
    model_zoo_path: Path = MODEL_ZOO_PATH,
    feature_path: Path = FEATURE_PATH,
    target: PredictionTarget | None = None,
    config: TradingConfig | None = None,
) -> pd.DataFrame:
    cfg = config or load_trading_config()
    if not feature_path.exists():
        return pd.DataFrame(columns=REPORT_FIELDS)

    features = load_market_features(feature_path)
    base_targets = [target] if target is not None else default_prediction_targets(cfg)
    targets = _target_variants(base_targets)
    model_configs = _model_configs(model_zoo_path)
    quality_status = _read_status_line(QUALITY_PATH, "status:") or ""
    baseline_status = _baseline_status()

    rows = []
    for candidate_target in targets:
        features = _ensure_target_column(features, candidate_target)
        target_col = target_column(candidate_target)
        try:
            supervised, feature_cols, _ = supervised_frame(features, target=candidate_target, config=cfg)
        except ValueError:
            continue

        extra_cols = [
            col
            for col in [
                TradingColumns(cfg).traded_price,
                TradingColumns(cfg).benchmark_uptrend,
                TradingColumns(cfg).benchmark_dist_ma_20,
            ]
            if col in features.columns and col not in supervised.columns
        ]
        if extra_cols:
            supervised = supervised.merge(features[["date"] + extra_cols], on="date", how="left")

        for model_config in model_configs:
            metrics = _evaluate_candidate(supervised, feature_cols, model_config, cfg)
            row = {
                "target_name": candidate_target.name,
                "target_mode": candidate_target.mode,
                "target_col": target_col,
                "model": model_config.name,
                **metrics,
                "model_quality_status": quality_status,
                "baseline_status": baseline_status,
            }
            row["score"] = _score_summary(row)
            rows.append(row)

    return rank_model_experiment_report(pd.DataFrame(rows, columns=REPORT_FIELDS))


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
        "score",
        "model_quality_status",
        "baseline_status",
    ]
    best = report.iloc[0]
    lines.extend(
        [
            "## Best Candidate",
            "",
            f"- target_name: {best['target_name']}",
            f"- target_mode: {best['target_mode']}",
            f"- model: {best['model']}",
            f"- mean_roc_auc: {best['mean_roc_auc']}",
            f"- mean_profit_factor: {best['mean_profit_factor']}",
            f"- worst_fold_drawdown: {best['worst_fold_drawdown']}",
            f"- score: {best['score']}",
            "",
            "## Ranked Candidates",
            "",
        ]
    )
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
