from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from trading_lab.backtests.walk_forward import _event_returns, _summarize
from trading_lab.signals.latest_regime import regime_feature_columns


FEATURE_PATH = Path("data/processed/market/market_features.csv")
REPORT_DIR = Path("data/reports")


@dataclass(frozen=True)
class ModelConfig:
    name: str
    threshold: float = 0.50
    take_profit: float = 0.04
    stop_loss: float = 0.04
    max_hold: int = 3
    require_trend: bool = True
    max_ext20: float | None = None


@dataclass(frozen=True)
class FoldSpec:
    name: str
    train_start: str
    train_end: str
    test_start: str
    test_end: str


class ProbabilityModel(Protocol):
    def fit(self, x: pd.DataFrame, y: pd.Series) -> ProbabilityModel:
        ...

    def predict_proba(self, x: pd.DataFrame) -> np.ndarray:
        ...


class ModelFactory:
    """Factory for prediction models used by the model zoo."""

    @staticmethod
    def build(name: str) -> ProbabilityModel:
        if name == "logistic_regression":
            return Pipeline(
                [
                    ("scale", StandardScaler()),
                    (
                        "model",
                        LogisticRegression(
                            max_iter=2000,
                            class_weight="balanced",
                            solver="lbfgs",
                        ),
                    ),
                ]
            )

        if name == "random_forest":
            return RandomForestClassifier(
                n_estimators=300,
                max_depth=5,
                min_samples_leaf=30,
                random_state=42,
                class_weight="balanced_subsample",
            )

        if name == "hist_gradient_boosting":
            return HistGradientBoostingClassifier(
                max_iter=250,
                learning_rate=0.03,
                max_leaf_nodes=15,
                l2_regularization=0.1,
                random_state=42,
            )

        if name == "random_forest_deeper":
            return RandomForestClassifier(
                n_estimators=400,
                max_depth=8,
                min_samples_leaf=20,
                random_state=7,
                class_weight="balanced_subsample",
            )

        raise ValueError(f"Unknown model name: {name}")


class MarketDataset:
    """Loads market features and prepares supervised classification rows."""

    def __init__(
        self,
        feature_path: Path = FEATURE_PATH,
        target_col: str = "TQQQ_hit_up_before_down_5d",
    ) -> None:
        self.feature_path = feature_path
        self.target_col = target_col

    def load(self) -> tuple[pd.DataFrame, list[str]]:
        df = pd.read_csv(self.feature_path)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

        feature_cols = regime_feature_columns(df)
        needed = list(
            dict.fromkeys(
                [
                    "date",
                    "TQQQ",
                    "QQQ_uptrend_20_50",
                    "QQQ_dist_ma_20",
                    self.target_col,
                ]
                + feature_cols
            )
        )

        work = df[needed].replace([np.inf, -np.inf], np.nan).dropna().copy()
        work["target"] = (work[self.target_col] == 1).astype(int)
        return work, feature_cols


class WalkForwardModelZoo:
    """Walk-forward model comparison for TQQQ event-style trading."""

    def __init__(
        self,
        dataset: MarketDataset,
        configs: list[ModelConfig],
        folds: list[FoldSpec] | None = None,
        report_dir: Path = REPORT_DIR,
    ) -> None:
        self.dataset = dataset
        self.configs = configs
        self.folds = folds or self.default_folds()
        self.report_dir = report_dir

    @staticmethod
    def default_folds() -> list[FoldSpec]:
        return [
            FoldSpec("2021_2022", "2012-01-01", "2020-12-31", "2021-01-01", "2022-12-31"),
            FoldSpec("2023", "2012-01-01", "2022-12-31", "2023-01-01", "2023-12-31"),
            FoldSpec("2024", "2012-01-01", "2023-12-31", "2024-01-01", "2024-12-31"),
            FoldSpec("2025_2026", "2012-01-01", "2024-12-31", "2025-01-01", "2026-12-31"),
        ]

    def run(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        df, feature_cols = self.dataset.load()

        fold_rows: list[dict] = []
        trade_rows: list[pd.DataFrame] = []

        for fold in self.folds:
            train = df[(df["date"] >= fold.train_start) & (df["date"] <= fold.train_end)].copy()
            test = df[(df["date"] >= fold.test_start) & (df["date"] <= fold.test_end)].copy()

            if len(train) < 500 or len(test) < 50:
                continue

            x_train = train[feature_cols]
            y_train = train["target"]
            x_test = test[feature_cols]
            y_test = test["target"]

            for config in self.configs:
                model = ModelFactory.build(config.name)
                model.fit(x_train, y_train)

                proba = model.predict_proba(x_test)[:, 1]
                pred = (proba >= config.threshold).astype(int)

                scored = test.copy()
                scored["proba"] = proba

                trades = _event_returns(
                    df=scored,
                    prob_col="proba",
                    threshold=config.threshold,
                    take_profit=config.take_profit,
                    stop_loss=config.stop_loss,
                    max_hold=config.max_hold,
                    require_trend=config.require_trend,
                    max_ext20=config.max_ext20,
                )
                trade_stats = _summarize(trades)

                row = {
                    "fold": fold.name,
                    "model": config.name,
                    "threshold": config.threshold,
                    "take_profit": config.take_profit,
                    "stop_loss": config.stop_loss,
                    "max_hold": config.max_hold,
                    "require_trend": config.require_trend,
                    "max_ext20": config.max_ext20,
                    "test_rows": len(test),
                    "positive_rate": float(y_test.mean()),
                    "accuracy": float(accuracy_score(y_test, pred)),
                    "brier": float(brier_score_loss(y_test, proba)),
                    "roc_auc": safe_roc_auc(y_test, proba),
                    **trade_stats,
                }
                fold_rows.append(row)

                if not trades.empty:
                    tmp = trades.copy()
                    tmp["fold"] = fold.name
                    tmp["model"] = config.name
                    trade_rows.append(tmp)

        fold_results = pd.DataFrame(fold_rows)
        trade_results = pd.concat(trade_rows, ignore_index=True) if trade_rows else pd.DataFrame()
        return fold_results, trade_results

    def summarize(self, fold_results: pd.DataFrame) -> pd.DataFrame:
        if fold_results.empty:
            return fold_results

        grouped = (
            fold_results.groupby(
                ["model", "threshold", "take_profit", "stop_loss", "max_hold", "require_trend", "max_ext20"],
                dropna=False,
            )
            .agg(
                folds=("fold", "nunique"),
                test_rows=("test_rows", "sum"),
                trades=("trades", "sum"),
                mean_accuracy=("accuracy", "mean"),
                mean_brier=("brier", "mean"),
                mean_roc_auc=("roc_auc", "mean"),
                mean_total_return=("total_return", "mean"),
                mean_avg_return=("avg_return", "mean"),
                mean_win_rate=("win_rate", "mean"),
                mean_profit_factor=("profit_factor", "mean"),
                worst_fold_return=("total_return", "min"),
                worst_fold_drawdown=("max_drawdown", "min"),
            )
            .reset_index()
        )

        grouped["score"] = (
            grouped["mean_profit_factor"].replace([np.inf, -np.inf], np.nan).fillna(0.0)
            + 10.0 * grouped["mean_avg_return"].fillna(0.0)
            - grouped["mean_brier"].fillna(1.0)
            + grouped["worst_fold_return"].fillna(-1.0)
        )

        return grouped.sort_values(
            ["score", "mean_profit_factor", "mean_avg_return"],
            ascending=False,
        )

    def write_reports(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        self.report_dir.mkdir(parents=True, exist_ok=True)

        fold_results, trade_results = self.run()
        summary = self.summarize(fold_results)

        fold_results.to_csv(self.report_dir / "model_zoo_fold_results.csv", index=False)
        trade_results.to_csv(self.report_dir / "model_zoo_trades.csv", index=False)
        summary.to_csv(self.report_dir / "model_zoo_ranking.csv", index=False)

        return fold_results, trade_results, summary


def safe_roc_auc(y_true: pd.Series, proba: np.ndarray) -> float:
    if y_true.nunique() < 2:
        return float("nan")
    return float(roc_auc_score(y_true, proba))


def default_configs() -> list[ModelConfig]:
    return [
        ModelConfig("logistic_regression"),
        ModelConfig("random_forest"),
        ModelConfig("random_forest_deeper"),
        ModelConfig("hist_gradient_boosting"),
    ]


def run_model_zoo() -> pd.DataFrame:
    zoo = WalkForwardModelZoo(
        dataset=MarketDataset(),
        configs=default_configs(),
    )
    _, _, ranking = zoo.write_reports()
    return ranking


def main() -> None:
    ranking = run_model_zoo()
    print("== Model zoo ranking ==")
    if ranking.empty:
        print("No model zoo results generated.")
        return

    cols = [
        "model",
        "folds",
        "trades",
        "mean_brier",
        "mean_roc_auc",
        "mean_avg_return",
        "mean_win_rate",
        "mean_profit_factor",
        "worst_fold_return",
        "worst_fold_drawdown",
        "score",
    ]
    print(ranking[cols].head(20).to_string(index=False))
    print()
    print(f"Wrote {REPORT_DIR / 'model_zoo_ranking.csv'}")


if __name__ == "__main__":
    main()
