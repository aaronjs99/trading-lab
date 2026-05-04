from __future__ import annotations

from dataclasses import dataclass
import sys

from trading_lab.portfolio.state import OPEN_ORDERS_PATH
from trading_lab.workflows.commands import CommandRunner, py
from trading_lab.workflows.daily import DailyWorkflow


@dataclass(frozen=True)
class FullDailyWorkflow:
    """Daily dashboard plus order parsing/reconciliation."""

    runner: CommandRunner = CommandRunner()

    def run(self) -> None:
        print("== trading-lab full daily workflow ==")

        DailyWorkflow(runner=self.runner).run()

        if OPEN_ORDERS_PATH.exists():
            print()
            print(f"== Using local portfolio open orders: {OPEN_ORDERS_PATH} ==")
        else:
            self.runner.run("Parse open orders", py("scripts/parse_open_orders.py"))
        self.runner.run(
            "Portfolio status",
            [sys.executable, "-m", "trading_lab.cli.main", "portfolio", "status"],
        )
        self.runner.run("Reconcile orders", py("scripts/reconcile_orders.py"))

        print()
        print("== Strict tests skipped ==")
        print("Run tltest when changing code or before committing.")
        print()
        print("== Done ==")


def main() -> None:
    FullDailyWorkflow().run()


if __name__ == "__main__":
    main()
