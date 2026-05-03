from __future__ import annotations

import argparse
from pathlib import Path

from trading_lab.fifo import calculate_fifo_realized_pnl
from trading_lab.ingestion import load_robinhood_folder
from trading_lab.positions import reconstruct_positions


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Robinhood CSV exports.")
    parser.add_argument("--input", default="data/raw/robinhood", help="Folder containing Robinhood CSV exports.")
    parser.add_argument("--output", default="data/processed", help="Folder for processed outputs.")
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    trades = load_robinhood_folder(input_dir)
    realized = calculate_fifo_realized_pnl(trades) if not trades.empty else trades
    positions = reconstruct_positions(trades) if not trades.empty else trades

    trades.to_csv(output_dir / "normalized_trades.csv", index=False)
    realized.to_csv(output_dir / "realized_fifo_pnl.csv", index=False)
    positions.to_csv(output_dir / "positions.csv", index=False)

    print(f"Wrote {len(trades)} normalized trades to {output_dir / 'normalized_trades.csv'}")
    print(f"Wrote {len(realized)} realized FIFO rows to {output_dir / 'realized_fifo_pnl.csv'}")
    print(f"Wrote {len(positions)} position rows to {output_dir / 'positions.csv'}")


if __name__ == "__main__":
    main()
