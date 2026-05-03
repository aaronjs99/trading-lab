import pandas as pd

from trading_lab.strategy.select import select_strategy


def test_select_strategy_applies_risk_filters():
    ranking = pd.DataFrame(
        [
            {
                "threshold": 0.50,
                "take_profit": 0.04,
                "stop_loss": 0.06,
                "max_hold": 3,
                "require_trend": True,
                "max_ext20": None,
                "trades": 120,
                "mean_total_return": 0.50,
                "mean_avg_return": 0.015,
                "mean_win_rate": 0.68,
                "mean_profit_factor": 2.8,
                "worst_fold_return": -0.60,
                "worst_fold_drawdown": -0.65,
            },
            {
                "threshold": 0.50,
                "take_profit": 0.05,
                "stop_loss": 0.04,
                "max_hold": 3,
                "require_trend": True,
                "max_ext20": 0.06,
                "trades": 120,
                "mean_total_return": 0.49,
                "mean_avg_return": 0.016,
                "mean_win_rate": 0.69,
                "mean_profit_factor": 2.4,
                "worst_fold_return": -0.35,
                "worst_fold_drawdown": -0.43,
            },
        ]
    )

    selected = select_strategy(ranking)

    assert selected.take_profit == 0.05
    assert selected.stop_loss == 0.04
    assert selected.worst_fold_drawdown >= -0.55
