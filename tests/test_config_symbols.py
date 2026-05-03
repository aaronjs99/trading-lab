from trading_lab.config.symbols import SymbolPair


def test_symbol_pair_generates_current_column_names():
    pair = SymbolPair(traded="TQQQ", benchmark="QQQ")

    assert pair.price_col(pair.traded) == "TQQQ"
    assert pair.distance_to_ma_col(pair.benchmark, 20) == "QQQ_dist_ma_20"
    assert pair.drawdown_col(pair.traded, 20) == "TQQQ_drawdown_from_20d_high"
    assert pair.hit_up_before_down_col(pair.traded, 5) == "TQQQ_hit_up_before_down_5d"
    assert pair.uptrend_col(pair.benchmark) == "QQQ_uptrend_20_50"


def test_symbol_pair_is_not_tqqq_specific():
    pair = SymbolPair(traded="SOXL", benchmark="SOXX")

    assert pair.price_col(pair.traded) == "SOXL"
    assert pair.distance_to_ma_col(pair.benchmark, 50) == "SOXX_dist_ma_50"
    assert pair.drawdown_col(pair.traded, 60) == "SOXL_drawdown_from_60d_high"
    assert pair.hit_up_before_down_col(pair.traded, 10) == "SOXL_hit_up_before_down_10d"
