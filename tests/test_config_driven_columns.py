from pathlib import Path

import matplotlib.axes
import pandas as pd

from trading_lab.backtests.event_strategy import run_event_backtest
from trading_lab.config import TradingConfig
from trading_lab.dashboard.action_card import build_action_card
from trading_lab.decision import render_daily_decision
from trading_lab.models.dataset import supervised_frame
from trading_lab.plots.model_dashboard import plot_model_dashboard
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


def test_dashboard_labels_follow_configured_symbols(tmp_path: Path, monkeypatch):
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

    titles: list[str] = []
    original_set_title = matplotlib.axes.Axes.set_title

    def capture_title(self, label, *args, **kwargs):
        titles.append(str(label))
        return original_set_title(self, label, *args, **kwargs)

    monkeypatch.setattr(matplotlib.axes.Axes, "set_title", capture_title)
    paths = plot_tqqq_dashboard(feature_path=feature_path, out_dir=out_dir, config=config)

    assert len(paths) == 3
    assert all(path.exists() for path in paths)
    assert "SOXL price context" in titles
    assert "XLK regime and extension" in titles
    assert "SOXL pullback context" in titles


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


def test_dashboard_and_plot_labels_follow_configured_symbols(tmp_path: Path, monkeypatch):
    config = TradingConfig(traded_symbol="UPRO", benchmark_symbol="SPY")
    monkeypatch.chdir(tmp_path)
    market_dir = tmp_path / "data" / "processed" / "market"
    reports_dir = tmp_path / "data" / "reports"
    plots_dir = reports_dir / "plots"
    market_dir.mkdir(parents=True)
    reports_dir.mkdir(parents=True)

    pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=3),
            "UPRO": [40.0, 41.0, 42.0],
            "SPY": [500.0, 501.0, 502.0],
            "SPY_uptrend_20_50": [True, True, True],
            "SPY_dist_ma_20": [0.01, 0.02, 0.03],
            "SPY_dist_ma_50": [0.02, 0.03, 0.04],
            "UPRO_drawdown_from_20d_high": [-0.05, -0.04, -0.03],
        }
    ).to_csv(market_dir / "market_features.csv", index=False)
    pd.DataFrame([{"model": "demo", "probability": 0.66}]).to_csv(
        reports_dir / "selected_model_latest_signal.csv",
        index=False,
    )
    pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=3),
            "random_forest_proba": [0.51, 0.55, 0.61],
        }
    ).to_csv(reports_dir / "regime_model_predictions.csv", index=False)
    pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=3),
            "always_tqqq": [1.0, 1.1, 1.2],
            "qqq_20_50_filter": [1.0, 1.05, 1.1],
        }
    ).to_csv(reports_dir / "regime_strategy_equity_curves.csv", index=False)

    labels: list[str] = []
    titles: list[str] = []
    original_plot = matplotlib.axes.Axes.plot
    original_set_title = matplotlib.axes.Axes.set_title

    def capture_plot(self, *args, **kwargs):
        if "label" in kwargs:
            labels.append(str(kwargs["label"]))
        return original_plot(self, *args, **kwargs)

    def capture_title(self, label, *args, **kwargs):
        titles.append(str(label))
        return original_set_title(self, label, *args, **kwargs)

    monkeypatch.setattr(matplotlib.axes.Axes, "plot", capture_plot)
    monkeypatch.setattr(matplotlib.axes.Axes, "set_title", capture_title)

    card = build_action_card(config)
    plot_model_dashboard(report_dir=reports_dir, out_dir=plots_dir, config=config)

    assert "UPRO" in card.loc[card["item"].eq("max_traded_allocation"), "detail"].iloc[0]
    assert "SPY" in card.loc[card["item"].eq("benchmark_20dma_extension"), "detail"].iloc[0]
    assert "UPRO model probability history" in titles
    assert "Always UPRO" in labels
    assert "SPY 20/50 filter" in labels


def test_non_default_symbol_pair_runs_through_core_decision_model_path(tmp_path: Path):
    config = TradingConfig(traded_symbol="UPRO", benchmark_symbol="SPY", core_symbol="VOO")
    prices = [40, 42, 41, 44, 43, 46, 45, 48, 47, 50, 49, 52]
    df = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=len(prices)),
            "UPRO": prices,
            "UPRO_ret_1d": pd.Series(prices).pct_change().fillna(0.0),
            "UPRO_dist_ma_20": [0.01] * len(prices),
            "UPRO_drawdown_from_20d_high": [-0.04] * len(prices),
            "SPY": [500 + i for i in range(len(prices))],
            "SPY_ret_1d": [0.01, -0.005] * 6,
            "SPY_dist_ma_20": [0.02] * len(prices),
            "SPY_dist_ma_50": [0.03] * len(prices),
            "SPY_uptrend_20_50": [True] * len(prices),
            "VOO_ret_1d": [0.004, -0.002] * 6,
        }
    )

    frame, features, target_col = supervised_frame(df, config=config)
    result = run_event_backtest(
        df=df.assign(random_forest_proba=0.70),
        name="upro_demo",
        prob_threshold=0.65,
        require_trend=True,
        max_extension_ma20=0.05,
        min_drawdown_20d=None,
        take_profit=0.04,
        stop_loss=0.04,
        max_hold_days=3,
        cooldown_days=1,
        config=config,
    )
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "daily_decision_summary.txt").write_text(
        "\n".join(
            [
                "Date: 2026-01-12",
                "SPY: 511.00",
                "UPRO: 52.00",
                "Profile: synthetic",
                "Suggested action: WAIT_FOR_PULLBACK",
                "Max UPRO allocation: 5%",
                "Selected strategy eligible today: YES",
                "- OK: SPY trend required and current trend is true",
                "",
                "Suggested UPRO ladder:",
                "- shallow_pullback: limit $50.44, allocation 1.2%, synthetic.",
            ]
        ),
        encoding="utf-8",
    )
    (reports / "selected_model_latest_signal.csv").write_text(
        "date,model,probability\n2026-01-12,demo,0.70\n",
        encoding="utf-8",
    )
    decision = render_daily_decision(reports_dir=reports, positions=["UPRO:1"], account_value=5000)

    summary, trades = result
    assert target_col.startswith("UPRO_")
    assert all(col.startswith(("UPRO_", "SPY_", "VOO_")) for col in features)
    assert not frame.empty
    assert summary["trades"] >= 1
    assert not trades.empty
    assert "HOLD UPRO" in decision


def test_no_unapproved_hardcoded_symbols_in_generic_modules():
    roots = [
        Path("src/trading_lab/backtests"),
        Path("src/trading_lab/models"),
        Path("src/trading_lab/signals"),
        Path("src/trading_lab/strategy"),
        Path("src/trading_lab/dashboard"),
        Path("src/trading_lab/plots"),
        Path("src/trading_lab/workflows"),
    ]
    allowed_files = {
        Path("src/trading_lab/dashboard/personal_edge.py"),
        Path("src/trading_lab/signals/parse_orders.py"),
        Path("src/trading_lab/backtests/ladder.py"),
        Path("src/trading_lab/workflows/demo.py"),
    }
    allowed_line_fragments = (
        "build_tqqq_ladder",
        "max_tqqq_allocation",
        "tqqq_drawdown_20d",
        "reconcile_tqqq_orders",
        "suggest_tqqq_order_adjustments",
        "run_tqqq_ladder_backtest",
        "plot_tqqq_dashboard",
        "tqqq_price_context.png",
        "qqq_regime_context.png",
        "tqqq_drawdown_context.png",
        "always_tqqq",
        "qqq_20_50_filter",
        "qqq_uptrend",
        "qqq_dist_ma20",
        "qqq_dist_ma50",
        '"TQQQ"',
        '"QQQ"',
        '"SPY"',
        "TACTICAL_TQQQ_BUY_ALLOWED",
        "SMALL_TQQQ_ALLOWED",
        "SPY_CORE",
        "SPY_CORE_ONLY_OR_WAIT",
    )
    tokens = ("TQQQ", "QQQ", "SPY", "SQQQ", "tqqq", "qqq")
    offenders: list[str] = []
    for root in roots:
        for path in root.rglob("*.py"):
            if path in allowed_files:
                continue
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if any(fragment in line for fragment in allowed_line_fragments):
                    continue
                if any(token in line for token in tokens):
                    offenders.append(f"{path}:{line_number}:{line.strip()}")

    assert offenders == []
