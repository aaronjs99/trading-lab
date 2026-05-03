from pathlib import Path

import pandas as pd

from trading_lab.dashboard.daily import build_daily_decision_summary


def test_daily_summary_builds_from_synthetic_reports(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    market_dir = tmp_path / "data" / "processed" / "market"
    reports_dir = tmp_path / "data" / "reports"
    market_dir.mkdir(parents=True)
    reports_dir.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "date": "2026-05-01",
                "TQQQ": 60.0,
                "QQQ": 420.0,
                "QQQ_uptrend_20_50": True,
                "QQQ_dist_ma_20": 0.06,
                "QQQ_dist_ma_50": 0.08,
                "TQQQ_drawdown_from_20d_high": -0.01,
            }
        ]
    ).to_csv(market_dir / "market_features.csv", index=False)
    pd.DataFrame([{"random_forest_proba": 0.57}]).to_csv(
        reports_dir / "latest_regime_signal.csv",
        index=False,
    )
    pd.DataFrame(
        [
            {
                "model": "logistic_regression",
                "probability": 0.58,
                "configured_target_mode": "barrier_first_hit",
                "active_target_mode": "threshold_horizon_return",
                "active_target_col": "TQQQ_threshold_horizon_return_up5pct_5d",
                "target_source": "experiment_report",
            }
        ]
    ).to_csv(reports_dir / "selected_model_latest_signal.csv", index=False)
    pd.DataFrame(
        [
            {
                "threshold": 0.65,
                "take_profit": 0.05,
                "stop_loss": 0.05,
                "max_hold": 3,
                "require_trend": True,
                "max_ext20": 0.07,
                "mean_win_rate": 0.6,
                "mean_profit_factor": 2.0,
                "mean_avg_return": 0.03,
                "mean_total_return": 0.08,
                "worst_fold_return": -0.04,
                "worst_fold_drawdown": -0.2,
                "trades": 20,
            }
        ]
    ).to_csv(reports_dir / "walk_forward_strategy_ranking.csv", index=False)

    text = build_daily_decision_summary()

    assert "Suggested action:" in text
    assert "Selected walk-forward strategy:" in text
    assert "Personal trading edge:" in text
