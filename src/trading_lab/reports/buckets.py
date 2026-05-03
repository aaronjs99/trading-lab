from __future__ import annotations

from pathlib import Path

import pandas as pd


LEDGER_PATH = Path("data/processed/ledger/realized_fifo_pnl.csv")
REPORT_DIR = Path("data/reports")

CORE_INDEX = {"SPY", "QQQ", "TQQQ"}
INVERSE = {"SQQQ", "SARK"}
MEGA_CAP = {"AAPL", "MSFT", "AMZN", "GOOGL", "GOOG", "META", "NVDA", "TSLA", "NFLX"}
COMMODITIES = {"GLD", "SLV", "BNO", "UNG", "USO", "SIVR"}


def bucket_symbol(symbol: str) -> str:
    sym = str(symbol).upper()
    if sym in CORE_INDEX:
        return "core_index_long"
    if sym in INVERSE:
        return "inverse_bearish"
    if sym in MEGA_CAP:
        return "mega_cap_single_name"
    if sym in COMMODITIES:
        return "commodity_macro"
    return "random_single_name"


def _profit_factor(series: pd.Series) -> float:
    gross_wins = series[series > 0].sum()
    gross_losses = series[series < 0].sum()
    if gross_losses < 0:
        return float(gross_wins / abs(gross_losses))
    if gross_wins > 0:
        return float("inf")
    return 0.0


def load_realized_pnl(path: Path = LEDGER_PATH) -> pd.DataFrame:
    realized = pd.read_csv(path)
    if "basis_status" in realized.columns:
        realized = realized[realized["basis_status"].eq("known")].copy()
    return realized


def build_bucket_reports(realized: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = realized.copy()
    df["bucket"] = df["symbol"].map(bucket_symbol)

    bucket_summary = (
        df.groupby("bucket")
        .agg(
            rows=("realized_pnl", "size"),
            symbols=("symbol", "nunique"),
            realized_pnl=("realized_pnl", "sum"),
            win_rate=("realized_pnl", lambda s: (s > 0).mean()),
            avg_pnl=("realized_pnl", "mean"),
            gross_wins=("realized_pnl", lambda s: s[s > 0].sum()),
            gross_losses=("realized_pnl", lambda s: s[s < 0].sum()),
            profit_factor=("realized_pnl", _profit_factor),
        )
        .reset_index()
        .sort_values("realized_pnl", ascending=False)
    )

    symbol_summary = (
        df.groupby(["bucket", "symbol"])
        .agg(
            rows=("realized_pnl", "size"),
            realized_pnl=("realized_pnl", "sum"),
            win_rate=("realized_pnl", lambda s: (s > 0).mean()),
            avg_pnl=("realized_pnl", "mean"),
        )
        .reset_index()
        .sort_values("realized_pnl", ascending=False)
    )

    return bucket_summary, symbol_summary


def write_bucket_report_markdown(
    bucket_summary: pd.DataFrame,
    symbol_summary: pd.DataFrame,
    report_dir: Path = REPORT_DIR,
) -> Path:
    lines = [
        "# Bucket Analysis",
        "",
        "## Bucket summary",
        "```",
        bucket_summary.to_string(index=False),
        "```",
        "",
        "## Top symbols",
        "```",
        symbol_summary.head(40).to_string(index=False),
        "```",
        "",
        "## Worst symbols",
        "```",
        symbol_summary.sort_values("realized_pnl").head(40).to_string(index=False),
        "```",
        "",
        "## Interpretation",
        "- Core index longs are the cleanest edge if they remain strongly positive.",
        "- Inverse/bearish trades should be treated as experimental unless they clearly outperform.",
        "- Random single-name trades are the likely source of most leakage if they show many symbols and poor total P&L.",
        "- The next system should allocate capital to the buckets that show repeatable edge, not buckets that only create action.",
    ]

    path = report_dir / "bucket_analysis.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_bucket_analysis(
    ledger_path: Path = LEDGER_PATH,
    report_dir: Path = REPORT_DIR,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    report_dir.mkdir(parents=True, exist_ok=True)

    realized = load_realized_pnl(ledger_path)
    bucket_summary, symbol_summary = build_bucket_reports(realized)

    bucket_summary.to_csv(report_dir / "bucket_summary.csv", index=False)
    symbol_summary.to_csv(report_dir / "symbol_bucket_summary.csv", index=False)
    write_bucket_report_markdown(bucket_summary, symbol_summary, report_dir)

    return bucket_summary, symbol_summary


def main() -> None:
    bucket_summary, symbol_summary = run_bucket_analysis()

    print("== Bucket summary ==")
    print(bucket_summary.to_string(index=False))

    print()
    print("== Top symbols by bucketed realized P&L ==")
    print(symbol_summary.head(25).to_string(index=False))

    print()
    print("== Worst symbols by bucketed realized P&L ==")
    print(symbol_summary.sort_values("realized_pnl").head(25).to_string(index=False))

    print()
    print("Wrote:")
    print(REPORT_DIR / "bucket_summary.csv")
    print(REPORT_DIR / "symbol_bucket_summary.csv")
    print(REPORT_DIR / "bucket_analysis.md")


if __name__ == "__main__":
    main()
