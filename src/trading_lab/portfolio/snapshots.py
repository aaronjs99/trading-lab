from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from trading_lab.config import load_trading_config
from trading_lab.decision import (
    DEFAULT_REPORTS_DIR,
    format_decision,
    load_decision_inputs,
)
from trading_lab.portfolio.review import normalize_risk_mode
from trading_lab.portfolio.state import (
    ACCOUNT_PATH,
    MARKET_DIR,
    OPEN_ORDERS_PATH,
    POSITIONS_PATH,
    build_portfolio_state,
)


SNAPSHOTS_PATH = Path("data/processed/portfolio/snapshots.csv")

SNAPSHOT_COLUMNS = (
    "timestamp",
    "risk_mode",
    "action",
    "account_value",
    "cash",
    "known_equity_value",
    "known_total_value",
    "traded_symbol",
    "traded_quantity",
    "traded_value",
    "traded_allocation",
    "pending_buy_notional",
    "pending_sell_notional",
    "pending_buy_count",
    "pending_sell_count",
    "model_probability",
    "active_target_mode",
    "active_target_column",
    "current_traded_price",
    "benchmark_symbol",
    "benchmark_price",
    "benchmark_trend",
    "positions_count",
    "open_orders_count",
    "notes",
    "warnings",
)


@dataclass(frozen=True)
class SnapshotResult:
    path: Path
    row: dict[str, str]


def build_snapshot_row(
    *,
    risk_mode: str = "conservative",
    notes: str = "",
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    positions_path: Path = POSITIONS_PATH,
    open_orders_path: Path = OPEN_ORDERS_PATH,
    account_path: Path = ACCOUNT_PATH,
    market_dir: Path = MARKET_DIR,
    account_value: float | None = None,
    cash: float | None = None,
    now: datetime | None = None,
) -> dict[str, str]:
    mode = normalize_risk_mode(risk_mode)
    timestamp = (now or datetime.now()).isoformat(timespec="seconds")
    config = load_trading_config()
    state = build_portfolio_state(
        positions_path=positions_path,
        open_orders_path=open_orders_path,
        account_path=account_path,
        market_dir=market_dir,
        account_value=account_value,
        cash=cash,
    )
    inputs = load_decision_inputs(
        reports_dir=reports_dir,
        positions_path=positions_path,
        open_orders_path=open_orders_path,
        account_path=account_path,
        market_dir=market_dir,
        risk_mode=mode,
        account_value=account_value,
        cash=cash,
    )

    traded_symbol = (inputs.traded_symbol if inputs is not None else config.traded_symbol).upper()
    item = state.symbols.get(traded_symbol)
    summary = inputs.summary if inputs is not None else {}
    selected_signal = inputs.selected_signal if inputs is not None else {}
    action = _decision_action(inputs)
    account_value = state.account_value
    cash = state.cash
    known_equity = state.total_market_value
    known_total = known_equity + cash if cash is not None else None
    placed_buys = [
        order
        for order in state.open_orders
        if order.status == "placed" and order.side == "buy"
    ]
    placed_sells = [
        order
        for order in state.open_orders
        if order.status == "placed" and order.side == "sell"
    ]

    return {
        "timestamp": timestamp,
        "risk_mode": mode,
        "action": action,
        "account_value": _number(account_value),
        "cash": _number(cash),
        "known_equity_value": _number(known_equity),
        "known_total_value": _number(known_total),
        "traded_symbol": traded_symbol,
        "traded_quantity": _number(item.quantity if item is not None else 0.0),
        "traded_value": _number(item.market_value if item is not None else None),
        "traded_allocation": _number(item.allocation_pct if item is not None else None),
        "pending_buy_notional": _number(sum(order.exposure for order in placed_buys)),
        "pending_sell_notional": _number(sum(order.exposure for order in placed_sells)),
        "pending_buy_count": str(len(placed_buys)),
        "pending_sell_count": str(len(placed_sells)),
        "model_probability": selected_signal.get("probability", ""),
        "active_target_mode": summary.get("active_target_mode", ""),
        "active_target_column": summary.get("active_target_column", ""),
        "current_traded_price": _number(
            item.latest_price if item is not None else _float_or_none(summary.get("traded_price"))
        ),
        "benchmark_symbol": config.benchmark_symbol.upper(),
        "benchmark_price": summary.get(config.benchmark_symbol.lower(), ""),
        "benchmark_trend": summary.get("benchmark_trend", "") or summary.get("qqq_trend", ""),
        "positions_count": str(len(state.positions)),
        "open_orders_count": str(len(state.open_orders)),
        "notes": notes,
        "warnings": " | ".join(state.warnings),
    }


def append_snapshot(
    *,
    path: Path = SNAPSHOTS_PATH,
    risk_mode: str = "conservative",
    notes: str = "",
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    positions_path: Path = POSITIONS_PATH,
    open_orders_path: Path = OPEN_ORDERS_PATH,
    account_path: Path = ACCOUNT_PATH,
    market_dir: Path = MARKET_DIR,
    account_value: float | None = None,
    cash: float | None = None,
) -> SnapshotResult:
    row = build_snapshot_row(
        risk_mode=risk_mode,
        notes=notes,
        reports_dir=reports_dir,
        positions_path=positions_path,
        open_orders_path=open_orders_path,
        account_path=account_path,
        market_dir=market_dir,
        account_value=account_value,
        cash=cash,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(SNAPSHOT_COLUMNS), extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(row)
    return SnapshotResult(path=path, row=row)


def read_snapshots(path: Path = SNAPSHOTS_PATH, limit: int = 10) -> list[dict[str, str]]:
    if not path.exists():
        return []
    if limit <= 0:
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [
            {key: value for key, value in row.items() if key is not None}
            for row in csv.DictReader(handle)
        ]
    return rows[-limit:]


def format_snapshots(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "No local portfolio snapshots found."
    lines = ["Recent portfolio snapshots:"]
    for row in rows:
        bits = [
            row.get("timestamp", ""),
            row.get("risk_mode", ""),
            row.get("action", ""),
            row.get("traded_symbol", ""),
            _money_text(row.get("traded_value", "")),
            f"buys {_money_text(row.get('pending_buy_notional', ''))}",
            f"sells {_money_text(row.get('pending_sell_notional', ''))}",
        ]
        notes = row.get("notes", "").strip()
        suffix = f" notes={notes}" if notes else ""
        lines.append("- " + " | ".join(part for part in bits if part) + suffix)
    return "\n".join(lines)


def _decision_action(inputs) -> str:
    if inputs is None:
        return ""
    first = format_decision(inputs).splitlines()[0]
    return first.split(":", 1)[1].strip() if ":" in first else ""


def _number(value: float | int | None) -> str:
    if value is None:
        return ""
    return f"{float(value):.6g}"


def _float_or_none(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value.replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def _money_text(value: str) -> str:
    parsed = _float_or_none(value)
    return "" if parsed is None else f"${parsed:,.2f}"
