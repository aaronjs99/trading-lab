import pandas as pd

from trading_lab.backtests.walk_forward import _event_returns


def test_event_returns_handles_scalar_qqq_dist_ma20():
    df = pd.DataFrame(
        [
            {
                "date": "2024-01-01",
                "TQQQ": 100.0,
                "proba": 0.70,
                "QQQ_uptrend_20_50": True,
                "QQQ_dist_ma_20": 0.01,
            },
            {
                "date": "2024-01-02",
                "TQQQ": 106.0,
                "proba": 0.70,
                "QQQ_uptrend_20_50": True,
                "QQQ_dist_ma_20": 0.01,
            },
            {
                "date": "2024-01-03",
                "TQQQ": 107.0,
                "proba": 0.70,
                "QQQ_uptrend_20_50": True,
                "QQQ_dist_ma_20": 0.01,
            },
            {
                "date": "2024-01-04",
                "TQQQ": 108.0,
                "proba": 0.70,
                "QQQ_uptrend_20_50": True,
                "QQQ_dist_ma_20": 0.01,
            },
            {
                "date": "2024-01-05",
                "TQQQ": 109.0,
                "proba": 0.70,
                "QQQ_uptrend_20_50": True,
                "QQQ_dist_ma_20": 0.01,
            },
            {
                "date": "2024-01-06",
                "TQQQ": 110.0,
                "proba": 0.70,
                "QQQ_uptrend_20_50": True,
                "QQQ_dist_ma_20": 0.01,
            },
            {
                "date": "2024-01-07",
                "TQQQ": 111.0,
                "proba": 0.70,
                "QQQ_uptrend_20_50": True,
                "QQQ_dist_ma_20": 0.01,
            },
        ]
    )

    trades = _event_returns(
        df=df,
        prob_col="proba",
        threshold=0.65,
        take_profit=0.05,
        stop_loss=0.05,
        max_hold=5,
        require_trend=True,
        max_ext20=0.04,
    )

    assert len(trades) == 1
    assert trades.iloc[0]["exit_reason"] == "take_profit"
