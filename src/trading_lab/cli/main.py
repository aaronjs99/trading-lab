from __future__ import annotations

import argparse
import subprocess
import sys


def _run(command: list[str]) -> int:
    return subprocess.run(command, check=False).returncode


def main() -> None:
    parser = argparse.ArgumentParser(prog="tl")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status")
    sub.add_parser("card")
    sub.add_parser("plots")
    sub.add_parser("orders")
    sub.add_parser("demo")
    sub.add_parser("test")
    sub.add_parser("audit")
    decide = sub.add_parser("decide")
    decide.add_argument("--profile")
    decide.add_argument("--account-value", type=float)
    decide.add_argument("--position", action="append", default=[])
    decide.add_argument("--cash", type=float)
    decide.add_argument(
        "--risk-mode",
        choices=["conservative", "balanced", "aggressive"],
        default="conservative",
    )
    decide.add_argument("--snapshot", action="store_true")
    decide.add_argument("--snapshot-notes", default="")

    portfolio = sub.add_parser("portfolio")
    portfolio_sub = portfolio.add_subparsers(dest="portfolio_command")
    portfolio_status = portfolio_sub.add_parser("status")
    portfolio_status.add_argument("--account-value", type=float)
    portfolio_status.add_argument("--cash", type=float)
    portfolio_sub.add_parser("positions")
    portfolio_sub.add_parser("orders")
    portfolio_sub.add_parser("gui")
    portfolio_snapshot = portfolio_sub.add_parser("snapshot")
    portfolio_snapshot.add_argument(
        "--risk-mode",
        choices=["conservative", "balanced", "aggressive"],
        default="conservative",
    )
    portfolio_snapshot.add_argument("--notes", default="")
    portfolio_snapshots = portfolio_sub.add_parser("snapshots")
    portfolio_snapshots.add_argument("--limit", type=int, default=10)
    portfolio_set = portfolio_sub.add_parser("set")
    portfolio_set.add_argument("symbol")
    portfolio_set.add_argument("quantity", type=float)
    portfolio_order = portfolio_sub.add_parser("order")
    portfolio_order_sub = portfolio_order.add_subparsers(dest="portfolio_order_command")
    portfolio_order_add = portfolio_order_sub.add_parser("add")
    portfolio_order_add.add_argument("side", choices=["buy", "sell"])
    portfolio_order_add.add_argument("symbol")
    portfolio_order_add.add_argument("quantity", type=float)
    portfolio_order_add.add_argument("limit_price", type=float)

    update = sub.add_parser("update")
    update_sub = update.add_subparsers(dest="update_command")
    for name in ("buy", "sell", "set"):
        update_position = update_sub.add_parser(name)
        update_position.add_argument("symbol")
        update_position.add_argument("quantity", type=float)
        if name == "sell":
            update_position.add_argument("--allow-negative", action="store_true")
    update_cash = update_sub.add_parser("cash")
    update_cash.add_argument("amount", type=float)
    update_account = update_sub.add_parser("account-value")
    update_account.add_argument("amount", type=float)
    update_order = update_sub.add_parser("order")
    update_order_sub = update_order.add_subparsers(dest="update_order_command")
    for side in ("buy", "sell"):
        update_order_add = update_order_sub.add_parser(side)
        update_order_add.add_argument("symbol")
        update_order_add.add_argument("quantity", type=float)
        update_order_add.add_argument("limit_price", type=float)
    update_order_clear = update_order_sub.add_parser("clear")
    update_order_clear.add_argument("symbol")
    update_order_sub.add_parser("clear-all")

    args, rest = parser.parse_known_args()
    command = args.command or "status"

    if command == "status":
        from trading_lab.cli.status import print_status

        print_status(refresh=False, compact=False)
        return

    if command == "card":
        from trading_lab.cli.status import print_status

        print_status(refresh=False, compact=True)
        return

    if command == "decide":
        from trading_lab.decision import render_daily_decision

        text = render_daily_decision(
            profile=args.profile,
            account_value=args.account_value,
            positions=args.position,
            cash=args.cash,
            risk_mode=args.risk_mode,
        )
        print(text)
        if not args.snapshot:
            print("\nRun tl portfolio snapshot to record this state.")
            return
        from trading_lab.portfolio.snapshots import append_snapshot

        result = append_snapshot(
            risk_mode=args.risk_mode,
            notes=args.snapshot_notes,
            account_value=args.account_value,
            cash=args.cash,
        )
        print(f"\nRecorded local-only portfolio snapshot at {result.path}.")
        return

    if command == "portfolio":
        _portfolio_command(args)
        return

    if command == "update":
        _update_command(args)
        return

    if command == "plots":
        raise SystemExit(
            _run([sys.executable, "scripts/plot_dashboard.py"])
            or _run([sys.executable, "-m", "trading_lab.plots.open_plots"])
        )

    if command == "orders":
        raise SystemExit(
            _run([sys.executable, "scripts/parse_open_orders.py"])
            or _run([sys.executable, "scripts/reconcile_orders.py"])
        )

    if command == "demo":
        from trading_lab.workflows.demo import run_demo

        run_demo()
        return

    if command == "test":
        raise SystemExit(_run(["./scripts/tl_test.sh", *rest]))

    if command == "audit":
        raise SystemExit(_run([sys.executable, "-m", "trading_lab.devtools.audit"]))

    raise SystemExit(f"Unknown command: {command}")


def _portfolio_command(args: argparse.Namespace) -> None:
    from trading_lab.portfolio.state import (
        OPEN_ORDERS_PATH,
        POSITIONS_PATH,
        append_open_order,
        build_portfolio_state,
        read_open_orders,
        read_positions,
        summarize_portfolio_state,
        write_position,
    )

    command = args.portfolio_command or "status"
    if command == "status":
        state = build_portfolio_state(account_value=args.account_value, cash=args.cash)
        lines = [summarize_portfolio_state(state)]
        from trading_lab.config import load_trading_config
        from trading_lab.portfolio.review import review_holdings

        traded = load_trading_config().traded_symbol
        reviews = review_holdings(state, traded)
        if reviews:
            lines.extend(["", "Non-traded holdings trend review:"])
            for row in reviews:
                date_text = f", price date {row.latest_price_date}" if row.latest_price_date else ""
                lines.append(
                    f"- {row.symbol}: size {row.status}, trend {row.trend_status}{date_text}. "
                    f"{row.trend_note}"
                )
            lines.append("- No model-backed predictions are claimed for non-traded holdings.")
        print("\n".join(lines))
        return
    if command == "positions":
        positions = read_positions()
        if not positions:
            print(f"No local positions found at {POSITIONS_PATH}.")
            return
        for position in positions:
            print(
                f"{position.symbol},{position.quantity:g},{position.notes},{position.updated_at}"
            )
        return
    if command == "orders":
        orders = read_open_orders()
        if not orders:
            print(f"No local open orders found at {OPEN_ORDERS_PATH}.")
            return
        for order in orders:
            print(
                f"{order.symbol},{order.side},{order.type},{order.quantity:g},"
                f"{order.limit_price:.2f},{order.time_in_force},{order.status},"
                f"{order.submitted_at},{order.notes}"
            )
        return
    if command == "gui":
        from trading_lab.portfolio.gui import run_gui

        run_gui()
        return
    if command == "snapshot":
        from trading_lab.portfolio.snapshots import append_snapshot

        result = append_snapshot(risk_mode=args.risk_mode, notes=args.notes)
        print(f"Recorded local-only portfolio snapshot at {result.path}.")
        return
    if command == "snapshots":
        from trading_lab.portfolio.snapshots import format_snapshots, read_snapshots

        print(format_snapshots(read_snapshots(limit=args.limit)))
        return
    if command == "set":
        write_position(POSITIONS_PATH, args.symbol, args.quantity)
        print(f"Updated local position for {args.symbol.upper()} in {POSITIONS_PATH}.")
        return
    if command == "order":
        if args.portfolio_order_command != "add":
            raise SystemExit(
                "Usage: tl portfolio order add {buy,sell} SYMBOL QUANTITY LIMIT_PRICE"
            )
        append_open_order(
            OPEN_ORDERS_PATH,
            side=args.side,
            symbol=args.symbol,
            quantity=args.quantity,
            limit_price=args.limit_price,
        )
        print(
            f"Added local {args.side} limit order for "
            f"{args.symbol.upper()} in {OPEN_ORDERS_PATH}."
        )
        return
    raise SystemExit(f"Unknown portfolio command: {command}")


def _update_command(args: argparse.Namespace) -> None:
    from trading_lab.portfolio.state import (
        ACCOUNT_PATH,
        OPEN_ORDERS_PATH,
        POSITIONS_PATH,
        append_open_order,
        clear_open_orders,
        update_position_quantity,
        write_account_value,
        write_position,
    )

    command = args.update_command
    if command == "buy":
        before, after = update_position_quantity(POSITIONS_PATH, args.symbol, args.quantity)
        print(
            f"Local-only update: {args.symbol.upper()} position {before:g} -> {after:g} "
            f"in {POSITIONS_PATH}."
        )
        return
    if command == "sell":
        before, after = update_position_quantity(
            POSITIONS_PATH,
            args.symbol,
            -args.quantity,
            allow_negative=args.allow_negative,
        )
        print(
            f"Local-only update: {args.symbol.upper()} position {before:g} -> {after:g} "
            f"in {POSITIONS_PATH}."
        )
        return
    if command == "set":
        write_position(POSITIONS_PATH, args.symbol, args.quantity)
        print(
            f"Local-only update: set {args.symbol.upper()} position to {args.quantity:g} "
            f"in {POSITIONS_PATH}."
        )
        return
    if command == "cash":
        write_account_value(ACCOUNT_PATH, "cash", args.amount)
        print(f"Local-only update: set cash to ${args.amount:,.2f} in {ACCOUNT_PATH}.")
        return
    if command == "account-value":
        write_account_value(ACCOUNT_PATH, "account_value", args.amount)
        print(
            f"Local-only update: set account value to ${args.amount:,.2f} "
            f"in {ACCOUNT_PATH}."
        )
        return
    if command == "order":
        _update_order_command(args, OPEN_ORDERS_PATH, append_open_order, clear_open_orders)
        return
    raise SystemExit("Usage: tl update {buy,sell,set,cash,account-value,order} ...")


def _update_order_command(
    args: argparse.Namespace,
    open_orders_path,
    append_open_order,
    clear_open_orders,
) -> None:
    command = args.update_order_command
    if command in {"buy", "sell"}:
        append_open_order(
            open_orders_path,
            side=command,
            symbol=args.symbol,
            quantity=args.quantity,
            limit_price=args.limit_price,
        )
        print(
            f"Local-only update: added placed {command} limit order for "
            f"{args.quantity:g} {args.symbol.upper()} at ${args.limit_price:,.2f} "
            f"in {open_orders_path}."
        )
        return
    if command == "clear":
        cleared = clear_open_orders(open_orders_path, args.symbol)
        print(
            f"Local-only update: marked {cleared} open order(s) for "
            f"{args.symbol.upper()} canceled in {open_orders_path}."
        )
        return
    if command == "clear-all":
        cleared = clear_open_orders(open_orders_path)
        print(
            f"Local-only update: marked {cleared} open order(s) canceled "
            f"in {open_orders_path}."
        )
        return
    raise SystemExit("Usage: tl update order {buy,sell,clear,clear-all} ...")


if __name__ == "__main__":
    main()
