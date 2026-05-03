import pandas as pd

from trading_lab.plots.model_dashboard import _capped_profit_factor


def test_capped_profit_factor_removes_inf():
    values = _capped_profit_factor(pd.Series([1.0, float("inf"), None]))

    assert values.notna().all()
    assert values.iloc[1] != float("inf")
    assert values.iloc[1] > 0
