from __future__ import annotations

import pandas as pd

from trading_lab.config.targets import PredictionTarget


def _threshold_label(value: float) -> str:
    return f"{value:.0%}".replace("%", "pct")


def target_column(target: PredictionTarget) -> str:
    if target.mode == "horizon_return":
        return f"{target.symbol.upper()}_horizon_return_{target.horizon_days}d"
    if target.mode == "threshold_horizon_return":
        return (
            f"{target.symbol.upper()}_threshold_horizon_return_"
            f"up{_threshold_label(target.up_threshold)}_{target.horizon_days}d"
        )
    return f"{target.symbol.upper()}_hit_up_before_down_{target.horizon_days}d"


def add_hit_up_before_down_target(
    df: pd.DataFrame,
    target: PredictionTarget,
    price_col: str | None = None,
) -> pd.DataFrame:
    price_col = price_col or target.symbol.upper()
    out = df.copy()

    future = out[price_col].shift(-1)
    hit_values: list[float | None] = []

    for idx in range(len(out)):
        entry = out.iloc[idx][price_col]
        future_prices = out.iloc[idx + 1 : idx + 1 + target.horizon_days][price_col]

        if pd.isna(entry) or future_prices.empty or future_prices.isna().all():
            hit_values.append(None)
            continue

        upper = entry * (1.0 + target.up_threshold)
        lower = entry * (1.0 + target.down_threshold)

        label = None
        for price in future_prices:
            if pd.isna(price):
                continue
            if price >= upper:
                label = 1
                break
            if price <= lower:
                label = 0
                break

        hit_values.append(label)

    out[target_column(target)] = hit_values
    return out


def add_horizon_return_target(
    df: pd.DataFrame,
    target: PredictionTarget,
    price_col: str | None = None,
) -> pd.DataFrame:
    price_col = price_col or target.symbol.upper()
    out = df.copy()
    forward_return = out[price_col].shift(-target.horizon_days) / out[price_col] - 1.0
    out[target_column(target)] = (forward_return > 0).astype("float")
    out.loc[forward_return.isna(), target_column(target)] = None
    return out


def add_threshold_horizon_return_target(
    df: pd.DataFrame,
    target: PredictionTarget,
    price_col: str | None = None,
) -> pd.DataFrame:
    price_col = price_col or target.symbol.upper()
    out = df.copy()
    forward_return = out[price_col].shift(-target.horizon_days) / out[price_col] - 1.0
    out[target_column(target)] = (forward_return >= target.up_threshold).astype("float")
    out.loc[forward_return.isna(), target_column(target)] = None
    return out


def add_prediction_target(df: pd.DataFrame, target: PredictionTarget) -> pd.DataFrame:
    if target.mode == "barrier_first_hit":
        return add_hit_up_before_down_target(df, target)
    if target.mode == "horizon_return":
        return add_horizon_return_target(df, target)
    if target.mode == "threshold_horizon_return":
        return add_threshold_horizon_return_target(df, target)
    raise ValueError(f"Unsupported target mode: {target.mode}")


def add_prediction_targets(
    df: pd.DataFrame,
    targets: list[PredictionTarget],
) -> pd.DataFrame:
    out = df.copy()
    for target in targets:
        out = add_prediction_target(out, target)
    return out
