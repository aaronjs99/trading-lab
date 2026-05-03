from trading_lab.strategy.eligibility import check_strategy_eligibility
from trading_lab.strategy.select import StrategySelection


def _selection() -> StrategySelection:
    return StrategySelection(
        threshold=0.50,
        take_profit=0.05,
        stop_loss=0.05,
        max_hold=3,
        require_trend=True,
        max_ext20=0.06,
        trades=118,
        mean_total_return=0.44,
        mean_avg_return=0.015,
        mean_win_rate=0.68,
        mean_profit_factor=2.48,
        worst_fold_return=-0.43,
        worst_fold_drawdown=-0.55,
    )


def test_strategy_eligible_when_all_conditions_pass():
    result = check_strategy_eligibility(
        selection=_selection(),
        rf_probability=0.55,
        qqq_uptrend=True,
        qqq_dist_ma20=0.04,
    )

    assert result.eligible


def test_strategy_ineligible_when_probability_low():
    result = check_strategy_eligibility(
        selection=_selection(),
        rf_probability=0.38,
        qqq_uptrend=True,
        qqq_dist_ma20=0.04,
    )

    assert not result.eligible
    assert any("RF probability" in reason for reason in result.reasons)
