from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from pathlib import Path

from trading_lab.config.profiles import PROFILE_ENV
from trading_lab.portfolio.state import (
    ACCOUNT_PATH,
    OPEN_ORDERS_PATH,
    POSITIONS_PATH,
    PortfolioState,
    build_portfolio_state,
    portfolio_files_exist,
)
from trading_lab.portfolio.review import (
    advice_lines,
    exposure_context,
    review_holdings,
    review_open_orders,
    suggested_order_ideas,
    summarize_order_reviews,
    normalize_risk_mode,
)


MISSING_REPORTS_MESSAGE = "Missing reports. Run ./scripts/tl_full_daily.sh first."
DEFAULT_REPORTS_DIR = Path("data/reports")
DEFAULT_MANUAL_DIR = Path("data/manual")
DEFAULT_MARKET_DIR = Path("data/raw/market")
SUMMARY_FILE = "daily_decision_summary.txt"
SELECTED_SIGNAL_FILE = "selected_model_latest_signal.csv"


@dataclass(frozen=True)
class Position:
    symbol: str
    quantity: float


@dataclass(frozen=True)
class DecisionInputs:
    profile: str
    traded_symbol: str
    account_value: float
    cash: float | None
    positions: tuple[Position, ...]
    summary: dict[str, str]
    reasons: tuple[str, ...]
    blockers: tuple[str, ...]
    ladder: tuple[str, ...]
    selected_signal: dict[str, str]
    portfolio_state: PortfolioState | None = None
    risk_mode: str = "conservative"
    market_dir: Path = DEFAULT_MARKET_DIR


def parse_position(value: str) -> Position:
    parts = value.split(":", 1)
    if len(parts) != 2 or not parts[0].strip():
        raise ValueError("positions must use SYMBOL:QUANTITY")
    return Position(symbol=parts[0].strip().upper(), quantity=float(parts[1]))


def render_daily_decision(
    *,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    manual_dir: Path = DEFAULT_MANUAL_DIR,
    profile: str | None = None,
    account_value: float | None = None,
    cash: float | None = None,
    positions: list[str] | tuple[str, ...] | None = None,
    positions_path: Path = POSITIONS_PATH,
    open_orders_path: Path = OPEN_ORDERS_PATH,
    account_path: Path = ACCOUNT_PATH,
    market_dir: Path = DEFAULT_MARKET_DIR,
    risk_mode: str = "conservative",
) -> str:
    """Render a fast read-only daily decision from existing report files."""

    inputs = load_decision_inputs(
        reports_dir=reports_dir,
        manual_dir=manual_dir,
        profile=profile,
        account_value=account_value,
        cash=cash,
        positions=positions,
        positions_path=positions_path,
        open_orders_path=open_orders_path,
        account_path=account_path,
        market_dir=market_dir,
        risk_mode=risk_mode,
    )
    if inputs is None:
        return MISSING_REPORTS_MESSAGE
    return format_decision(inputs)


def load_decision_inputs(
    *,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    manual_dir: Path = DEFAULT_MANUAL_DIR,
    profile: str | None = None,
    account_value: float | None = None,
    cash: float | None = None,
    positions: list[str] | tuple[str, ...] | None = None,
    positions_path: Path = POSITIONS_PATH,
    open_orders_path: Path = OPEN_ORDERS_PATH,
    account_path: Path = ACCOUNT_PATH,
    market_dir: Path = DEFAULT_MARKET_DIR,
    risk_mode: str = "conservative",
) -> DecisionInputs | None:
    _ = manual_dir
    resolved_risk_mode = normalize_risk_mode(risk_mode)
    summary_path = reports_dir / SUMMARY_FILE
    if not summary_path.exists():
        return None

    positions_path, open_orders_path, account_path, market_dir = _resolve_local_state_paths(
        reports_dir=reports_dir,
        positions_path=positions_path,
        open_orders_path=open_orders_path,
        account_path=account_path,
        market_dir=market_dir,
    )
    parsed_cli_positions = tuple(parse_position(value) for value in positions or ())

    summary_text = summary_path.read_text(encoding="utf-8")
    summary, reasons, blockers, ladder = _parse_summary(summary_text)
    selected_signal = _read_latest_csv_row(reports_dir / SELECTED_SIGNAL_FILE)
    active_profile = profile or os.environ.get(PROFILE_ENV) or summary.get("profile") or "default"

    traded = _infer_traded_symbol(summary)
    traded_price = summary.get(traded.lower())
    if traded_price is not None:
        summary["traded_price"] = traded_price
    traded_allocation = summary.get(f"max_{traded.lower()}_allocation")
    if traded_allocation is not None:
        summary["max_traded_allocation"] = traded_allocation

    resolved_account_value = float(account_value if account_value is not None else 5000.0)
    resolved_cash = cash
    local_portfolio = None
    if portfolio_files_exist(positions_path, open_orders_path, account_path):
        local_portfolio = build_portfolio_state(
            positions_path=positions_path,
            open_orders_path=open_orders_path,
            account_path=account_path,
            market_dir=market_dir,
            account_value=account_value,
            cash=cash,
        )
        if local_portfolio.account_value is not None:
            resolved_account_value = float(local_portfolio.account_value)
        if local_portfolio.cash is not None:
            resolved_cash = local_portfolio.cash

    if parsed_cli_positions:
        parsed_positions = parsed_cli_positions
    elif local_portfolio is not None:
        parsed_positions = tuple(
            Position(symbol=position.symbol, quantity=position.quantity)
            for position in local_portfolio.positions
        )
    else:
        parsed_positions = ()

    return DecisionInputs(
        profile=active_profile,
        traded_symbol=traded,
        account_value=resolved_account_value,
        cash=resolved_cash,
        positions=parsed_positions,
        summary=summary,
        reasons=tuple(reasons),
        blockers=tuple(blockers),
        ladder=tuple(ladder),
        selected_signal=selected_signal,
        portfolio_state=local_portfolio,
        risk_mode=resolved_risk_mode,
        market_dir=market_dir,
    )


def _resolve_local_state_paths(
    *,
    reports_dir: Path,
    positions_path: Path,
    open_orders_path: Path,
    account_path: Path,
    market_dir: Path,
) -> tuple[Path, Path, Path, Path]:
    if reports_dir == DEFAULT_REPORTS_DIR:
        return positions_path, open_orders_path, account_path, market_dir

    data_dir = reports_dir.parent
    resolved_positions = (
        data_dir / "raw" / "portfolio" / "positions.csv"
        if positions_path == POSITIONS_PATH
        else positions_path
    )
    resolved_open_orders = (
        data_dir / "raw" / "portfolio" / "open_orders.csv"
        if open_orders_path == OPEN_ORDERS_PATH
        else open_orders_path
    )
    resolved_account = (
        data_dir / "raw" / "portfolio" / "account.csv"
        if account_path == ACCOUNT_PATH
        else account_path
    )
    resolved_market_dir = (
        data_dir / "raw" / "market" if market_dir == DEFAULT_MARKET_DIR else market_dir
    )
    return resolved_positions, resolved_open_orders, resolved_account, resolved_market_dir


def format_decision(inputs: DecisionInputs) -> str:
    traded = inputs.traded_symbol.upper()
    price = _float_or_none(inputs.summary.get("traded_price"))
    max_allocation = _percent_or_none(inputs.summary.get("max_traded_allocation"))
    raw_action = inputs.summary.get("suggested_action", "NO_TRADE")
    eligible = inputs.summary.get("strategy_eligible", "").upper() == "YES"
    held_qty = sum(position.quantity for position in inputs.positions if position.symbol == traded)
    holding = held_qty > 0
    position_value = held_qty * price if price is not None else None
    max_dollars = inputs.account_value * max_allocation if max_allocation is not None else None
    available_budget = max_dollars
    if position_value is not None and max_dollars is not None:
        available_budget = max(max_dollars - position_value, 0.0)
    if inputs.cash is not None and available_budget is not None:
        available_budget = min(available_budget, inputs.cash)

    action = _daily_action(
        raw_action=raw_action,
        eligible=eligible,
        holding=holding,
        position_value=position_value,
        max_dollars=max_dollars,
    )

    lines = [f"ACTION: {action}", ""]
    lines.append(f"Now: {_now_instruction(action, traded, available_budget, holding)}")
    lines.append(f"Decision: {_decision_sentence(action, traded)}")
    lines.append(f"Profile: {inputs.profile}")
    lines.append(f"Risk mode: {inputs.risk_mode}")
    lines.append(f"Suggested report action: {raw_action}")
    lines.append(f"Strategy eligible today: {'YES' if eligible else 'NO'}")

    if inputs.summary.get("active_target_mode"):
        lines.append(f"Active target mode: {inputs.summary['active_target_mode']}")
    if inputs.summary.get("active_target_column"):
        lines.append(f"Active target column: {inputs.summary['active_target_column']}")
    if inputs.summary.get("target_source"):
        lines.append(f"Target source: {inputs.summary['target_source']}")

    if price is not None:
        lines.append(f"{traded} reference price: ${price:.2f}")
    if max_dollars is not None:
        lines.append(f"Max {traded} exposure: ${max_dollars:,.2f}")
    if available_budget is not None:
        lines.append(f"Buy capacity now: ${available_budget:,.2f}")
    lines.append(f"Account value: ${inputs.account_value:,.2f}")
    if inputs.cash is not None:
        lines.append(f"Cash: ${inputs.cash:,.2f}")

    lines.append(f"Already holding: {_holding_sentence(traded, held_qty, position_value)}")
    lines.append(f"In cash: {_cash_sentence(inputs.cash)}")
    if inputs.portfolio_state is not None:
        lines.extend(["", *_portfolio_decision_lines(inputs, max_allocation)])
        lines.extend(["", *_advice_lines(inputs, action, max_allocation)])
        lines.extend(["", *_portfolio_holdings_review_lines(inputs)])
        lines.extend(["", *_open_order_review_lines(inputs, max_allocation)])

    lines.extend(["", "Ladder prices:"])
    if inputs.ladder:
        lines.extend(f"- {line}" for line in inputs.ladder)
    else:
        lines.append("- No pullback ladder found in existing reports.")

    lines.extend(["", "Reasons:"])
    if inputs.reasons:
        lines.extend(f"- {reason}" for reason in inputs.reasons[:8])
    elif inputs.selected_signal:
        lines.append("- Existing selected model signal report is present.")
    else:
        lines.append("- Existing daily summary report is present.")

    lines.extend(["", "Blockers:"])
    if inputs.blockers:
        lines.extend(f"- {blocker}" for blocker in inputs.blockers)
    else:
        lines.append("- None in existing reports.")

    return "\n".join(lines)


def _portfolio_decision_lines(inputs: DecisionInputs, max_allocation: float | None) -> list[str]:
    traded = inputs.traded_symbol.upper()
    state = inputs.portfolio_state
    if state is None:
        return []
    item = state.symbols.get(traded)
    lines = ["Portfolio state:"]
    if item is None:
        lines.append(f"- Current {traded} position: 0 shares.")
        lines.append("- Pending buy orders: none.")
        lines.append("- Pending sell orders: none.")
        lines.append("- Portfolio action: do not add orders.")
        return lines

    current_value = item.market_value or 0.0
    allocation = item.allocation_pct
    worst_value = current_value + item.pending_buy_value
    worst_allocation = worst_value / inputs.account_value if inputs.account_value > 0 else None
    max_dollars = inputs.account_value * max_allocation if max_allocation is not None else None
    exceeds = max_dollars is not None and worst_value > max_dollars

    lines.append(f"- Current {traded} position: {item.quantity:g} shares.")
    if item.market_value is not None:
        allocation_text = f" ({allocation:.1%})" if allocation is not None else ""
        lines.append(
            f"- Current {traded} market value: ${item.market_value:,.2f}{allocation_text}."
        )
    else:
        lines.append(f"- Current {traded} market value: unavailable.")
    lines.append(
        f"- Pending buy orders: {item.pending_buy_quantity:g} shares, "
        f"${item.pending_buy_value:,.2f}."
    )
    lines.append(
        f"- Pending sell orders: {item.pending_sell_quantity:g} shares, "
        f"${item.pending_sell_value:,.2f}."
    )
    worst_text = f" ({worst_allocation:.1%})" if worst_allocation is not None else ""
    lines.append(f"- Worst-case if all buys fill: ${worst_value:,.2f}{worst_text}.")
    if max_dollars is not None:
        lines.append(
            f"- Pending orders exceed max recommended allocation: {'YES' if exceeds else 'NO'}."
        )
    else:
        lines.append("- Pending orders exceed max recommended allocation: unknown.")
    lines.append(f"- Portfolio action: {_portfolio_action(inputs, item, exceeds)}.")
    for warning in state.warnings:
        lines.append(f"- Warning: {warning}")
    return lines


def _portfolio_action(
    inputs: DecisionInputs,
    item,
    exceeds: bool,
) -> str:
    traded = inputs.traded_symbol.upper()
    raw_action = inputs.summary.get("suggested_action", "NO_TRADE")
    if exceeds:
        return "cancel/reduce orders"
    buy_allowed_actions = {
        "WAIT_FOR_PULLBACK",
        "TACTICAL_TQQQ_BUY_ALLOWED",
        "SMALL_TQQQ_ALLOWED",
    }
    if item.pending_buy_value > 0 and raw_action in buy_allowed_actions:
        return "keep orders"
    if item.pending_buy_value > 0:
        return "do not add orders"
    if item.quantity > 0 and raw_action == "DEFENSIVE_OR_CASH":
        return f"hold/trim existing {traded} position"
    if item.quantity > 0:
        return f"hold/trim existing {traded} position"
    return "do not add orders"


def _portfolio_holdings_review_lines(inputs: DecisionInputs) -> list[str]:
    state = inputs.portfolio_state
    if state is None:
        return []
    reviews = review_holdings(state, inputs.traded_symbol, market_dir=inputs.market_dir)
    lines = ["Portfolio holdings review:"]
    if not reviews:
        lines.append("- No non-traded holdings to review.")
        return lines
    for row in reviews:
        value = _format_money(row.value)
        allocation = _format_pct(row.allocation)
        date_text = f", price date {row.latest_price_date}" if row.latest_price_date else ""
        lines.append(
            f"- {row.symbol}: qty {row.quantity:g}, value {value}, "
            f"allocation {allocation}, price {row.price_status}, status {row.status}, "
            f"trend {row.trend_status}{date_text}. {row.trend_note}"
        )
    lines.append("- No model-backed predictions are claimed for non-traded holdings.")
    return lines


def _open_order_review_lines(
    inputs: DecisionInputs,
    max_allocation: float | None,
) -> list[str]:
    state = inputs.portfolio_state
    if state is None:
        return []
    reviews = review_open_orders(
        state,
        inputs.traded_symbol,
        account_value=inputs.account_value,
        max_allocation=max_allocation,
        suggested_action=inputs.summary.get("suggested_action", "NO_TRADE"),
        strategy_eligible=inputs.summary.get("strategy_eligible", "").upper() == "YES",
        ladder=inputs.ladder,
        risk_mode=inputs.risk_mode,
    )
    summary = summarize_order_reviews(reviews)
    lines = ["Open-order review:"]
    lines.append(f"- Total pending buy notional: {_format_money(summary.total_pending_buy_notional)}.")
    lines.append(f"- Total pending sell notional: {_format_money(summary.total_pending_sell_notional)}.")
    lines.append(f"- Orders to cancel/reduce/review: {summary.cancel_reduce_review_count}.")
    if summary.top_actions:
        lines.append("- Top order actions:")
        for row in summary.top_actions:
            lines.append(
                f"  - {row.recommended_action} {row.side} {row.symbol} "
                f"{row.quantity:g} @ {_format_money(row.limit_price)}: {row.reason}"
            )
    if not reviews:
        lines.append("- No local open orders found.")
        return lines
    lines.append("- Order details:")
    for row in reviews:
        projected = _format_money(row.projected_exposure)
        lines.append(
            f"  - {row.recommended_action} {row.symbol} {row.side} "
            f"{row.quantity:g} @ {_format_money(row.limit_price)} "
            f"({_format_money(row.notional)}, status {row.status}, "
            f"{row.price_relation}, ladder {row.ladder_relation}, "
            f"projected exposure {projected}): {row.reason}"
        )
    return lines


def _advice_lines(
    inputs: DecisionInputs,
    action: str,
    max_allocation: float | None,
) -> list[str]:
    state = inputs.portfolio_state
    if state is None:
        return []
    reviews = review_open_orders(
        state,
        inputs.traded_symbol,
        account_value=inputs.account_value,
        max_allocation=max_allocation,
        suggested_action=inputs.summary.get("suggested_action", "NO_TRADE"),
        strategy_eligible=inputs.summary.get("strategy_eligible", "").upper() == "YES",
        ladder=inputs.ladder,
        risk_mode=inputs.risk_mode,
    )
    summary = summarize_order_reviews(reviews)
    context = exposure_context(state, inputs.traded_symbol, inputs.account_value, max_allocation)
    lines = ["Advice and Interpretation:"]
    lines.extend(f"- {line}" for line in advice_lines(
        state,
        inputs.traded_symbol,
        action=action,
        max_exposure=context.max_exposure,
        order_summary=summary,
        risk_mode=inputs.risk_mode,
    ))
    if context.current_exposure is not None and context.max_exposure is not None:
        lines.append(
            f"- Exposure warning: current {inputs.traded_symbol.upper()} exposure "
            f"{_format_money(context.current_exposure)} vs max {_format_money(context.max_exposure)}."
        )
    lines.extend(["", "Suggested order ideas:"])
    lines.extend(f"- {line}" for line in suggested_order_ideas(
        state,
        inputs.traded_symbol,
        context=context,
        reviews=reviews,
        ladder=inputs.ladder,
        risk_mode=inputs.risk_mode,
    ))
    return lines


def _parse_summary(text: str) -> tuple[dict[str, str], list[str], list[str], list[str]]:
    summary: dict[str, str] = {}
    reasons: list[str] = []
    blockers: list[str] = []
    ladder: list[str] = []
    section = ""

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        if lower.endswith(":"):
            section = lower[:-1]
            if section.startswith("suggested ") and section.endswith(" ladder"):
                symbol = section.removeprefix("suggested ").removesuffix(" ladder").strip()
                if symbol:
                    summary["traded_symbol"] = symbol.upper()
            continue

        if line.startswith("- "):
            bullet = line[2:].strip()
            if section.startswith("suggested ") and section.endswith(" ladder"):
                if not bullet.lower().startswith("no buy ladder"):
                    ladder.append(bullet)
            elif section == "selected strategy eligible today":
                _collect_eligibility_bullet(bullet, reasons, blockers)
            elif section in {"personal trading edge", "selected prediction model"}:
                reasons.append(bullet)
            continue

        if ":" in line:
            key, value = line.split(":", 1)
            normalized = _normalize_key(key)
            clean_value = value.strip()
            summary[normalized] = clean_value
            _maybe_symbol_price(summary, key.strip(), clean_value)
            if normalized == "reason":
                reasons.append(clean_value)
            if normalized == "selected_strategy_eligible_today":
                summary["strategy_eligible"] = clean_value.upper()
                section = "selected strategy eligible today"
            continue

    return summary, reasons, blockers, ladder


def _collect_eligibility_bullet(bullet: str, reasons: list[str], blockers: list[str]) -> None:
    if bullet.startswith("NO:"):
        blockers.append(bullet[3:].strip())
    elif bullet.startswith("OK:"):
        reasons.append(bullet[3:].strip())
    else:
        reasons.append(bullet)


def _normalize_key(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("(", "")
        .replace(")", "")
    )


def _maybe_symbol_price(summary: dict[str, str], key: str, value: str) -> None:
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9._-]{0,9}", key) and _float_or_none(value) is not None:
        summary[key.lower()] = value


def _read_latest_csv_row(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {key: value for key, value in (rows[-1] if rows else {}).items() if key is not None}


def _infer_traded_symbol(summary: dict[str, str]) -> str:
    if summary.get("traded_symbol"):
        return summary["traded_symbol"].upper()
    for key in summary:
        if key.startswith("max_") and key.endswith("_allocation"):
            return key.removeprefix("max_").removesuffix("_allocation").upper()
    return "TQQQ"


def _daily_action(
    *,
    raw_action: str,
    eligible: bool,
    holding: bool,
    position_value: float | None,
    max_dollars: float | None,
) -> str:
    if holding and position_value is not None and max_dollars is not None and position_value > max_dollars * 1.25:
        return "TRIM"
    if raw_action == "DEFENSIVE_OR_CASH":
        return "SELL" if holding else "NO_TRADE"
    if (
        raw_action in {"TACTICAL_TQQQ_BUY_ALLOWED", "SMALL_TQQQ_ALLOWED"}
        or raw_action.startswith("TACTICAL_") and raw_action.endswith("_BUY_ALLOWED")
        or raw_action.startswith("SMALL_") and raw_action.endswith("_ALLOWED")
    ) and eligible:
        return "HOLD" if holding else "BUY_SMALL"
    if holding:
        return "HOLD"
    if raw_action == "WAIT_FOR_PULLBACK":
        return "WAIT"
    return "NO_TRADE"


def _now_instruction(action: str, traded: str, budget: float | None, holding: bool) -> str:
    if action == "BUY_SMALL":
        amount = f" up to ${budget:,.2f}" if budget is not None else " a small starter"
        return f"place no market chase; consider buying {traded}{amount} only within the plan."
    if action == "WAIT":
        return f"wait for the {traded} pullback ladder; no new buy now."
    if action == "HOLD":
        return f"hold existing {traded} position." if holding else "hold cash and wait."
    if action == "TRIM":
        return f"trim {traded} back toward the report's max exposure."
    if action == "SELL":
        return f"sell or stay defensive in {traded}."
    return "no trade from existing reports."


def _decision_sentence(action: str, traded: str) -> str:
    if action == "BUY_SMALL":
        return f"BUY_SMALL {traded}; keep size capped by cash and allocation."
    if action == "WAIT":
        return f"WAIT; do not buy {traded} until a listed ladder level trades."
    if action == "HOLD":
        return f"HOLD {traded}; no fresh signal to increase risk."
    if action == "TRIM":
        return f"TRIM {traded}; current exposure is above the cap."
    if action == "SELL":
        return f"SELL {traded} or avoid exposure until reports improve."
    return "NO_TRADE; stay in cash."


def _holding_sentence(traded: str, qty: float, value: float | None) -> str:
    if qty <= 0:
        return f"no {traded} position supplied."
    if value is None:
        return f"yes, {qty:g} shares of {traded}."
    return f"yes, {qty:g} shares of {traded}, about ${value:,.2f}."


def _cash_sentence(cash: float | None) -> str:
    if cash is None:
        return "cash not supplied."
    return f"yes, ${cash:,.2f} supplied." if cash > 0 else "no cash supplied."


def _format_money(value: float | None) -> str:
    if value is None:
        return "unavailable"
    return f"${value:,.2f}"


def _format_pct(value: float | None) -> str:
    if value is None:
        return "unknown"
    return f"{value:.1%}"


def _float_or_none(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value.replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def _percent_or_none(value: str | None) -> float | None:
    if value is None:
        return None
    stripped = value.strip()
    if stripped.endswith("%"):
        parsed = _float_or_none(stripped[:-1])
        return None if parsed is None else parsed / 100.0
    return _float_or_none(stripped)
