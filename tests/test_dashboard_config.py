from pathlib import Path


def test_daily_dashboard_uses_trading_columns_for_core_market_fields():
    source = Path("src/trading_lab/dashboard/daily.py").read_text(encoding="utf-8")

    assert "TradingColumns" in source
    assert "cols = TradingColumns(cfg)" in source
    assert "cols.traded_price" in source
    assert "cols.benchmark_price" in source
    assert "cols.benchmark_uptrend" in source
    assert 'pred["TQQQ"]' not in source
    assert 'pred["QQQ"]' not in source
    assert 'pred["QQQ_uptrend_20_50"]' not in source
