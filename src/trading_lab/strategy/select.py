from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_RANKING_PATH = Path("data/reports/walk_forward_strategy_ranking.csv")
DEFAULT_OUTPUT_PATH = Path("data/reports/selected_strategy.txt")


@dataclass(frozen=True)
class StrategySelection:
    threshold: float
    take_profit: float
    stop_loss: float
    max_hold: int
    require_trend: bool
    max_ext20: float | None
    trades: int
    mean_total_return: float
    mean_avg_return: float
    mean_win_rate: float
    mean_profit_factor: float
    worst_fold_return: float
    worst_fold_drawdown: float


REQUIRED_COLUMNS = {
    "threshold",
    "take_profit",
    "stop_loss",
    "max_hold",
    "require_trend",
    "max_ext20",
    "trades",
    "mean_total_return",
    "mean_avg_return",
    "mean_win_rate",
    "mean_profit_factor",
    "worst_fold_return",
    "worst_fold_drawdown",
}


def _coerce_ranking(ranking: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(ranking.columns)
    if missing:
        raise ValueError(f"Ranking missing columns: {sorted(missing)}")

    out = ranking.copy()
    numeric_cols = REQUIRED_COLUMNS - {"require_trend"}

    for col in numeric_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    finite_pf = out["mean_profit_factor"].replace([np.inf, -np.inf], np.nan)
    cap = finite_pf.quantile(0.95)
    if pd.isna(cap) or cap <= 0:
        cap = 10.0

    out["selection_profit_factor"] = out["mean_profit_factor"].replace([np.inf, -np.inf], cap)
    out = out.dropna(
        subset=[
            "trades",
            "selection_profit_factor",
            "mean_win_rate",
            "mean_avg_return",
            "worst_fold_return",
            "worst_fold_drawdown",
        ]
    )
    return out


def _selection_from_row(row: pd.Series) -> StrategySelection:
    max_ext20 = row["max_ext20"]
    if pd.isna(max_ext20):
        max_ext20 = None
    else:
        max_ext20 = float(max_ext20)

    return StrategySelection(
        threshold=float(row["threshold"]),
        take_profit=float(row["take_profit"]),
        stop_loss=float(row["stop_loss"]),
        max_hold=int(row["max_hold"]),
        require_trend=bool(row["require_trend"]),
        max_ext20=max_ext20,
        trades=int(row["trades"]),
        mean_total_return=float(row["mean_total_return"]),
        mean_avg_return=float(row["mean_avg_return"]),
        mean_win_rate=float(row["mean_win_rate"]),
        mean_profit_factor=float(row["mean_profit_factor"]),
        worst_fold_return=float(row["worst_fold_return"]),
        worst_fold_drawdown=float(row["worst_fold_drawdown"]),
    )


def _rank_candidates(candidates: pd.DataFrame) -> pd.DataFrame:
    return candidates.sort_values(
        [
            "selection_profit_factor",
            "mean_win_rate",
            "mean_avg_return",
            "worst_fold_return",
            "worst_fold_drawdown",
            "trades",
        ],
        ascending=[False, False, False, False, False, False],
    )


def select_strategy(
    ranking: pd.DataFrame,
    min_trades: int = 80,
    min_profit_factor: float = 2.0,
    min_win_rate: float = 0.60,
    min_worst_fold_return: float = -0.50,
    min_worst_fold_drawdown: float = -0.55,
) -> StrategySelection:
    """Select a walk-forward strategy with strict filters, then safe fallbacks."""

    clean = _coerce_ranking(ranking)
    if clean.empty:
        raise ValueError("No strategy rows available.")

    strict = clean[
        (clean["trades"] >= min_trades)
        & (clean["selection_profit_factor"] >= min_profit_factor)
        & (clean["mean_win_rate"] >= min_win_rate)
        & (clean["worst_fold_return"] >= min_worst_fold_return)
        & (clean["worst_fold_drawdown"] >= min_worst_fold_drawdown)
    ]

    if not strict.empty:
        return _selection_from_row(_rank_candidates(strict).iloc[0])

    relaxed = clean[
        (clean["trades"] >= min_trades)
        & (clean["selection_profit_factor"] >= min_profit_factor)
        & (clean["mean_win_rate"] >= min_win_rate)
    ]

    if not relaxed.empty:
        return _selection_from_row(_rank_candidates(relaxed).iloc[0])

    enough_trades = clean[clean["trades"] >= min_trades]
    if not enough_trades.empty:
        return _selection_from_row(_rank_candidates(enough_trades).iloc[0])

    return _selection_from_row(_rank_candidates(clean).iloc[0])


def write_selection(selection: StrategySelection, output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    lines = [
        "== Selected walk-forward strategy ==",
        f"threshold: {selection.threshold:.2f}",
        f"take_profit: {selection.take_profit:.2%}",
        f"stop_loss: {selection.stop_loss:.2%}",
        f"max_hold: {selection.max_hold} days",
        f"require_trend: {selection.require_trend}",
        f"max_ext20: {selection.max_ext20}",
        f"trades: {selection.trades}",
        f"mean_total_return: {selection.mean_total_return:.2%}",
        f"mean_avg_return: {selection.mean_avg_return:.2%}",
        f"mean_win_rate: {selection.mean_win_rate:.2%}",
        f"mean_profit_factor: {selection.mean_profit_factor:.2f}",
        f"worst_fold_return: {selection.worst_fold_return:.2%}",
        f"worst_fold_drawdown: {selection.worst_fold_drawdown:.2%}",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ranking = pd.read_csv(DEFAULT_RANKING_PATH)
    selection = select_strategy(ranking)
    write_selection(selection)
    print(DEFAULT_OUTPUT_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
