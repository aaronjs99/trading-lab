from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

from trading_lab.portfolio.state import collect_portfolio_symbols


DEFAULT_SYMBOLS_PATH = Path("config/market_symbols.txt")
DEFAULT_OUT_DIR = Path("data/raw/market")
DEFAULT_START = "2010-01-01"


def load_market_symbols(path: Path = DEFAULT_SYMBOLS_PATH) -> list[str]:
    if not path.exists():
        return [
            "AAPL",
            "AMD",
            "AMZN",
            "AVGO",
            "GOOGL",
            "HOOD",
            "META",
            "MSFT",
            "NVDA",
            "PLTR",
            "QQQ",
            "SMH",
            "SOXX",
            "SPY",
            "SQQQ",
            "TQQQ",
            "TSLA",
            "XLK",
        ]

    symbols = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        symbol = raw.strip().upper()
        if not symbol or symbol.startswith("#"):
            continue
        symbols.append(symbol)

    return symbols


def market_symbol_universe(config_symbols: list[str] | None = None) -> list[str]:
    """Return configured market symbols plus symbols found in local portfolio CSVs."""
    symbols = load_market_symbols() if config_symbols is None else config_symbols
    combined: dict[str, None] = {}
    for symbol in [*symbols, *collect_portfolio_symbols()]:
        clean = symbol.strip().upper()
        if clean:
            combined[clean] = None
    return list(combined)


def csv_has_today_data(path: Path, today: date | None = None) -> bool:
    """Return True when this CSV file has already been refreshed today.

    This checks the file modification date, not the newest market row date. On
    weekends and market holidays, the newest valid market row can be older than
    today's calendar date, but we still do not want to redownload repeatedly.
    """
    today = today or date.today()
    if not path.exists():
        return False

    modified = date.fromtimestamp(path.stat().st_mtime)
    return modified >= today


def _normalize_download(symbol: str, raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        raise ValueError(f"No data returned for {symbol}")

    df = raw.copy()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [
            "_".join(str(part) for part in col if part).strip("_")
            for col in df.columns.to_flat_index()
        ]

    df = df.reset_index()

    lower = {str(col).lower(): col for col in df.columns}
    date_col = lower.get("date") or lower.get("datetime")
    close_col = (
        lower.get("close")
        or lower.get(f"close_{symbol.lower()}")
        or lower.get("adj close")
        or lower.get(f"adj close_{symbol.lower()}")
        or lower.get("adj_close")
    )

    if date_col is None or close_col is None:
        close_candidates = [col for col in df.columns if str(col).lower().startswith("close")]
        if close_candidates:
            close_col = close_candidates[0]

    if date_col is None or close_col is None:
        raise ValueError(f"Could not identify date/close columns for {symbol}: {list(df.columns)}")

    out = df[[date_col, close_col]].copy()
    out.columns = ["date", "close"]
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.date
    out["close"] = pd.to_numeric(out["close"], errors="coerce")
    out = out.dropna(subset=["date", "close"]).drop_duplicates(subset=["date"]).sort_values("date")

    if out.empty:
        raise ValueError(f"No usable date/close rows for {symbol}")

    return out


def download_symbol(symbol: str, start: str = DEFAULT_START) -> pd.DataFrame:
    raw = yf.download(symbol, start=start, auto_adjust=True, progress=False)
    return _normalize_download(symbol, raw)


def update_market_data(
    symbols: list[str] | None = None,
    out_dir: Path = DEFAULT_OUT_DIR,
    start: str = DEFAULT_START,
    force: bool = False,
) -> dict[str, int]:
    symbols = symbols or market_symbol_universe()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Updating {len(symbols)} market CSVs under {out_dir}")
    print("Symbols:", ", ".join(symbols))

    downloaded = 0
    skipped = 0
    failed = 0
    failed_symbols: list[str] = []

    for symbol in symbols:
        out_path = out_dir / f"{symbol}.csv"

        if not force and csv_has_today_data(out_path):
            print(f"SKIP {symbol}: already updated today -> {out_path}")
            skipped += 1
            continue

        try:
            df = download_symbol(symbol, start=start)
            df.to_csv(out_path, index=False)
            print(f"OK {symbol}: {len(df)} rows -> {out_path}")
            downloaded += 1
        except Exception as exc:
            print(f"FAILED {symbol}: {exc}")
            failed += 1
            failed_symbols.append(symbol)

    print()
    print(f"Downloaded: {downloaded}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")

    if failed_symbols:
        print("Failed symbols:", ", ".join(failed_symbols))

    return {
        "downloaded": downloaded,
        "skipped": skipped,
        "failed": failed,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Download even if CSVs were refreshed today.")
    parser.add_argument("--start", default=DEFAULT_START)
    args = parser.parse_args()

    update_market_data(start=args.start, force=args.force)


if __name__ == "__main__":
    main()
