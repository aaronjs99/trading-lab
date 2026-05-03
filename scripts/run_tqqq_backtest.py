from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from trading_lab.backtest import LadderConfig, run_tqqq_ladder_backtest


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TQQQ/SPY long-biased ladder backtest.")
    parser.add_argument("--market-data", default="data/processed/market_data.csv", help="Market data CSV.")
    parser.add_argument("--output", default="data/reports", help="Report output folder.")
    parser.add_argument("--initial-cash", type=float, default=100_000.0)
    args = parser.parse_args()

    market_data = pd.read_csv(args.market_data, parse_dates=["date"])
    config = LadderConfig(initial_cash=args.initial_cash)
    results, metrics = run_tqqq_ladder_backtest(market_data, config)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_dir / "tqqq_ladder_backtest.csv", index=False)
    pd.DataFrame([metrics]).to_csv(output_dir / "tqqq_ladder_metrics.csv", index=False)

    print(pd.DataFrame([metrics]).to_string(index=False))
    print(f"Wrote backtest outputs under {output_dir}")


if __name__ == "__main__":
    main()
