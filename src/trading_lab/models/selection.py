from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


MODEL_ZOO_PATH = Path("data/reports/model_zoo_ranking.csv")


@dataclass(frozen=True)
class SelectedModel:
    model: str
    trades: int
    mean_brier: float
    mean_roc_auc: float
    mean_avg_return: float
    mean_win_rate: float
    mean_profit_factor: float
    worst_fold_return: float
    worst_fold_drawdown: float
    score: float


def select_model_zoo_winner(path: Path = MODEL_ZOO_PATH) -> SelectedModel:
    ranking = pd.read_csv(path)

    if ranking.empty:
        raise ValueError("Model zoo ranking is empty.")

    row = ranking.sort_values(
        ["score", "mean_profit_factor", "mean_avg_return"],
        ascending=False,
    ).iloc[0]

    return SelectedModel(
        model=str(row["model"]),
        trades=int(row["trades"]),
        mean_brier=float(row["mean_brier"]),
        mean_roc_auc=float(row["mean_roc_auc"]),
        mean_avg_return=float(row["mean_avg_return"]),
        mean_win_rate=float(row["mean_win_rate"]),
        mean_profit_factor=float(row["mean_profit_factor"]),
        worst_fold_return=float(row["worst_fold_return"]),
        worst_fold_drawdown=float(row["worst_fold_drawdown"]),
        score=float(row["score"]),
    )


def model_winner_lines(path: Path = MODEL_ZOO_PATH) -> list[str]:
    selected = select_model_zoo_winner(path)
    return [
        "Selected prediction model:",
        f"- model: {selected.model}",
        f"- trades: {selected.trades}",
        f"- mean ROC AUC: {selected.mean_roc_auc:.3f}",
        f"- mean Brier: {selected.mean_brier:.3f}",
        f"- mean avg trade return: {selected.mean_avg_return:.2%}",
        f"- mean win rate: {selected.mean_win_rate:.2%}",
        f"- mean profit factor: {selected.mean_profit_factor:.2f}",
        f"- worst fold return: {selected.worst_fold_return:.2%}",
        f"- worst fold drawdown: {selected.worst_fold_drawdown:.2%}",
        f"- score: {selected.score:.3f}",
    ]
