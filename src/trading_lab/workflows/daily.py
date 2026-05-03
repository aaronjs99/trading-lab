from __future__ import annotations

from dataclasses import dataclass

from trading_lab.workflows.commands import CommandRunner, py


@dataclass(frozen=True)
class DailyWorkflow:
    """Daily trading-lab workflow.

    This intentionally does not run pytest. Use tltest for code validation.
    """

    runner: CommandRunner = CommandRunner()

    def run(self) -> None:
        print("== trading-lab daily dashboard ==")

        self.runner.run("1. Update market data", py("scripts/update_market_data.py"))
        self.runner.run("2. Build market features", py("scripts/build_market_features.py"))
        self.runner.run("3. Train regime model", py("scripts/train_regime_model.py"))
        self.runner.run("4. Score latest regime", py("scripts/score_latest_regime.py"))
        self.runner.run("5. Score multi-horizon signals", py("scripts/score_multi_horizon.py"))
        self.runner.run("6. Generate price/regime plots", py("scripts/plot_dashboard.py"))
        self.runner.run("7. Generate model plots", py("scripts/plot_model_dashboard.py"))
        self.runner.run("8. Backtest daily regime strategies", py("scripts/backtest_regime_strategy.py"))
        self.runner.run("9. Backtest event strategies", py("scripts/backtest_event_strategy.py"))
        self.runner.run("10. Walk-forward optimize strategies", py("scripts/walk_forward_optimize.py"))
        self.runner.run("11. Select strategy", py("scripts/select_strategy.py"))
        self.runner.run("12. Run model zoo", py("scripts/run_model_zoo.py"))
        self.runner.run("13. Build model experiment report", py("scripts/model_experiment_report.py"))
        self.runner.run("14. Score selected model latest", py("scripts/score_selected_model_latest.py"))
        self.runner.run("15. Print decision summary", py("scripts/daily_decision_summary.py"))

        print()
        print("== Done ==")


def main() -> None:
    DailyWorkflow().run()


if __name__ == "__main__":
    main()
