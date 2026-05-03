from trading_lab.workflows.market_features import main


def test_market_feature_workflow_main_callable():
    assert callable(main)
