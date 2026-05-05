from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from trading_lab.config import load_trading_config
from trading_lab.decision import (
    DEFAULT_REPORTS_DIR,
    format_decision,
    load_decision_inputs,
)
from trading_lab.portfolio.review import (
    exposure_context,
    normalize_risk_mode,
    review_open_orders,
    suggested_order_ideas,
    summarize_order_reviews,
)
from trading_lab.portfolio.state import (
    ACCOUNT_PATH,
    MARKET_DIR,
    OPEN_ORDERS_PATH,
    POSITIONS_PATH,
    build_portfolio_state,
)


OUTCOMES_PATH = Path("data/processed/portfolio/decision_outcomes.csv")

OUTCOME_COLUMNS = (
    "decision_id",
    "decision_timestamp",
    "risk_mode",
    "action",
    "traded_symbol",
    "traded_price_at_decision",
    "model_probability",
    "active_target_mode",
    "active_target_column",
    "suggested_report_action",
    "strategy_eligible_today",
    "max_exposure",
    "current_exposure",
    "pending_buy_notional",
    "pending_sell_notional",
    "suggested_order_summary",
    "current_price",
    "future_price_1d",
    "future_price_3d",
    "future_price_5d",
    "future_price_10d",
    "return_1d",
    "return_3d",
    "return_5d",
    "return_10d",
    "outcome_status",
    "notes",
)

HORIZONS = (1, 3, 5, 10)


@dataclass(frozen=True)
class OutcomeResult:
    path: Path
    row: dict[str, str]


def build_outcome_row(
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
    max_allocation = _percent(summary.get("max_traded_allocation"))
    decision_price = _float_or_none(summary.get("traded_price"))
    current_price = decision_price if decision_price is not None else (
        item.latest_price if item is not None else None
    )
    max_exposure = (
        float(inputs.account_value) * max_allocation
        if inputs is not None and max_allocation is not None
        else None
    )
    current_exposure = (
        item.quantity * current_price
        if item is not None and current_price is not None
        else item.market_value if item is not None else None
    )
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
    order_summary_text = ""
    if inputs is not None:
        reviews = review_open_orders(
            state,
            traded_symbol,
            account_value=inputs.account_value,
            max_allocation=max_allocation,
            suggested_action=summary.get("suggested_action", "NO_TRADE"),
            strategy_eligible=summary.get("strategy_eligible", "").upper() == "YES",
            ladder=inputs.ladder,
            risk_mode=mode,
        )
        review_summary = summarize_order_reviews(reviews)
        context = exposure_context(state, traded_symbol, inputs.account_value, max_allocation)
        ideas = suggested_order_ideas(
            state,
            traded_symbol,
            context=context,
            reviews=reviews,
            ladder=inputs.ladder,
            risk_mode=mode,
        )
        top = [
            f"{row.recommended_action} {row.side} {row.symbol} {row.quantity:g} @ {row.limit_price:g}"
            for row in review_summary.top_actions
        ]
        order_summary_text = " | ".join(tuple(ideas) + tuple(top))

    return {
        "decision_id": timestamp,
        "decision_timestamp": timestamp,
        "risk_mode": mode,
        "action": action,
        "traded_symbol": traded_symbol,
        "traded_price_at_decision": _number(current_price),
        "model_probability": selected_signal.get("probability", ""),
        "active_target_mode": summary.get("active_target_mode", ""),
        "active_target_column": summary.get("active_target_column", ""),
        "suggested_report_action": summary.get("suggested_action", ""),
        "strategy_eligible_today": summary.get("strategy_eligible", ""),
        "max_exposure": _number(max_exposure),
        "current_exposure": _number(current_exposure),
        "pending_buy_notional": _number(sum(order.exposure for order in placed_buys)),
        "pending_sell_notional": _number(sum(order.exposure for order in placed_sells)),
        "suggested_order_summary": order_summary_text,
        "current_price": _number(current_price),
        "future_price_1d": "",
        "future_price_3d": "",
        "future_price_5d": "",
        "future_price_10d": "",
        "return_1d": "",
        "return_3d": "",
        "return_5d": "",
        "return_10d": "",
        "outcome_status": "PENDING" if current_price is not None else "PRICE_MISSING",
        "notes": notes,
    }


def append_outcome(
    *,
    path: Path = OUTCOMES_PATH,
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
) -> OutcomeResult:
    row = build_outcome_row(
        risk_mode=risk_mode,
        notes=notes,
        reports_dir=reports_dir,
        positions_path=positions_path,
        open_orders_path=open_orders_path,
        account_path=account_path,
        market_dir=market_dir,
        account_value=account_value,
        cash=cash,
        now=now,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(OUTCOME_COLUMNS), extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(row)
    return OutcomeResult(path=path, row=row)


def read_outcomes(path: Path = OUTCOMES_PATH, limit: int = 10) -> list[dict[str, str]]:
    if not path.exists() or limit <= 0:
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [
            {key: value for key, value in row.items() if key is not None}
            for row in csv.DictReader(handle)
        ]
    return rows[-limit:]


def update_outcomes(
    *,
    path: Path = OUTCOMES_PATH,
    market_dir: Path = MARKET_DIR,
) -> int:
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [
            {key: value for key, value in row.items() if key is not None}
            for row in csv.DictReader(handle)
        ]
    updated = 0
    output: list[dict[str, str]] = []
    for row in rows:
        new_row, changed = update_outcome_row(row, market_dir=market_dir)
        output.append(new_row)
        if changed:
            updated += 1
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(OUTCOME_COLUMNS), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(output)
    return updated


def update_outcome_row(
    row: dict[str, str],
    *,
    market_dir: Path = MARKET_DIR,
) -> tuple[dict[str, str], bool]:
    out = {column: row.get(column, "") for column in OUTCOME_COLUMNS}
    symbol = out.get("traded_symbol", "").upper()
    decision_date = _date_from_timestamp(out.get("decision_timestamp", ""))
    prices = _market_prices(symbol, market_dir)
    if not symbol or decision_date is None or not prices:
        changed = out.get("outcome_status") != "PRICE_MISSING"
        out["outcome_status"] = "PRICE_MISSING"
        return out, changed

    future = [(row_date, price) for row_date, price in prices if row_date > decision_date]
    base = _float_or_none(out.get("traded_price_at_decision")) or _price_on_or_before(
        prices,
        decision_date,
    )
    if base is not None and not out.get("current_price"):
        out["current_price"] = _number(base)
    if base is not None and not out.get("traded_price_at_decision"):
        out["traded_price_at_decision"] = _number(base)

    original = dict(out)
    for horizon in HORIZONS:
        price_key = f"future_price_{horizon}d"
        return_key = f"return_{horizon}d"
        if len(future) >= horizon:
            future_price = future[horizon - 1][1]
            out[price_key] = _number(future_price)
            out[return_key] = _number(future_price / base - 1.0) if base else ""
        else:
            out.setdefault(price_key, "")
            out.setdefault(return_key, "")

    if all(out.get(f"future_price_{horizon}d") for horizon in HORIZONS):
        out["outcome_status"] = "UPDATED"
    elif any(out.get(f"future_price_{horizon}d") for horizon in HORIZONS):
        out["outcome_status"] = "INSUFFICIENT_FUTURE_DATA"
    else:
        out["outcome_status"] = "PENDING" if future else "INSUFFICIENT_FUTURE_DATA"
    return out, out != original


def format_outcomes(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "No local decision outcomes found."
    lines = ["Recent decision outcomes:"]
    for row in rows:
        bits = [
            row.get("decision_timestamp", ""),
            row.get("risk_mode", ""),
            row.get("action", ""),
            row.get("traded_symbol", ""),
            _money_text(row.get("traded_price_at_decision", "")),
            row.get("outcome_status", ""),
            _percent_text(row.get("return_5d", "")),
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


def _market_prices(symbol: str, market_dir: Path) -> list[tuple[date, float]]:
    path = market_dir / f"{symbol.upper()}.csv"
    if not path.exists():
        return []
    rows: list[tuple[date, float]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            parsed_date = _parse_date(row.get("date", ""))
            price = _row_price(row)
            if parsed_date is not None and price is not None:
                rows.append((parsed_date, price))
    rows.sort(key=lambda item: item[0])
    return rows


def _row_price(row: dict[str, str]) -> float | None:
    normalized = {key.strip().lower().replace(" ", "_").replace("-", "_"): key for key in row}
    for candidate in ("adj_close", "adjusted_close", "close"):
        column = normalized.get(candidate)
        if column and row.get(column, "").strip():
            return _float_or_none(row[column])
    return None


def _price_on_or_before(prices: list[tuple[date, float]], target: date) -> float | None:
    prior = [price for row_date, price in prices if row_date <= target]
    return prior[-1] if prior else None


def _date_from_timestamp(value: str) -> date | None:
    text = value.strip()
    if not text:
        return None
    return _parse_date(text[:10])


def _parse_date(value: str) -> date | None:
    text = value.strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        try:
            return datetime.strptime(text[:10], "%m/%d/%Y").date()
        except ValueError:
            return None


def _percent(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip()
    try:
        if text.endswith("%"):
            return float(text[:-1]) / 100.0
        return float(text)
    except ValueError:
        return None


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


def _percent_text(value: str) -> str:
    parsed = _float_or_none(value)
    return "" if parsed is None else f"{parsed:.1%}"
