from trading_lab.config import TradingColumns, TradingConfig


def test_trading_columns_default_names_match_current_files():
    cols = TradingColumns(TradingConfig())

    assert cols.traded_price == "TQQQ"
    assert cols.benchmark_price == "QQQ"
    assert cols.benchmark_uptrend == "QQQ_uptrend_20_50"
    assert cols.benchmark_dist_ma_20 == "QQQ_dist_ma_20"
    assert cols.benchmark_dist_ma_50 == "QQQ_dist_ma_50"
    assert cols.traded_drawdown_20d == "TQQQ_drawdown_from_20d_high"
    assert cols.traded_target(5) == "TQQQ_hit_up_before_down_5d"


def test_trading_columns_support_other_symbol_pairs():
    cfg = TradingConfig(
        traded_symbol="SOXL",
        benchmark_symbol="SOXX",
        core_symbol="SPY",
        inverse_symbol="SOXS",
    )
    cols = TradingColumns(cfg)

    assert cols.traded_price == "SOXL"
    assert cols.benchmark_price == "SOXX"
    assert cols.benchmark_uptrend == "SOXX_uptrend_20_50"
    assert cols.traded_target(10) == "SOXL_hit_up_before_down_10d"
