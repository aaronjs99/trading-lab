from trading_lab.workflows.ingest_robinhood import main


def test_ingest_robinhood_main_callable():
    assert callable(main)
