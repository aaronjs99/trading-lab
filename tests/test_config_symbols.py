from trading_lab.config import TradingColumns, TradingConfig
from trading_lab.config.symbols import SymbolPair
from trading_lab.config.targets import PredictionTarget, default_prediction_targets


def test_symbol_helpers_generate_default_and_configured_column_names():
    default_pair = SymbolPair(traded="TQQQ", benchmark="QQQ")

    assert default_pair.price_col(default_pair.traded) == "TQQQ"
    assert default_pair.distance_to_ma_col(default_pair.benchmark, 20) == "QQQ_dist_ma_20"
    assert default_pair.drawdown_col(default_pair.traded, 20) == "TQQQ_drawdown_from_20d_high"
    assert default_pair.hit_up_before_down_col(default_pair.traded, 5) == "TQQQ_hit_up_before_down_5d"
    assert default_pair.uptrend_col(default_pair.benchmark) == "QQQ_uptrend_20_50"

    cfg = TradingConfig(traded_symbol="SOXL", benchmark_symbol="SOXX")
    cols = TradingColumns(cfg)
    targets = default_prediction_targets(cfg)

    assert cols.traded_price == "SOXL"
    assert cols.benchmark_uptrend == "SOXX_uptrend_20_50"
    assert cols.traded_target(10) == "SOXL_hit_up_before_down_10d"
    assert [target.symbol for target in targets] == ["SOXL", "SOXL"]
    assert targets[0].name.startswith("soxl_")


def test_prediction_target_description_is_symbol_generic():
    target = PredictionTarget(
        name="soxl_5d",
        symbol="SOXL",
        horizon_days=5,
        up_threshold=0.05,
        down_threshold=-0.05,
    )

    assert "SOXL hits +5%" in target.description
    assert "within 5 trading days" in target.description
