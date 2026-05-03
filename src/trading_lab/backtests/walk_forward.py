from __future__ import annotations

from pathlib import Path
from itertools import product

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from trading_lab.signals.latest_regime import regime_feature_columns


FEATURE_PATH = Path("data/processed/market/market_features.csv")
REPORT_DIR = Path("data/reports")


def _max_drawdown(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    equity = (1.0 + returns.fillna(0.0)).cumprod()
    return float((equity / equity.cummax() - 1.0).min())


def _event_returns(
    df: pd.DataFrame,
    prob_col: str,
    threshold: float,
    take_profit: float,
    stop_loss: float,
    max_hold: int,
    require_trend: bool,
    max_ext20: float | None,
    cooldown: int = 2,
) -> pd.DataFrame:
    trades = []
    i = 0

    while i < len(df) - max_hold - 1:
        row = df.iloc[i]

        if float(row[prob_col]) < threshold:
            i += 1
            continue

        if require_trend and not bool(row["QQQ_uptrend_20_50"]):
            i += 1
            continue

        if max_ext20 is not None and float(row["QQQ_dist_ma_20"]) > max_ext20:
            i += 1
            continue

        entry = float(row["TQQQ"])
        exit_idx = min(i + max_hold, len(df) - 1)
        exit_px = float(df.iloc[exit_idx]["TQQQ"])
        reason = "timeout"

        for j in range(i + 1, min(i + max_hold + 1, len(df))):
            px = float(df.iloc[j]["TQQQ"])
            ret = px / entry - 1.0
            if ret >= take_profit:
                exit_idx = j
                exit_px = px
                reason = "take_profit"
                break
            if ret <= -stop_loss:
                exit_idx = j
                exit_px = px
                reason = "stop_loss"
                break

        trades.append(
            {
                "entry_date": row["date"],
                "exit_date": df.iloc[exit_idx]["date"],
                "return": exit_px / entry - 1.0,
                "exit_reason": reason,
                "hold_days": exit_idx - i,
            }
        )

        i = exit_idx + cooldown

    return pd.DataFrame(trades)


def _summarize(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {
            "trades": 0,
            "total_return": 0.0,
            "avg_return": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
        }

    rets = trades["return"]
    wins = rets[rets > 0].sum()
    losses = rets[rets < 0].sum()

    return {
        "trades": len(trades),
        "total_return": float((1.0 + rets).prod() - 1.0),
        "avg_return": float(rets.mean()),
        "win_rate": float((rets > 0).mean()),
        "profit_factor": float(wins / abs(losses)) if losses < 0 else float("inf"),
        "max_drawdown": _max_drawdown(rets),
    }


def _param_grid() -> list[dict]:
    rows = []
    for threshold, take_profit, stop_loss, max_hold, require_trend, max_ext20 in product(
        [0.50, 0.55, 0.60, 0.65],
        [0.04, 0.05, 0.06],
        [0.04, 0.05, 0.06],
        [3, 5, 7],
        [False, True],
        [None, 0.04, 0.06],
    ):
        rows.append(
            {
                "threshold": threshold,
                "take_profit": take_profit,
                "stop_loss": stop_loss,
                "max_hold": max_hold,
                "require_trend": require_trend,
                "max_ext20": max_ext20,
            }
        )
    return rows


def walk_forward_optimize(
    feature_path: Path = FEATURE_PATH,
    report_dir: Path = REPORT_DIR,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    report_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(feature_path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    target_col = "TQQQ_hit_up_before_down_5d"
    feature_cols = regime_feature_columns(df)

    needed = list(dict.fromkeys(
        ["date", "TQQQ", "QQQ_uptrend_20_50", "QQQ_dist_ma_20", target_col] + feature_cols
    ))
    work = df[needed].replace([np.inf, -np.inf], np.nan).dropna().copy()
    work["target"] = (work[target_col] == 1).astype(int)

    folds = [
        ("2021_2022", "2012-01-01", "2020-12-31", "2021-01-01", "2022-12-31"),
        ("2023", "2012-01-01", "2022-12-31", "2023-01-01", "2023-12-31"),
        ("2024", "2012-01-01", "2023-12-31", "2024-01-01", "2024-12-31"),
        ("2025_2026", "2012-01-01", "2024-12-31", "2025-01-01", "2026-12-31"),
    ]

    param_grid = _param_grid()
    summary_rows = []
    all_trades = []

    for fold, train_start, train_end, test_start, test_end in folds:
        train = work[(work["date"] >= train_start) & (work["date"] <= train_end)].copy()
        test = work[(work["date"] >= test_start) & (work["date"] <= test_end)].copy()

        if len(train) < 500 or len(test) < 50:
            continue

        model = RandomForestClassifier(
            n_estimators=300,
            max_depth=5,
            min_samples_leaf=30,
            random_state=42,
            class_weight="balanced_subsample",
        )
        model.fit(train[feature_cols], train["target"])

        test = test.copy()
        test["proba"] = model.predict_proba(test[feature_cols])[:, 1]

        for params in param_grid:
            trades = _event_returns(
                df=test,
                prob_col="proba",
                threshold=params["threshold"],
                take_profit=params["take_profit"],
                stop_loss=params["stop_loss"],
                max_hold=params["max_hold"],
                require_trend=params["require_trend"],
                max_ext20=params["max_ext20"],
            )
            stats = _summarize(trades)

            row = {"fold": fold, **params, **stats}
            summary_rows.append(row)

            if not trades.empty:
                tmp = trades.copy()
                for k, v in params.items():
                    tmp[k] = v
                tmp["fold"] = fold
                all_trades.append(tmp)

    summary = pd.DataFrame(summary_rows)
    non_empty_trades = [
        t.dropna(axis=1, how="all")
        for t in all_trades
        if not t.empty and not t.dropna(axis=1, how="all").empty
    ]
    trades = pd.concat(non_empty_trades, ignore_index=True) if non_empty_trades else pd.DataFrame()

    if not summary.empty:
        grouped = (
            summary.groupby(["threshold", "take_profit", "stop_loss", "max_hold", "require_trend", "max_ext20"], dropna=False)
            .agg(
                folds=("fold", "nunique"),
                trades=("trades", "sum"),
                mean_total_return=("total_return", "mean"),
                mean_avg_return=("avg_return", "mean"),
                mean_win_rate=("win_rate", "mean"),
                mean_profit_factor=("profit_factor", "mean"),
                worst_fold_return=("total_return", "min"),
                worst_fold_drawdown=("max_drawdown", "min"),
            )
            .reset_index()
        )
        grouped = grouped.sort_values(
            ["mean_profit_factor", "mean_avg_return", "worst_fold_return"],
            ascending=False,
        )
    else:
        grouped = pd.DataFrame()

    summary.to_csv(report_dir / "walk_forward_fold_results.csv", index=False)
    grouped.to_csv(report_dir / "walk_forward_strategy_ranking.csv", index=False)
    trades.to_csv(report_dir / "walk_forward_trades.csv", index=False)

    return summary, grouped


def main() -> None:
    _, ranking = walk_forward_optimize()
    print("== Walk-forward strategy ranking ==")
    if ranking.empty:
        print("No ranking generated.")
    else:
        print(ranking.head(25).to_string(index=False))
    print()
    print(f"Wrote {REPORT_DIR / 'walk_forward_strategy_ranking.csv'}")


if __name__ == "__main__":
    main()
