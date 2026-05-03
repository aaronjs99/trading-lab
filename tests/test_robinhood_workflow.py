from pathlib import Path

from trading_lab.workflows.robinhood import RobinhoodWorkflow


def test_robinhood_workflow_paths_are_configurable():
    workflow = RobinhoodWorkflow(
        raw_dir=Path("raw"),
        ledger_dir=Path("ledger"),
        report_dir=Path("reports"),
    )

    assert workflow.raw_dir == Path("raw")
    assert workflow.ledger_dir == Path("ledger")
    assert workflow.report_dir == Path("reports")
