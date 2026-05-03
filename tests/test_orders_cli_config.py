from pathlib import Path


def test_order_reconciler_uses_trading_columns():
    source = Path("src/trading_lab/signals/orders.py").read_text(encoding="utf-8")

    assert "TradingColumns" in source
    assert "cols.traded_price" in source
    assert "cols.benchmark_uptrend" in source
    assert 'f"{trading_cfg.benchmark_upper}_uptrend_20_50"' not in source
