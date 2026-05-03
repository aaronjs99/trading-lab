from trading_lab.workflows.commands import py
from trading_lab.workflows.daily import DailyWorkflow
from trading_lab.workflows.full_daily import FullDailyWorkflow


def test_py_builds_python_command():
    cmd = py("scripts/example.py", "--flag")

    assert cmd[-2:] == ["scripts/example.py", "--flag"]


def test_workflow_objects_construct():
    assert DailyWorkflow()
    assert FullDailyWorkflow()
