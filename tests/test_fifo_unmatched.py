import pandas as pd

from trading_lab.fifo import calculate_fifo_realized_pnl


def test_fifo_allows_starting_lot_side():
    trades = pd.DataFrame(
        [
            {
                "executed_at": "2026-01-01",
                "symbol": "CPRX",
                "side": "starting_lot",
                "quantity": 1,
                "price": 0,
                "amount": 0,
                "fees": 0,
                "source_file": "x.csv",
            },
            {
                "executed_at": "2026-01-02",
                "symbol": "CPRX",
                "side": "sell",
                "quantity": 1,
                "price": 10,
                "amount": 10,
                "fees": 0,
                "source_file": "x.csv",
            },
        ]
    )

    out = calculate_fifo_realized_pnl(trades, allow_unmatched_sells=True)

    assert len(out) == 1
    assert out.loc[0, "basis_status"] == "unknown"
    assert out.loc[0, "proceeds"] == 10


def test_fifo_flags_unmatched_sells_without_crashing():
    trades = pd.DataFrame(
        [
            {
                "executed_at": "2026-01-02",
                "symbol": "CPRX",
                "side": "sell",
                "quantity": 1,
                "price": 10,
                "amount": 10,
                "fees": 0,
                "source_file": "x.csv",
            },
        ]
    )

    out = calculate_fifo_realized_pnl(trades, allow_unmatched_sells=True)

    assert len(out) == 1
    assert out.loc[0, "basis_status"] == "unknown_unmatched_sell"
    assert out.loc[0, "realized_pnl"] == 0.0
