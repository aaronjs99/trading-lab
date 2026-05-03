from __future__ import annotations

import argparse
import subprocess
import sys

from trading_lab.cli.status import print_status


def _run(command: list[str]) -> int:
    return subprocess.run(command, check=False).returncode


def main() -> None:
    parser = argparse.ArgumentParser(prog="tl")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status")
    sub.add_parser("card")
    sub.add_parser("plots")
    sub.add_parser("orders")
    sub.add_parser("test")
    sub.add_parser("audit")

    args, rest = parser.parse_known_args()
    command = args.command or "status"

    if command == "status":
        print_status(refresh=False, compact=False)
        return

    if command == "card":
        print_status(refresh=False, compact=True)
        return

    if command == "plots":
        raise SystemExit(_run([sys.executable, "scripts/plot_dashboard.py"]) or _run([sys.executable, "-m", "trading_lab.plots.open_plots"]))

    if command == "orders":
        raise SystemExit(_run([sys.executable, "scripts/parse_open_orders.py"]) or _run([sys.executable, "scripts/reconcile_orders.py"]))

    if command == "test":
        raise SystemExit(_run(["./scripts/tl_test.sh", *rest]))

    if command == "audit":
        raise SystemExit(_run([sys.executable, "-m", "trading_lab.devtools.audit"]))

    raise SystemExit(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
