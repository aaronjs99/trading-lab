from __future__ import annotations

from functools import reduce
from pathlib import Path

import numpy as np
import pandas as pd

from trading_lab.config import load_trading_config
from trading_lab.config.targets import default_prediction_targets
from trading_lab.features.targets import add_prediction_targets


DEFAULT_MARKET_DIR = Path("data/raw/market")
DEFAULT_OUTPUT_PATH = Path("data/processed/market/market_features.csv")


def load_price_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    lower = {str(col).lower(): col for col in df.columns}

    date_col = lower.get("date") or lower.get("datetime")
    close_col = lower.get("close") or lower.get("adj close") or lower.get("adj_close")

    if date_col is None or close_col is None:
        raise ValueError(f"Could not find date/close columns in {path}. Columns={list(df.columns)}")

    out = df[[date_col, close_col]].copy()
    out.columns = ["date", path.stem.upper()]
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    return out.dropna(subset=["date"]).sort_values("date")


def add_price_features(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    out = df.copy()
    px = out[symbol].astype(float)

    for window in [1, 3, 5, 10, 20]:
        out[f"{symbol}_ret_{window}d"] = px.pct_change(window)

    for window in [20, 50, 100]:
        ma = px.rolling(window).mean()
        out[f"{symbol}_ma_{window}"] = ma
        out[f"{symbol}_dist_ma_{window}"] = px / ma - 1.0

    for window in [5, 20]:
        out[f"{symbol}_vol_{window}d"] = px.pct_change().rolling(window).std() * np.sqrt(252)

    for window in [20, 60]:
        high = px.rolling(window).max()
        out[f"{symbol}_drawdown_from_{window}d_high"] = px / high - 1.0

    return out


def add_uptrend_feature(df: pd.DataFrame, symbol: str, fast: int = 20, slow: int = 50) -> pd.DataFrame:
    out = df.copy()
    fast_col = f"{symbol}_ma_{fast}"
    slow_col = f"{symbol}_ma_{slow}"

    if fast_col in out.columns and slow_col in out.columns:
        out[f"{symbol}_uptrend_{fast}_{slow}"] = out[fast_col] > out[slow_col]

    return out


def configured_feature_symbols(config_symbols: list[str], available_symbols: set[str]) -> list[str]:
    return [symbol.upper() for symbol in config_symbols if symbol.upper() in available_symbols]


def merge_price_frames(paths: list[Path]) -> pd.DataFrame:
    frames = [load_price_csv(path) for path in paths]
    if not frames:
        raise SystemExit(
            f"No market CSVs found. Run scripts/update_market_data.py first or place CSVs under {DEFAULT_MARKET_DIR}."
        )
    return reduce(lambda left, right: left.merge(right, on="date", how="outer"), frames).sort_values("date").reset_index(drop=True)


def build_market_features(
    market_dir: Path = DEFAULT_MARKET_DIR,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> pd.DataFrame:
    config = load_trading_config()
    paths = sorted(market_dir.glob("*.csv"))
    merged = merge_price_frames(paths)

    desired_symbols = [
        config.core_symbol,
        config.benchmark_symbol,
        config.traded_symbol,
        config.inverse_symbol,
    ]
    symbols = configured_feature_symbols(desired_symbols, set(merged.columns))

    features = merged
    for symbol in symbols:
        features = add_price_features(features, symbol)

    features = add_uptrend_feature(features, config.benchmark_symbol.upper())
    features = add_prediction_targets(features, default_prediction_targets(config))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(output_path, index=False)
    return features


def main() -> None:
    df = build_market_features()
    print(f"Wrote {DEFAULT_OUTPUT_PATH}")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")


if __name__ == "__main__":
    main()
