from trading_lab.signals.parse_orders import parse_robinhood_upcoming_activity


def test_parse_robinhood_upcoming_activity_tqqq_orders():
    text = """
ProShares UltraPro QQQ limit buy
Apr 29, 2026
Placed
Symbol
TQQQ
Type
Limit buy
Limit price
$60.50
Entered quantity
10
Cancel Order

ProShares UltraPro QQQ limit sell
Apr 29, 2026
Placed
Symbol
TQQQ
Type
Limit sell
Limit price
$68.50
Entered quantity
4
Cancel Order
"""

    df = parse_robinhood_upcoming_activity(text)

    assert len(df) == 2
    assert list(df["side"]) == ["buy", "sell"]
    assert list(df["limit_price"]) == [60.50, 68.50]
    assert list(df["quantity"]) == [10.0, 4.0]
