from __future__ import annotations

import numpy as np
import pandas as pd


def summarize_realized_by_symbol(realized: pd.DataFrame) -> pd.DataFrame:
    if realized.empty:
        return pd.DataFrame(
            columns=["symbol", "trades", "quantity", "realized_pnl", "win_rate", "avg_pnl", "profit_factor"]
        )

    grouped = realized.groupby("symbol")
    summary = grouped.agg(
        trades=("realized_pnl", "count"),
        quantity=("quantity", "sum"),
        realized_pnl=("realized_pnl", "sum"),
        avg_pnl=("realized_pnl", "mean"),
    )
    wins = grouped["realized_pnl"].apply(lambda values: (values > 0).mean())
    gross_profit = grouped["realized_pnl"].apply(lambda values: values[values > 0].sum())
    gross_loss = grouped["realized_pnl"].apply(lambda values: values[values < 0].sum())
    summary["win_rate"] = wins
    summary["profit_factor"] = gross_profit / gross_loss.abs().replace(0, np.nan)
    return summary.reset_index().sort_values("realized_pnl", ascending=False)


def equity_curve_metrics(equity: pd.Series) -> dict[str, float]:
    if equity.empty:
        return {"total_return": 0.0, "max_drawdown": 0.0, "sharpe": 0.0}

    returns = equity.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    total_return = equity.iloc[-1] / equity.iloc[0] - 1 if equity.iloc[0] else 0.0
    drawdown = equity / equity.cummax() - 1
    sharpe = 0.0
    if returns.std(ddof=0) > 0:
        sharpe = float(np.sqrt(252) * returns.mean() / returns.std(ddof=0))
    return {
        "total_return": float(total_return),
        "max_drawdown": float(drawdown.min()),
        "sharpe": sharpe,
    }
