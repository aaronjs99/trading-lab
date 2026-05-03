from __future__ import annotations

from pathlib import Path

import pandas as pd


BUCKET_PATH = Path("data/reports/bucket_summary.csv")
SYMBOL_BUCKET_PATH = Path("data/reports/symbol_bucket_summary.csv")


FOCUS_SYMBOLS = ["SPY", "TQQQ", "QQQ", "SQQQ", "TSLA"]


def build_personal_edge_summary(
    bucket_path: Path = BUCKET_PATH,
    symbol_bucket_path: Path = SYMBOL_BUCKET_PATH,
) -> list[str]:
    if not bucket_path.exists() or not symbol_bucket_path.exists():
        return [
            "Personal trading edge:",
            "- No Robinhood bucket report found. Run ./scripts/run_robinhood_pipeline.sh and ./scripts/analyze_buckets.sh.",
        ]

    buckets = pd.read_csv(bucket_path)
    symbols = pd.read_csv(symbol_bucket_path)

    buckets = buckets.sort_values("realized_pnl", ascending=False)
    best = buckets.iloc[0]

    lines = [
        "Personal trading edge:",
        (
            f"- Best bucket: {best['bucket']} "
            f"PnL ${float(best['realized_pnl']):,.2f}, "
            f"win rate {float(best['win_rate']):.1%}, "
            f"profit factor {float(best['profit_factor']):.2f}"
        ),
    ]

    focus = symbols[symbols["symbol"].isin(FOCUS_SYMBOLS)].copy()
    order = {sym: i for i, sym in enumerate(FOCUS_SYMBOLS)}
    focus["sort_order"] = focus["symbol"].map(order)
    focus = focus.sort_values("sort_order")

    for _, row in focus.iterrows():
        symbol = row["symbol"]
        pnl = float(row["realized_pnl"])
        win_rate = float(row["win_rate"])
        rows = int(row["rows"])
        lines.append(f"- {symbol}: PnL ${pnl:,.2f}, win rate {win_rate:.1%}, rows {rows}")

    bad = buckets[buckets["realized_pnl"] < 0].sort_values("realized_pnl")
    if not bad.empty:
        avoid = ", ".join(bad["bucket"].head(3).astype(str).tolist())
        lines.append(f"- Avoid/leakage buckets: {avoid}")

    lines.append("- Operating rule: prioritize SPY/QQQ/TQQQ long setups; treat SQQQ/inverse trades as hedge-only.")
    return lines
