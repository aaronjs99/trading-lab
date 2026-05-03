from __future__ import annotations


def _finite_frame(df: pd.DataFrame) -> pd.DataFrame:
    return df.replace([np.inf, -np.inf], np.nan)

def _capped_profit_factor(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    finite = values.replace([np.inf, -np.inf], np.nan)
    cap = finite.dropna().quantile(0.95)
    if pd.isna(cap) or cap <= 0:
        cap = 10.0
    return values.replace([np.inf, -np.inf], cap).fillna(0.0)

from pathlib import Path

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from trading_lab.config import TradingConfig, load_trading_config

REPORT_DIR = Path("data/reports")
OUT_DIR = Path("data/reports/plots")


def plot_model_dashboard(
    report_dir: Path = REPORT_DIR,
    out_dir: Path = OUT_DIR,
    config: TradingConfig | None = None,
) -> list[Path]:
    cfg = config or load_trading_config()
    traded = cfg.traded_symbol.upper()
    benchmark = cfg.benchmark_symbol.upper()
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    pred_path = report_dir / "regime_model_predictions.csv"
    if pred_path.exists():
        preds = pd.read_csv(pred_path)
        preds["date"] = pd.to_datetime(preds["date"], errors="coerce")
        preds = preds.sort_values("date").tail(500)

        out = out_dir / "model_probability_history.png"
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(preds["date"], preds["random_forest_proba"], label="RF probability")
        ax.axhline(0.50, linestyle="--", label="0.50 selected threshold")
        ax.axhline(0.60, linestyle=":", label="0.60 stronger signal")
        ax.set_title(f"{traded} model probability history")
        ax.set_xlabel("Date")
        ax.set_ylabel("Probability")
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(out, dpi=160)
        plt.close(fig)
        paths.append(out)

    equity_path = report_dir / "regime_strategy_equity_curves.csv"
    if equity_path.exists():
        curves = pd.read_csv(equity_path)
        curves["date"] = pd.to_datetime(curves["date"], errors="coerce")
        curves = curves.sort_values("date")

        out = out_dir / "strategy_equity_curves.png"
        fig, ax = plt.subplots(figsize=(12, 6))
        labels = {
            "always_tqqq": f"Always {traded}",
            "qqq_20_50_filter": f"{benchmark} 20/50 filter",
            "rf_prob_ge_0.60": "RF probability >= 0.60",
            "rf_prob_ge_0.55": "RF probability >= 0.55",
        }
        for col in ["always_tqqq", "qqq_20_50_filter", "rf_prob_ge_0.60", "rf_prob_ge_0.55"]:
            if col in curves.columns:
                ax.plot(curves["date"], curves[col], label=labels[col])
        ax.set_title("Strategy equity curves")
        ax.set_xlabel("Date")
        ax.set_ylabel("Equity multiple")
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(out, dpi=160)
        plt.close(fig)
        paths.append(out)

    ranking_path = report_dir / "walk_forward_strategy_ranking.csv"
    if ranking_path.exists():
        ranking = pd.read_csv(ranking_path).head(15).copy()
        ranking["strategy"] = (
            "p>=" + ranking["threshold"].map(lambda x: f"{x:.2f}")
            + " tp" + ranking["take_profit"].map(lambda x: f"{x:.0%}")
            + " sl" + ranking["stop_loss"].map(lambda x: f"{x:.0%}")
            + " h" + ranking["max_hold"].astype(str)
        )

        out = out_dir / "walk_forward_top_strategies.png"
        fig, ax = plt.subplots(figsize=(12, 7))
        ax.barh(ranking["strategy"], _capped_profit_factor(ranking["mean_profit_factor"]))
        ax.set_title("Top walk-forward strategies by profit factor")
        ax.set_xlabel("Mean profit factor")
        ax.set_ylabel("Strategy")
        ax.invert_yaxis()
        ax.grid(True, axis="x", alpha=0.3)
        fig.tight_layout()
        fig.savefig(out, dpi=160)
        plt.close(fig)
        paths.append(out)

    return paths


def main() -> None:
    paths = plot_model_dashboard()
    print("== Model dashboard plots ==")
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
