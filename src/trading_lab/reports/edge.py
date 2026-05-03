from __future__ import annotations

from pathlib import Path

import pandas as pd


def _date_column(df: pd.DataFrame) -> str:
    if "sold_at" in df.columns:
        return "sold_at"
    if "executed_at" in df.columns:
        return "executed_at"
    raise KeyError("Expected realized P&L dataframe to contain sold_at or executed_at")


def write_edge_report(realized: pd.DataFrame, output_dir: str | Path) -> pd.DataFrame:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    realized = realized.copy()

    realized.to_csv(output_dir / "realized_fifo_pnl.csv", index=False)

    summary_columns = [
        "symbol",
        "trades",
        "quantity",
        "realized_pnl",
        "win_rate",
        "avg_pnl",
        "profit_factor",
    ]

    if realized.empty:
        summary = pd.DataFrame(columns=summary_columns)
        summary.to_csv(output_dir / "symbol_summary.csv", index=False)
        pd.DataFrame(columns=["date", "equity_curve"]).to_csv(output_dir / "equity_curve.csv", index=False)
        return summary

    if "realized_pnl" not in realized.columns:
        raise KeyError("Expected realized P&L dataframe to contain realized_pnl")

    if "symbol" not in realized.columns:
        raise KeyError("Expected realized P&L dataframe to contain symbol")

    qty_col = "matched_quantity" if "matched_quantity" in realized.columns else "quantity"

    grouped = realized.groupby("symbol", dropna=False)

    gross_wins = grouped["realized_pnl"].apply(lambda s: s[s > 0].sum())
    gross_losses = grouped["realized_pnl"].apply(lambda s: abs(s[s < 0].sum()))

    summary = pd.DataFrame(
        {
            "symbol": grouped.size().index,
            "trades": grouped.size().values,
            "quantity": grouped[qty_col].sum().values if qty_col in realized.columns else grouped.size().values,
            "realized_pnl": grouped["realized_pnl"].sum().values,
            "win_rate": grouped["realized_pnl"].apply(lambda s: (s > 0).mean()).values,
            "avg_pnl": grouped["realized_pnl"].mean().values,
            "profit_factor": [
                (w / l if l > 0 else float("inf") if w > 0 else 0.0)
                for w, l in zip(gross_wins.values, gross_losses.values)
            ],
        }
    ).sort_values("realized_pnl", ascending=False)

    summary.to_csv(output_dir / "symbol_summary.csv", index=False)

    date_col = _date_column(realized)
    curve = realized.sort_values(date_col)["realized_pnl"].cumsum()
    equity_curve = pd.DataFrame(
        {
            "date": pd.to_datetime(realized.sort_values(date_col)[date_col], errors="coerce"),
            "equity_curve": curve.values,
        }
    )
    equity_curve.to_csv(output_dir / "equity_curve.csv", index=False)

    return summary


def main() -> None:
    from argparse import ArgumentParser

    import pandas as pd

    parser = ArgumentParser()
    parser.add_argument("--ledger", default="data/processed/ledger")
    parser.add_argument("--output-dir", default="data/reports")
    parser.add_argument("--trades", default=None)
    parser.add_argument("--output", default=None, help="Deprecated; use --output-dir.")
    args = parser.parse_args()

    ledger = Path(args.ledger)
    output_dir = Path(args.output_dir)
    trades_path = Path(args.trades) if args.trades else ledger / "realized_fifo_pnl.csv"

    realized = pd.read_csv(trades_path)
    write_edge_report(realized, output_dir)


if __name__ == "__main__":
    main()
