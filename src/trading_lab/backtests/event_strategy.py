from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from trading_lab.config import TradingColumns, TradingConfig, load_trading_config


FEATURE_PATH = Path("data/processed/market/market_features.csv")
PRED_PATH = Path("data/reports/regime_model_predictions.csv")
REPORT_DIR = Path("data/reports")


def run_event_backtest(
    df: pd.DataFrame,
    name: str,
    prob_threshold: float,
    require_trend: bool,
    max_extension_ma20: float | None,
    min_drawdown_20d: float | None,
    take_profit: float,
    stop_loss: float,
    max_hold_days: int,
    cooldown_days: int,
    config: TradingConfig | None = None,
) -> dict:
    trades = []
    i = 0
    cfg = config or load_trading_config()
    cols = TradingColumns(cfg)

    while i < len(df) - max_hold_days - 1:
        row = df.iloc[i]

        if row["random_forest_proba"] < prob_threshold:
            i += 1
            continue

        if require_trend and not bool(row.get(cols.benchmark_uptrend, False)):
            i += 1
            continue

        if max_extension_ma20 is not None:
            if row.get(cols.benchmark_dist_ma_20, np.nan) > max_extension_ma20:
                i += 1
                continue

        if min_drawdown_20d is not None:
            if row.get(cols.traded_drawdown_20d, np.nan) > min_drawdown_20d:
                i += 1
                continue

        entry_price = float(row[cols.traded_price])
        entry_date = row["date"]

        exit_reason = "timeout"
        exit_idx = min(i + max_hold_days, len(df) - 1)
        exit_price = float(df.iloc[exit_idx][cols.traded_price])

        for j in range(i + 1, min(i + max_hold_days + 1, len(df))):
            px = float(df.iloc[j][cols.traded_price])
            ret = px / entry_price - 1.0

            if ret >= take_profit:
                exit_idx = j
                exit_price = px
                exit_reason = "take_profit"
                break

            if ret <= -stop_loss:
                exit_idx = j
                exit_price = px
                exit_reason = "stop_loss"
                break

        ret = exit_price / entry_price - 1.0

        trades.append(
            {
                "strategy": name,
                "entry_date": entry_date,
                "exit_date": df.iloc[exit_idx]["date"],
                "entry_price": entry_price,
                "exit_price": exit_price,
                "return": ret,
                "exit_reason": exit_reason,
                "prob": row["random_forest_proba"],
                f"{cfg.benchmark_symbol.lower()}_trend": row.get(cols.benchmark_uptrend, np.nan),
                f"{cfg.benchmark_symbol.lower()}_dist_ma20": row.get(
                    cols.benchmark_dist_ma_20,
                    np.nan,
                ),
                f"{cfg.traded_symbol.lower()}_drawdown_20d": row.get(
                    cols.traded_drawdown_20d,
                    np.nan,
                ),
                "hold_days": exit_idx - i,
            }
        )

        i = exit_idx + cooldown_days

    trades_df = pd.DataFrame(trades)

    if trades_df.empty:
        return {
            "strategy": name,
            "trades": 0,
            "total_return_compounded": 0.0,
            "avg_trade_return": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "max_loss": 0.0,
            "max_gain": 0.0,
            "avg_hold_days": 0.0,
            "take_profit_rate": 0.0,
            "stop_loss_rate": 0.0,
            "timeout_rate": 0.0,
        }

    gross_wins = trades_df.loc[trades_df["return"] > 0, "return"].sum()
    gross_losses = trades_df.loc[trades_df["return"] < 0, "return"].sum()

    return {
        "strategy": name,
        "trades": len(trades_df),
        "total_return_compounded": float((1.0 + trades_df["return"]).prod() - 1.0),
        "avg_trade_return": float(trades_df["return"].mean()),
        "win_rate": float((trades_df["return"] > 0).mean()),
        "profit_factor": float(gross_wins / abs(gross_losses)) if gross_losses < 0 else float("inf"),
        "max_loss": float(trades_df["return"].min()),
        "max_gain": float(trades_df["return"].max()),
        "avg_hold_days": float(trades_df["hold_days"].mean()),
        "take_profit_rate": float((trades_df["exit_reason"] == "take_profit").mean()),
        "stop_loss_rate": float((trades_df["exit_reason"] == "stop_loss").mean()),
        "timeout_rate": float((trades_df["exit_reason"] == "timeout").mean()),
    }, trades_df


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    features = pd.read_csv(FEATURE_PATH)
    preds = pd.read_csv(PRED_PATH)
    config = load_trading_config()
    cols_cfg = TradingColumns(config)

    features["date"] = pd.to_datetime(features["date"], errors="coerce")
    preds["date"] = pd.to_datetime(preds["date"], errors="coerce")

    keep = [
        "date",
        cols_cfg.traded_price,
        cols_cfg.benchmark_price,
        cols_cfg.benchmark_uptrend,
        cols_cfg.benchmark_dist_ma_20,
        cols_cfg.benchmark_dist_ma_50,
        cols_cfg.traded_drawdown_20d,
        f"{config.traded_symbol.upper()}_drawdown_from_60d_high",
        f"{config.traded_symbol.upper()}_vol_20d",
    ]
    keep = [c for c in keep if c in features.columns]

    df = preds.merge(features[keep], on="date", how="left").sort_values("date").reset_index(drop=True)
    df = df.dropna(subset=[cols_cfg.traded_price, "random_forest_proba"]).copy()

    configs = []

    for threshold in [0.50, 0.55, 0.60, 0.65]:
        configs.append(
            {
                "name": f"rf_{threshold:.2f}_tp5_sl5_hold5",
                "prob_threshold": threshold,
                "require_trend": False,
                "max_extension_ma20": None,
                "min_drawdown_20d": None,
                "take_profit": 0.05,
                "stop_loss": 0.05,
                "max_hold_days": 5,
                "cooldown_days": 2,
            }
        )

    for threshold in [0.50, 0.55, 0.60]:
        configs.append(
            {
                "name": f"rf_{threshold:.2f}_trend_not_ext_tp5_sl5_hold5",
                "prob_threshold": threshold,
                "require_trend": True,
                "max_extension_ma20": 0.04,
                "min_drawdown_20d": None,
                "take_profit": 0.05,
                "stop_loss": 0.05,
                "max_hold_days": 5,
                "cooldown_days": 2,
            }
        )

    for threshold in [0.50, 0.55, 0.60]:
        configs.append(
            {
                "name": f"rf_{threshold:.2f}_pullback_tp5_sl5_hold5",
                "prob_threshold": threshold,
                "require_trend": True,
                "max_extension_ma20": 0.05,
                "min_drawdown_20d": -0.03,
                "take_profit": 0.05,
                "stop_loss": 0.05,
                "max_hold_days": 5,
                "cooldown_days": 2,
            }
        )

    rows = []
    all_trades = []

    for cfg in configs:
        result = run_event_backtest(
            df=df,
            name=cfg["name"],
            prob_threshold=cfg["prob_threshold"],
            require_trend=cfg["require_trend"],
            max_extension_ma20=cfg["max_extension_ma20"],
            min_drawdown_20d=cfg["min_drawdown_20d"],
            take_profit=cfg["take_profit"],
            stop_loss=cfg["stop_loss"],
            max_hold_days=cfg["max_hold_days"],
            cooldown_days=cfg["cooldown_days"],
            config=config,
        )

        if isinstance(result, tuple):
            summary, trades = result
            all_trades.append(trades)
        else:
            summary = result

        rows.append(summary)

    summary_df = pd.DataFrame(rows).sort_values(
        ["profit_factor", "avg_trade_return", "total_return_compounded"],
        ascending=False,
    )

    summary_df.to_csv(REPORT_DIR / "event_strategy_summary.csv", index=False)

    if all_trades:
        trades_df = pd.concat(all_trades, ignore_index=True)
    else:
        trades_df = pd.DataFrame()

    trades_df.to_csv(REPORT_DIR / "event_strategy_trades.csv", index=False)

    print("== Event strategy summary ==")
    print(summary_df.to_string(index=False))

    print()
    print("== Best strategy trades preview ==")
    if not trades_df.empty and not summary_df.empty:
        best = summary_df.iloc[0]["strategy"]
        print("Best:", best)
        print(trades_df[trades_df["strategy"] == best].tail(20).to_string(index=False))

    print()
    print("Wrote:")
    print(REPORT_DIR / "event_strategy_summary.csv")
    print(REPORT_DIR / "event_strategy_trades.csv")


if __name__ == "__main__":
    main()
