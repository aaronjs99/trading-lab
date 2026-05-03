from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from trading_lab.fifo import calculate_fifo_realized_pnl
from trading_lab.reports import write_edge_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run realized P&L edge report.")
    parser.add_argument("--trades", default="data/processed/normalized_trades.csv", help="Normalized trades CSV.")
    parser.add_argument("--output", default="data/reports", help="Report output folder.")
    args = parser.parse_args()

    trades = pd.read_csv(args.trades, parse_dates=["executed_at"])
    realized = calculate_fifo_realized_pnl(trades)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    realized.to_csv(output_dir / "realized_fifo_pnl.csv", index=False)
    summary = write_edge_report(realized, output_dir)
    print(summary.to_string(index=False))
    print(f"Wrote edge report outputs under {output_dir}")


if __name__ == "__main__":
    main()
