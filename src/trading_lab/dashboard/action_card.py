from __future__ import annotations

from pathlib import Path

import pandas as pd

from trading_lab.config import TradingColumns, load_trading_config
from trading_lab.signals.allocation import recommend_allocation
from trading_lab.signals.ladder import build_tqqq_ladder


OUT_MD = Path("data/reports/action_card.md")
OUT_CSV = Path("data/reports/action_card.csv")


def build_action_card() -> pd.DataFrame:
    cfg = load_trading_config()
    cols = TradingColumns(cfg)

    features = pd.read_csv("data/processed/market/market_features.csv")
    selected = pd.read_csv("data/reports/selected_model_latest_signal.csv").iloc[-1]

    latest = features.dropna(
        subset=[
            cols.traded_price,
            cols.benchmark_price,
            cols.benchmark_uptrend,
            cols.benchmark_dist_ma_20,
            cols.benchmark_dist_ma_50,
            cols.traded_drawdown_20d,
        ]
    ).iloc[-1]

    probability = float(selected["probability"])
    traded_price = float(latest[cols.traded_price])
    benchmark_ext20 = float(latest[cols.benchmark_dist_ma_20])

    allocation = recommend_allocation(
        rf_probability=probability,
        qqq_uptrend=bool(latest[cols.benchmark_uptrend]),
        qqq_dist_ma20=benchmark_ext20,
        qqq_dist_ma50=float(latest[cols.benchmark_dist_ma_50]),
        tqqq_drawdown_20d=float(latest[cols.traded_drawdown_20d]),
    )

    ladder = build_tqqq_ladder(
        current_price=traded_price,
        max_tqqq_allocation=allocation.max_tqqq_allocation,
        action=allocation.action,
    )

    rows = [
        {
            "section": "decision",
            "item": "action",
            "value": allocation.action,
            "detail": allocation.reason,
        },
        {
            "section": "decision",
            "item": "selected_model_probability",
            "value": f"{probability:.3f}",
            "detail": str(selected["model"]),
        },
        {
            "section": "risk",
            "item": "max_traded_allocation",
            "value": f"{allocation.max_tqqq_allocation:.1%}",
            "detail": cfg.traded_symbol,
        },
        {
            "section": "risk",
            "item": "benchmark_20dma_extension",
            "value": f"{benchmark_ext20:.2%}",
            "detail": cfg.benchmark_symbol,
        },
    ]

    for order in ladder:
        rows.append(
            {
                "section": "ladder",
                "item": order.level,
                "value": f"{order.allocation_fraction:.1%} @ ${order.limit_price:.2f}",
                "detail": order.reason,
            }
        )

    return pd.DataFrame(rows)


def write_action_card() -> pd.DataFrame:
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    card = build_action_card()
    card.to_csv(OUT_CSV, index=False)

    lines = ["# Daily Action Card", ""]
    for _, row in card.iterrows():
        lines.append(f"- **{row['section']} / {row['item']}**: {row['value']} — {row['detail']}")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return card


def main() -> None:
    card = write_action_card()
    print("== Daily action card ==")
    print(card.to_string(index=False))
    print()
    print("Wrote:")
    print(OUT_MD)
    print(OUT_CSV)


if __name__ == "__main__":
    main()
