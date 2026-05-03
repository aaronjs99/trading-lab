import pandas as pd

from trading_lab.signals.ladder import build_tqqq_ladder
from trading_lab.signals.orders import reconcile_tqqq_orders


def test_reconcile_flags_oversized_pending_orders():
    orders = pd.DataFrame(
        [
            {"symbol": "TQQQ", "side": "buy", "quantity": 10, "limit_price": 60.5},
            {"symbol": "TQQQ", "side": "buy", "quantity": 10, "limit_price": 58.0},
        ]
    )
    ladder = build_tqqq_ladder(65.30, 0.05, "WAIT_FOR_PULLBACK")

    checks = reconcile_tqqq_orders(
        open_orders=orders,
        ladder=ladder,
        account_value=5000,
        current_price=65.30,
    )

    assert any(c.status == "TOO_AGGRESSIVE" for c in checks)


def test_reconcile_ok_when_orders_fit_allocation():
    orders = pd.DataFrame(
        [
            {"symbol": "TQQQ", "side": "buy", "quantity": 1, "limit_price": 63.34},
        ]
    )
    ladder = build_tqqq_ladder(65.30, 0.05, "WAIT_FOR_PULLBACK")

    checks = reconcile_tqqq_orders(
        open_orders=orders,
        ladder=ladder,
        account_value=5000,
        current_price=65.30,
    )

    assert any(c.status == "OK_SIZE" for c in checks)
