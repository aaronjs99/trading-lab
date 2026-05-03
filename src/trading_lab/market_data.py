from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf


def download_prices(symbols: list[str], start: str, end: str | None = None) -> pd.DataFrame:
    data = yf.download(symbols, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        close = data["Close"].stack().rename("close").reset_index()
        close.columns = ["date", "symbol", "close"]
    else:
        close = data[["Close"]].rename(columns={"Close": "close"}).reset_index()
        close["symbol"] = symbols[0]
    close["date"] = pd.to_datetime(close["date"]).dt.date
    return close.sort_values(["symbol", "date"]).reset_index(drop=True)


def write_prices(symbols: list[str], start: str, output: str | Path, end: str | None = None) -> pd.DataFrame:
    prices = download_prices(symbols, start=start, end=end)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(output, index=False)
    return prices
