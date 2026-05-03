from pathlib import Path

import pandas as pd

from trading_lab.models.selection import select_model_zoo_winner


def test_select_model_zoo_winner_uses_score_then_profit(tmp_path: Path):
    path = tmp_path / "ranking.csv"
    pd.DataFrame(
        [
            {
                "model": "a",
                "trades": 10,
                "mean_brier": 0.3,
                "mean_roc_auc": 0.55,
                "mean_avg_return": 0.01,
                "mean_win_rate": 0.60,
                "mean_profit_factor": 1.5,
                "worst_fold_return": -0.3,
                "worst_fold_drawdown": -0.4,
                "score": 1.0,
            },
            {
                "model": "b",
                "trades": 12,
                "mean_brier": 0.25,
                "mean_roc_auc": 0.60,
                "mean_avg_return": 0.02,
                "mean_win_rate": 0.70,
                "mean_profit_factor": 2.0,
                "worst_fold_return": -0.2,
                "worst_fold_drawdown": -0.3,
                "score": 2.0,
            },
        ]
    ).to_csv(path, index=False)

    selected = select_model_zoo_winner(path)

    assert selected.model == "b"
    assert selected.trades == 12
