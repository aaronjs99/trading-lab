from trading_lab.dashboard.daily import build_daily_decision_summary
from trading_lab.data.market import csv_has_today_data


def test_dashboard_summary_function_imports():
    assert callable(build_daily_decision_summary)


def test_market_freshness_function_imports():
    assert callable(csv_has_today_data)
