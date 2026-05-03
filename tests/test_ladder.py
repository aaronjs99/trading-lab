from trading_lab.signals.ladder import build_tqqq_ladder


def test_wait_for_pullback_ladder_starts_below_current_price():
    ladder = build_tqqq_ladder(
        current_price=65.30,
        max_tqqq_allocation=0.05,
        action="WAIT_FOR_PULLBACK",
    )

    assert len(ladder) == 3
    assert ladder[0].limit_price < 65.30
    assert sum(o.allocation_fraction for o in ladder) == 0.05


def test_defensive_ladder_is_empty():
    ladder = build_tqqq_ladder(
        current_price=65.30,
        max_tqqq_allocation=0.0,
        action="DEFENSIVE_OR_CASH",
    )

    assert ladder == []
