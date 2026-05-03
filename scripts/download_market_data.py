from __future__ import annotations

import argparse

from trading_lab.market_data import write_prices


def main() -> None:
    parser = argparse.ArgumentParser(description="Download historical market data.")
    parser.add_argument("--symbols", nargs="+", default=["SPY", "TQQQ"], help="Ticker symbols to download.")
    parser.add_argument("--start", default="2018-01-01", help="Start date, YYYY-MM-DD.")
    parser.add_argument("--end", default=None, help="Optional end date, YYYY-MM-DD.")
    parser.add_argument("--output", default="data/processed/market_data.csv", help="Output CSV path.")
    args = parser.parse_args()

    prices = write_prices(args.symbols, start=args.start, end=args.end, output=args.output)
    print(f"Wrote {len(prices)} price rows to {args.output}")


if __name__ == "__main__":
    main()
