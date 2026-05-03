import pandas as pd

from trading_lab.signals.ladder import build_tqqq_ladder
from trading_lab.signals.orders import suggest_tqqq_order_adjustments


def test_suggest_order_adjustments_reduces_oversized_buy():
    orders = pd.DataFrame(
        [
            {"symbol": "TQQQ", "side": "buy", "quantity": 10, "limit_price": 60.50},
            {"symbol": "TQQQ", "side": "sell", "quantity": 4, "limit_price": 68.50},
        ]
    )
    ladder = build_tqqq_ladder(65.30, 0.05, "WAIT_FOR_PULLBACK")

    out = suggest_tqqq_order_adjustments(orders, ladder, account_value=5000)

    buy = out[out["side"] == "buy"].iloc[0]
    sell = out[out["side"] == "sell"].iloc[0]

    assert buy["recommendation"] in {"REDUCE_BUY", "CANCEL_BUY"}
    assert buy["suggested_notional"] <= 250.0
    assert sell["recommendation"] == "KEEP_SELL_ORDER"
