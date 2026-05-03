import pandas as pd

from trading_lab.reports.buckets import bucket_symbol, build_bucket_reports


def test_bucket_symbol_classification():
    assert bucket_symbol("SPY") == "core_index_long"
    assert bucket_symbol("TQQQ") == "core_index_long"
    assert bucket_symbol("SQQQ") == "inverse_bearish"
    assert bucket_symbol("TSLA") == "mega_cap_single_name"
    assert bucket_symbol("GLD") == "commodity_macro"
    assert bucket_symbol("XYZ") == "random_single_name"


def test_build_bucket_reports_summarizes_profit_factor():
    realized = pd.DataFrame(
        [
            {"symbol": "SPY", "realized_pnl": 10.0},
            {"symbol": "SPY", "realized_pnl": -2.0},
            {"symbol": "TSLA", "realized_pnl": -5.0},
        ]
    )

    buckets, symbols = build_bucket_reports(realized)

    core = buckets[buckets["bucket"].eq("core_index_long")].iloc[0]
    assert core["realized_pnl"] == 8.0
    assert core["profit_factor"] == 5.0

    spy = symbols[symbols["symbol"].eq("SPY")].iloc[0]
    assert spy["rows"] == 2
