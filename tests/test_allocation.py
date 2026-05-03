from trading_lab.signals.allocation import recommend_allocation


def test_wait_for_pullback_when_uptrend_is_extended():
    signal = recommend_allocation(
        rf_probability=0.49,
        qqq_uptrend=True,
        qqq_dist_ma20=0.056,
        qqq_dist_ma50=0.101,
        tqqq_drawdown_20d=0.0,
    )

    assert signal.action == "WAIT_FOR_PULLBACK"
    assert signal.max_tqqq_allocation == 0.05


def test_tactical_buy_allowed_on_strong_pullback_signal():
    signal = recommend_allocation(
        rf_probability=0.70,
        qqq_uptrend=True,
        qqq_dist_ma20=0.01,
        qqq_dist_ma50=0.03,
        tqqq_drawdown_20d=-0.08,
    )

    assert signal.action == "TACTICAL_TQQQ_BUY_ALLOWED"
    assert signal.max_tqqq_allocation == 0.30


def test_defensive_when_not_uptrend():
    signal = recommend_allocation(
        rf_probability=0.70,
        qqq_uptrend=False,
        qqq_dist_ma20=-0.02,
        qqq_dist_ma50=-0.04,
        tqqq_drawdown_20d=-0.10,
    )

    assert signal.action == "DEFENSIVE_OR_CASH"
    assert signal.max_tqqq_allocation == 0.0
