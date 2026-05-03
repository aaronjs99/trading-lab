from trading_lab.cli.status import print_status


def test_print_status_callable():
    assert callable(print_status)
