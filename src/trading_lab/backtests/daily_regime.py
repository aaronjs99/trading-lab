from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from trading_lab.config import TradingColumns, load_trading_config


FEATURE_PATH = Path("data/processed/market/market_features.csv")
PRED_PATH = Path("data/reports/regime_model_predictions.csv")
REPORT_DIR = Path("data/reports")


def max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min())


def summarize_strategy(name: str, daily_returns: pd.Series, exposure: pd.Series) -> dict:
    daily_returns = daily_returns.fillna(0.0)
    equity = (1.0 + daily_returns).cumprod()

    total_return = float(equity.iloc[-1] - 1.0)
    years = len(daily_returns) / 252
    cagr = float(equity.iloc[-1] ** (1 / years) - 1) if years > 0 else np.nan
    vol = float(daily_returns.std() * np.sqrt(252))
    sharpe = float((daily_returns.mean() * 252) / vol) if vol > 0 else np.nan

    active = exposure > 0
    active_returns = daily_returns[active]
    win_rate = float((active_returns > 0).mean()) if len(active_returns) else 0.0

    return {
        "strategy": name,
        "days": len(daily_returns),
        "active_days": int(active.sum()),
        "exposure_rate": float(active.mean()),
        "total_return": total_return,
        "cagr": cagr,
        "vol": vol,
        "sharpe_like": sharpe,
        "max_drawdown": max_drawdown(equity),
        "avg_daily_return": float(daily_returns.mean()),
        "active_win_rate": win_rate,
        "final_equity": float(equity.iloc[-1]),
    }


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    features = pd.read_csv(FEATURE_PATH)
    preds = pd.read_csv(PRED_PATH)
    config = load_trading_config()
    cols_cfg = TradingColumns(config)

    features["date"] = pd.to_datetime(features["date"], errors="coerce")
    preds["date"] = pd.to_datetime(preds["date"], errors="coerce")

    cols = [
        "date",
        cols_cfg.traded_price,
        cols_cfg.benchmark_price,
        f"{config.traded_symbol.upper()}_ret_1d",
        cols_cfg.benchmark_uptrend,
        cols_cfg.benchmark_dist_ma_20,
        cols_cfg.benchmark_dist_ma_50,
    ]
    cols = [c for c in cols if c in features.columns]

    df = preds.merge(features[cols], on="date", how="left").sort_values("date").reset_index(drop=True)

    # Use next-day return to avoid same-day lookahead.
    next_ret_col = f"next_{config.traded_symbol.lower()}_ret"
    df[next_ret_col] = df[cols_cfg.traded_price].shift(-1) / df[cols_cfg.traded_price] - 1.0
    df = df.dropna(subset=[next_ret_col]).copy()

    prob_col = "random_forest_proba"
    if prob_col not in df.columns:
        raise SystemExit(f"Missing prediction column: {prob_col}")

    strategies = []

    # Baselines.
    always_col = f"always_{config.traded_symbol.lower()}_exposure"
    df[always_col] = 1.0
    strategies.append(
        (
            f"always_{config.traded_symbol.lower()}",
            df[always_col] * df[next_ret_col],
            df[always_col],
        )
    )

    if cols_cfg.benchmark_uptrend in df.columns:
        trend_exposure = f"{config.benchmark_symbol.lower()}_20_50_exposure"
        df[trend_exposure] = df[cols_cfg.benchmark_uptrend].astype(float)
        strategies.append(
            (
                f"{config.benchmark_symbol.lower()}_20_50_filter",
                df[trend_exposure] * df[next_ret_col],
                df[trend_exposure],
            )
        )

    # Model thresholds.
    for threshold in [0.50, 0.55, 0.60, 0.65, 0.70]:
        exposure = (df[prob_col] >= threshold).astype(float)
        strategies.append((f"rf_prob_ge_{threshold:.2f}", exposure * df[next_ret_col], exposure))

    # Model plus trend filter.
    if cols_cfg.benchmark_uptrend in df.columns:
        trend = df[cols_cfg.benchmark_uptrend].astype(bool)
        for threshold in [0.50, 0.55, 0.60, 0.65, 0.70]:
            exposure = ((df[prob_col] >= threshold) & trend).astype(float)
            strategies.append(
                (f"rf_prob_ge_{threshold:.2f}_and_trend", exposure * df[next_ret_col], exposure)
            )

    rows = []
    curves = pd.DataFrame({"date": df["date"]})

    for name, returns, exposure in strategies:
        rows.append(summarize_strategy(name, returns, exposure))
        curves[name] = (1.0 + returns.fillna(0.0)).cumprod()

    summary = pd.DataFrame(rows).sort_values("sharpe_like", ascending=False)
    summary.to_csv(REPORT_DIR / "regime_strategy_summary.csv", index=False)
    curves.to_csv(REPORT_DIR / "regime_strategy_equity_curves.csv", index=False)

    print("== Regime strategy summary ==")
    print(summary.to_string(index=False))

    print()
    print("== Latest model signal ==")
    latest = df.iloc[-1]
    latest_cols = [
        "date",
        cols_cfg.traded_price,
        cols_cfg.benchmark_price,
        prob_col,
        cols_cfg.benchmark_uptrend,
        cols_cfg.benchmark_dist_ma_20,
        cols_cfg.benchmark_dist_ma_50,
    ]
    latest_cols = [c for c in latest_cols if c in df.columns]
    for c in latest_cols:
        print(f"{c}: {latest[c]}")

    print()
    print("Wrote:")
    print(REPORT_DIR / "regime_strategy_summary.csv")
    print(REPORT_DIR / "regime_strategy_equity_curves.csv")


if __name__ == "__main__":
    main()
