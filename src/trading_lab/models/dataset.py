from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from trading_lab.config import TradingColumns, TradingConfig, load_trading_config
from trading_lab.config.targets import PredictionTarget, default_prediction_targets
from trading_lab.features.targets import add_prediction_target
from trading_lab.features.targets import target_column as feature_target_column


FEATURE_PATH = Path("data/processed/market/market_features.csv")


def _config(config: TradingConfig | None = None) -> TradingConfig:
    return config or load_trading_config()


def load_market_features(path: Path = FEATURE_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def _feature_symbols(config: TradingConfig) -> list[str]:
    return list(
        dict.fromkeys(
            [
                config.core_symbol.upper(),
                config.benchmark_symbol.upper(),
                config.traded_symbol.upper(),
            ]
        )
    )


def feature_columns(df: pd.DataFrame, config: TradingConfig | None = None) -> list[str]:
    cfg = _config(config)
    cols = TradingColumns(cfg)
    symbols = _feature_symbols(cfg)
    prefixes = tuple(f"{symbol}_" for symbol in symbols)
    suffix_markers = (
        "_ret_",
        "_dist_ma_",
        "_vol_",
        "_drawdown_from_",
    )

    selected = [
        col
        for col in df.columns
        if col.startswith(prefixes) and any(marker in col for marker in suffix_markers)
    ]
    if cols.benchmark_uptrend in df.columns:
        selected.append(cols.benchmark_uptrend)
    return list(dict.fromkeys(selected))


def primary_prediction_target(config: TradingConfig | None = None) -> PredictionTarget:
    return default_prediction_targets(_config(config))[0]


def target_column(target: PredictionTarget) -> str:
    return feature_target_column(target)


def ensure_target_column(df: pd.DataFrame, target: PredictionTarget) -> pd.DataFrame:
    if target_column(target) in df.columns:
        return df
    return add_prediction_target(df, target)


def supervised_frame(
    df: pd.DataFrame,
    target: PredictionTarget | None = None,
    config: TradingConfig | None = None,
) -> tuple[pd.DataFrame, list[str], str]:
    cfg = _config(config)
    selected_target = target or primary_prediction_target(cfg)
    df = ensure_target_column(df, selected_target)
    target_col = target_column(selected_target)
    features = feature_columns(df, cfg)

    if target_col not in df.columns:
        raise ValueError(f"Missing target column: {target_col}")
    if not features:
        raise ValueError("No configured feature columns found")

    needed = list(dict.fromkeys(["date", target_col] + features))
    work = df[needed].replace([np.inf, -np.inf], np.nan).dropna(subset=[target_col] + features)
    work = work.copy()
    work["target"] = (work[target_col] == 1).astype(int)
    return work, features, target_col


def latest_feature_row(
    df: pd.DataFrame,
    config: TradingConfig | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    features = feature_columns(df, config)
    if not features:
        raise ValueError("No configured feature columns found")
    latest = df.replace([np.inf, -np.inf], np.nan).dropna(subset=features).iloc[-1:].copy()
    return latest, features


def train_test_split_time(
    df: pd.DataFrame,
    test_fraction: float = 0.30,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between 0 and 1")
    split_idx = int(len(df) * (1.0 - test_fraction))
    split_idx = min(max(split_idx, 1), max(len(df) - 1, 1))
    return df.iloc[:split_idx].copy(), df.iloc[split_idx:].copy()


def walk_forward_folds(df: pd.DataFrame, n_folds: int = 4) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
    if n_folds < 1:
        raise ValueError("n_folds must be at least 1")
    if len(df) < n_folds + 1:
        return []

    test_size = max(1, len(df) // (n_folds + 1))
    folds: list[tuple[pd.DataFrame, pd.DataFrame]] = []
    for fold_idx in range(n_folds):
        test_start = len(df) - test_size * (n_folds - fold_idx)
        test_end = test_start + test_size
        if test_start <= 0 or test_start >= len(df):
            continue
        train = df.iloc[:test_start].copy()
        test = df.iloc[test_start:test_end].copy()
        if not train.empty and not test.empty:
            folds.append((train, test))
    return folds
