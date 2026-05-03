from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from trading_lab.reports.buckets import run_bucket_analysis
from trading_lab.workflows.commands import CommandRunner, py


RAW_DIR = Path("data/raw/robinhood")
LEDGER_DIR = Path("data/processed/ledger")
REPORT_DIR = Path("data/reports")


@dataclass(frozen=True)
class RobinhoodWorkflow:
    """Ingest Robinhood history and refresh realized-P&L reports."""

    runner: CommandRunner = CommandRunner()
    raw_dir: Path = RAW_DIR
    ledger_dir: Path = LEDGER_DIR
    report_dir: Path = REPORT_DIR

    def run(self) -> None:
        print("== Robinhood pipeline ==")
        self._show_inputs()

        self.runner.run(
            "Ingest Robinhood CSVs",
            py(
                "scripts/ingest_robinhood.py",
                "--input",
                str(self.raw_dir),
                "--output",
                str(self.ledger_dir),
            ),
        )

        self.runner.run(
            "Run edge report",
            py(
                "scripts/run_edge_report.py",
                "--ledger",
                str(self.ledger_dir),
                "--output-dir",
                str(self.report_dir),
            ),
        )

        print()
        print("== Run bucket analysis ==")
        run_bucket_analysis(self.ledger_dir / "realized_fifo_pnl.csv", self.report_dir)

        self._show_outputs()
        print()
        print("Done.")

    def _show_inputs(self) -> None:
        print(f"Input:   {self.raw_dir}")
        print(f"Ledger:  {self.ledger_dir}")
        print(f"Reports: {self.report_dir}")

        csvs = sorted(self.raw_dir.glob("*.csv"))
        print()
        print("== Found CSVs ==")
        if not csvs:
            print(f"No CSV files found under {self.raw_dir}")
            raise SystemExit(1)

        for csv in csvs:
            print(f"  {csv}")

    def _show_outputs(self) -> None:
        print()
        print("== Outputs ==")
        outputs = [
            self.ledger_dir / "normalized_trades.csv",
            self.ledger_dir / "positions.csv",
            self.ledger_dir / "realized_fifo_pnl.csv",
            self.report_dir / "analysis_summary.md",
            self.report_dir / "bucket_summary.csv",
            self.report_dir / "symbol_bucket_summary.csv",
            self.report_dir / "bucket_analysis.md",
        ]

        for output in outputs:
            if output.exists():
                print(output)


def main() -> None:
    RobinhoodWorkflow().run()


if __name__ == "__main__":
    main()
