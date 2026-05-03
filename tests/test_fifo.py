import pandas as pd
import pytest

from trading_lab.fifo import calculate_fifo_realized_pnl


def test_fifo_realized_pnl_partial_lots():
    trades = pd.DataFrame(
        [
            {"executed_at": pd.Timestamp("2024-01-01"), "symbol": "TQQQ", "side": "buy", "quantity": 10, "price": 10.0, "fees": 0.0},
            {"executed_at": pd.Timestamp("2024-01-02"), "symbol": "TQQQ", "side": "buy", "quantity": 10, "price": 12.0, "fees": 0.0},
            {"executed_at": pd.Timestamp("2024-01-03"), "symbol": "TQQQ", "side": "sell", "quantity": 15, "price": 15.0, "fees": 0.0},
        ]
    )

    realized = calculate_fifo_realized_pnl(trades)

    assert realized["quantity"].tolist() == [10, 5]
    assert realized["realized_pnl"].tolist() == [50.0, 15.0]
    assert realized["realized_pnl"].sum() == 65.0


def test_fifo_rejects_oversell():
    trades = pd.DataFrame(
        [
            {"executed_at": pd.Timestamp("2024-01-01"), "symbol": "SPY", "side": "buy", "quantity": 1, "price": 400.0, "fees": 0.0},
            {"executed_at": pd.Timestamp("2024-01-02"), "symbol": "SPY", "side": "sell", "quantity": 2, "price": 410.0, "fees": 0.0},
        ]
    )

    with pytest.raises(ValueError, match="Sell quantity exceeds"):
        calculate_fifo_realized_pnl(trades)
