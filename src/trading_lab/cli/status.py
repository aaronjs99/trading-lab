from __future__ import annotations

from pathlib import Path

from trading_lab.dashboard.action_card import write_action_card
from trading_lab.dashboard.daily import build_daily_decision_summary


SUMMARY = Path("data/reports/daily_decision_summary.txt")
ACTION_CARD = Path("data/reports/action_card.md")


def print_status(refresh: bool = False, compact: bool = False) -> None:
    if refresh or not SUMMARY.exists():
        build_daily_decision_summary()

    if compact:
        write_action_card()
        print(ACTION_CARD.read_text(encoding="utf-8"))
        return

    print(SUMMARY.read_text(encoding="utf-8"))


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    print_status(refresh=args.refresh, compact=args.compact)


if __name__ == "__main__":
    main()
