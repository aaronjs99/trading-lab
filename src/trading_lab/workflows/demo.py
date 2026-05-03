from __future__ import annotations

import tempfile
import os
from pathlib import Path

import pandas as pd

from trading_lab.config import TradingConfig, TradingColumns
from trading_lab.dashboard.action_card import build_action_card
from trading_lab.decision import render_daily_decision
from trading_lab.features.market import build_market_features


DEMO_ROOT = Path("examples/demo_data")


def _write_demo_config(root: Path) -> TradingConfig:
    cfg_dir = root / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "trading.yaml").write_text(
        "\n".join(
            [
                "symbols:",
                "  traded: SOXL",
                "  benchmark: XLK",
                "  core: SPY",
                "  inverse: SQQQ",
                "",
                "account:",
                "  value: 5000.0",
                "",
                "allocation:",
                "  max_traded_allocation_wait: 0.05",
                "  max_core_allocation_wait: 0.50",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return TradingConfig(traded_symbol="SOXL", benchmark_symbol="XLK", core_symbol="SPY", inverse_symbol="SQQQ")


def _write_selected_signal(reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "date": "2026-03-20",
                "model": "demo_synthetic_model",
                "probability": 0.61,
                "active_target_mode": "barrier_first_hit",
                "active_target_col": "SOXL_5d_up5%_before_down5%",
                "target_source": "demo_fixture",
            }
        ]
    ).to_csv(reports_dir / "selected_model_latest_signal.csv", index=False)


def _write_decision_summary(root: Path, cfg: TradingConfig, card: pd.DataFrame) -> None:
    reports_dir = root / "data" / "reports"
    features = pd.read_csv(root / "data" / "processed" / "market" / "market_features.csv")
    cols = TradingColumns(cfg)
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
    action = str(card.loc[card["item"].eq("action"), "value"].iloc[0])
    reason = str(card.loc[card["item"].eq("action"), "detail"].iloc[0])
    max_alloc = str(card.loc[card["item"].eq("max_traded_allocation"), "value"].iloc[0])
    ladder = card[card["section"].eq("ladder")]

    lines = [
        f"Date: {latest['date']}",
        f"{cfg.benchmark_symbol}: {float(latest[cols.benchmark_price]):.2f}",
        f"{cfg.traded_symbol}: {float(latest[cols.traded_price]):.2f}",
        "Profile: demo",
        "Active target mode: barrier_first_hit",
        "Active target column: SOXL_5d_up5%_before_down5%",
        "Target source: demo_fixture",
        f"{cfg.benchmark_symbol} uptrend 20/50: {bool(latest[cols.benchmark_uptrend])}",
        f"{cfg.benchmark_symbol} distance from 20DMA: {float(latest[cols.benchmark_dist_ma_20]):.2%}",
        f"{cfg.traded_symbol} drawdown from 20d high: {float(latest[cols.traded_drawdown_20d]):.2%}",
        f"Suggested action: {action}",
        f"Max {cfg.traded_symbol} allocation: {max_alloc}",
        "Selected strategy eligible today: YES",
        f"- OK: {cfg.benchmark_symbol} trend required and current trend is true",
        f"Reason: {reason}",
        "",
        f"Suggested {cfg.traded_symbol} ladder:",
    ]
    if ladder.empty:
        lines.append("- No buy ladder suggested.")
    else:
        for _, row in ladder.iterrows():
            lines.append(f"- {row['item']}: {row['value']}, {row['detail']}")

    (reports_dir / "daily_decision_summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_demo() -> Path:
    fixture_market = DEMO_ROOT / "market"
    if not fixture_market.exists():
        raise FileNotFoundError(f"Missing demo fixtures: {fixture_market}")

    out_root = Path(tempfile.mkdtemp(prefix="trading_lab_demo_"))
    cfg = _write_demo_config(out_root)
    market_out = out_root / "data" / "raw" / "market"
    market_out.mkdir(parents=True, exist_ok=True)
    for fixture in fixture_market.glob("*.csv"):
        (market_out / fixture.name).write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    old_cwd = Path.cwd()
    try:
        os.chdir(out_root)
        build_market_features(
            market_dir=Path("data/raw/market"),
            output_path=Path("data/processed/market/market_features.csv"),
        )
        _write_selected_signal(Path("data/reports"))
        card = build_action_card(cfg)
        card.to_csv(Path("data/reports/action_card.csv"), index=False)
        _write_decision_summary(Path("."), cfg, card)
        decision = render_daily_decision(
            reports_dir=Path("data/reports"),
            profile="demo",
            account_value=5000,
            cash=1000,
        )
    finally:
        os.chdir(old_cwd)

    print("== trading-lab demo ==")
    print(f"Demo output: {out_root}")
    print()
    print(card.to_string(index=False))
    print()
    print(decision)
    return out_root


def main() -> None:
    run_demo()


if __name__ == "__main__":
    main()
