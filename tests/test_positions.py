import pandas as pd

from trading_lab.ingestion import normalize_robinhood_frame
from trading_lab.positions import reconstruct_positions


def test_position_reconstruction_sums_signed_quantity():
    trades = pd.DataFrame(
        [
            {"executed_at": pd.Timestamp("2024-01-01"), "symbol": "SPY", "side": "buy", "quantity": 3, "price": 400.0},
            {"executed_at": pd.Timestamp("2024-01-02"), "symbol": "SPY", "side": "sell", "quantity": 1, "price": 410.0},
            {"executed_at": pd.Timestamp("2024-01-03"), "symbol": "TQQQ", "side": "buy", "quantity": 5, "price": 50.0},
        ]
    )

    positions = reconstruct_positions(trades)

    spy = positions.loc[positions["symbol"] == "SPY"].iloc[0]
    assert spy["quantity"] == 2
    assert spy["buy_quantity"] == 3
    assert spy["sell_quantity"] == 1


def test_robinhood_normalizer_accepts_common_column_names():
    raw = pd.DataFrame(
        {
            "Trade Date": ["2024-01-01"],
            "Ticker": ["tqqq"],
            "Transaction Type": ["Buy"],
            "Shares": ["2"],
            "Price Per Share": ["$50.00"],
            "Regulatory Fees": ["0.01"],
        }
    )

    normalized = normalize_robinhood_frame(raw, source_file="sample.csv")

    assert normalized.loc[0, "symbol"] == "TQQQ"
    assert normalized.loc[0, "side"] == "buy"
    assert normalized.loc[0, "quantity"] == 2
    assert normalized.loc[0, "price"] == 50.0
    assert normalized.loc[0, "source_file"] == "sample.csv"
