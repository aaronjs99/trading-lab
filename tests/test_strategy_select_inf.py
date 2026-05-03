import pandas as pd

from trading_lab.strategy.select import select_strategy


def _row(**overrides):
    row = {
        "threshold": 0.55,
        "take_profit": 0.06,
        "stop_loss": 0.05,
        "max_hold": 5,
        "require_trend": True,
        "max_ext20": 0.06,
        "trades": 52,
        "mean_total_return": 0.36,
        "mean_avg_return": 0.043,
        "mean_win_rate": 0.71,
        "mean_profit_factor": float("inf"),
        "worst_fold_return": 0.17,
        "worst_fold_drawdown": -0.22,
    }
    row.update(overrides)
    return row


def test_select_strategy_handles_infinite_profit_factor_rows():
    selected = select_strategy(pd.DataFrame([_row()]))

    assert selected.threshold == 0.55
    assert selected.trades == 52
    assert selected.mean_profit_factor == float("inf")


def test_select_strategy_prefers_enough_trades_when_strict_filter_fails():
    ranking = pd.DataFrame(
        [
            _row(threshold=0.55, trades=52, mean_win_rate=0.71),
            _row(threshold=0.50, trades=120, mean_win_rate=0.58, mean_profit_factor=1.4),
        ]
    )

    selected = select_strategy(ranking)

    assert selected.threshold == 0.50
    assert selected.trades == 120
