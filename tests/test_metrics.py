import pandas as pd
import pytest

from trading_lab.backtest import LadderConfig, run_tqqq_ladder_backtest
from trading_lab.metrics import equity_curve_metrics, summarize_realized_by_symbol


def test_summary_metrics_by_symbol():
    realized = pd.DataFrame(
        [
            {"symbol": "AAPL", "quantity": 1, "realized_pnl": 10.0},
            {"symbol": "AAPL", "quantity": 1, "realized_pnl": -5.0},
            {"symbol": "SPY", "quantity": 2, "realized_pnl": 8.0},
        ]
    )

    summary = summarize_realized_by_symbol(realized)
    aapl = summary.loc[summary["symbol"] == "AAPL"].iloc[0]

    assert aapl["trades"] == 2
    assert aapl["realized_pnl"] == 5.0
    assert aapl["win_rate"] == 0.5
    assert aapl["profit_factor"] == 2.0


def test_equity_curve_metrics_basic():
    metrics = equity_curve_metrics(pd.Series([100.0, 110.0, 105.0, 120.0]))

    assert metrics["total_return"] == pytest.approx(0.2)
    assert metrics["max_drawdown"] < 0
    assert "sharpe" in metrics


def test_tqqq_ladder_backtest_runs():
    market_data = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "symbol": ["TQQQ", "TQQQ", "TQQQ"],
            "close": [100.0, 90.0, 95.0],
        }
    )

    results, metrics = run_tqqq_ladder_backtest(market_data, LadderConfig(initial_cash=1000.0))

    assert len(results) == 3
    assert results["equity"].iloc[0] == pytest.approx(1000.0)
    assert set(metrics) == {"total_return", "max_drawdown", "sharpe"}
