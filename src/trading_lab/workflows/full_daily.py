from __future__ import annotations

from dataclasses import dataclass

from trading_lab.workflows.commands import CommandRunner, py
from trading_lab.workflows.daily import DailyWorkflow


@dataclass(frozen=True)
class FullDailyWorkflow:
    """Daily dashboard plus order parsing/reconciliation."""

    runner: CommandRunner = CommandRunner()

    def run(self) -> None:
        print("== trading-lab full daily workflow ==")

        DailyWorkflow(runner=self.runner).run()

        self.runner.run("Parse open orders", py("scripts/parse_open_orders.py"))
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
