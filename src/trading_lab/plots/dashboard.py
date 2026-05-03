from __future__ import annotations


def _finite_frame(df):
    return df.replace([float("inf"), float("-inf")], float("nan"))

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


FEATURE_PATH = Path("data/processed/market/market_features.csv")
PRED_PATH = Path("data/reports/latest_regime_signal.csv")
OUT_DIR = Path("data/reports/plots")


def plot_tqqq_dashboard(
    feature_path: Path = FEATURE_PATH,
    pred_path: Path = PRED_PATH,
    out_dir: Path = OUT_DIR,
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(feature_path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values("date").tail(260).copy()

    paths: list[Path] = []

    price_path = out_dir / "tqqq_price_context.png"
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df["date"], df["TQQQ"], label="TQQQ")
    if "TQQQ_ma_20" in df.columns:
        ax.plot(df["date"], df["TQQQ_ma_20"], label="20DMA")
    if "TQQQ_ma_50" in df.columns:
        ax.plot(df["date"], df["TQQQ_ma_50"], label="50DMA")
    ax.set_title("TQQQ price context")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(price_path, dpi=160)
    plt.close(fig)
    paths.append(price_path)

    regime_path = out_dir / "qqq_regime_context.png"
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df["date"], df["QQQ_dist_ma_20"] * 100, label="QQQ % from 20DMA")
    ax.plot(df["date"], df["QQQ_dist_ma_50"] * 100, label="QQQ % from 50DMA")
    ax.axhline(6.0, linestyle="--", label="6% extension cap")
    ax.axhline(0.0, linestyle=":")
    ax.set_title("QQQ regime and extension")
    ax.set_xlabel("Date")
    ax.set_ylabel("Percent")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(regime_path, dpi=160)
    plt.close(fig)
    paths.append(regime_path)

    drawdown_path = out_dir / "tqqq_drawdown_context.png"
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df["date"], df["TQQQ_drawdown_from_20d_high"] * 100, label="20d high drawdown")
    ax.plot(df["date"], df["TQQQ_drawdown_from_60d_high"] * 100, label="60d high drawdown")
    ax.axhline(-3.0, linestyle="--", label="-3% pullback")
    ax.axhline(0.0, linestyle=":")
    ax.set_title("TQQQ pullback context")
    ax.set_xlabel("Date")
    ax.set_ylabel("Percent")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(drawdown_path, dpi=160)
    plt.close(fig)
    paths.append(drawdown_path)

    return paths


def main() -> None:
    paths = plot_tqqq_dashboard()
    print("== Dashboard plots ==")
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
