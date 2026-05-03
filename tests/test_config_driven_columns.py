from pathlib import Path

import pandas as pd

from trading_lab.backtests.event_strategy import run_event_backtest
from trading_lab.config import TradingConfig
from trading_lab.plots.dashboard import plot_tqqq_dashboard
from trading_lab.signals.ladder import LadderOrder
from trading_lab.signals.orders import reconcile_tqqq_orders, suggest_tqqq_order_adjustments


def test_event_backtest_uses_configured_price_and_regime_columns():
    config = TradingConfig(traded_symbol="SOXL", benchmark_symbol="XLK")
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=7),
            "SOXL": [100, 106, 107, 108, 109, 110, 111],
            "random_forest_proba": [0.7] * 7,
            "XLK_uptrend_20_50": [True] * 7,
            "XLK_dist_ma_20": [0.01] * 7,
            "SOXL_drawdown_from_20d_high": [-0.02] * 7,
        }
    )

    result = run_event_backtest(
        df=df,
        name="test",
        prob_threshold=0.65,
        require_trend=True,
        max_extension_ma20=0.04,
        min_drawdown_20d=None,
        take_profit=0.05,
        stop_loss=0.05,
        max_hold_days=5,
        cooldown_days=2,
        config=config,
    )

    summary, trades = result
    assert summary["trades"] == 1
    assert trades.iloc[0]["exit_reason"] == "take_profit"


def test_dashboard_labels_follow_configured_symbols(tmp_path: Path):
    config = TradingConfig(traded_symbol="SOXL", benchmark_symbol="XLK")
    feature_path = tmp_path / "features.csv"
    out_dir = tmp_path / "plots"
    pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=3),
            "SOXL": [10, 11, 12],
            "SOXL_ma_20": [9, 10, 11],
            "SOXL_ma_50": [8, 9, 10],
            "XLK_dist_ma_20": [0.01, 0.02, 0.03],
            "XLK_dist_ma_50": [0.00, 0.01, 0.02],
            "SOXL_drawdown_from_20d_high": [0.0, -0.01, -0.02],
            "SOXL_drawdown_from_60d_high": [0.0, -0.02, -0.03],
        }
    ).to_csv(feature_path, index=False)

    paths = plot_tqqq_dashboard(feature_path=feature_path, out_dir=out_dir, config=config)

    assert len(paths) == 3
    assert all(path.exists() for path in paths)


def test_order_reconciliation_uses_configured_traded_symbol():
    config = TradingConfig(traded_symbol="SOXL", benchmark_symbol="XLK")
    open_orders = pd.DataFrame(
        {"symbol": ["SOXL"], "side": ["buy"], "quantity": [1], "limit_price": [10.0]}
    )
    ladder = [LadderOrder(level="L1", limit_price=10.0, allocation_fraction=0.10, reason="test")]

    checks = reconcile_tqqq_orders(open_orders, ladder, 1000.0, 12.0, config=config)
    adjustments = suggest_tqqq_order_adjustments(open_orders, ladder, 1000.0, config=config)

    assert "SOXL" in checks[0].message
    assert adjustments.iloc[0]["symbol"] == "SOXL"
