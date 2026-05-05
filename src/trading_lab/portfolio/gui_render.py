from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
import csv

from trading_lab.decision import (
    DEFAULT_REPORTS_DIR,
    SUMMARY_FILE,
    format_decision,
    load_decision_inputs,
)
from trading_lab.portfolio.gui_assets import CSS, dashboard_script
from trading_lab.portfolio.gui_forms import render_forms
from trading_lab.portfolio.outcomes import read_outcomes
from trading_lab.portfolio.snapshots import read_snapshots
from trading_lab.portfolio.state import (
    ACCOUNT_PATH,
    OPEN_ORDERS_PATH,
    POSITIONS_PATH,
    build_portfolio_state,
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


def render_status_page(risk_mode: str = "conservative", active_tab: str = "daily") -> str:
    risk_mode = normalize_risk_mode(risk_mode)
    active_tab = _normalize_tab(active_tab)
    state = build_portfolio_state()
    decision_inputs = load_decision_inputs(risk_mode=risk_mode)
    decision_text = format_decision(decision_inputs) if decision_inputs is not None else ""
    decision = _decision_view_model(decision_text, decision_inputs)
    traded_item = state.symbols.get(decision["traded_symbol"])
    metadata = _metadata(decision["traded_symbol"])
    max_allocation = _percent(decision_inputs.summary.get("max_traded_allocation")) if decision_inputs else None
    holding_reviews = (
        review_holdings(state, decision_inputs.traded_symbol) if decision_inputs is not None else ()
    )
    order_reviews = (
        review_open_orders(
            state,
            decision_inputs.traded_symbol,
            account_value=decision_inputs.account_value,
            max_allocation=max_allocation,
            suggested_action=decision_inputs.summary.get("suggested_action", "NO_TRADE"),
            strategy_eligible=decision_inputs.summary.get("strategy_eligible", "").upper() == "YES",
            ladder=decision_inputs.ladder,
            risk_mode=risk_mode,
        )
        if decision_inputs is not None
        else ()
    )
    order_summary = summarize_order_reviews(order_reviews)
    context = (
        exposure_context(
            state,
            decision_inputs.traded_symbol,
            decision_inputs.account_value,
            max_allocation,
        )
        if decision_inputs is not None
        else None
    )
    advice = (
        advice_lines(
            state,
            decision_inputs.traded_symbol,
            action=decision["action"],
            max_exposure=context.max_exposure if context is not None else None,
            order_summary=order_summary,
            risk_mode=risk_mode,
        )
        if decision_inputs is not None
        else ()
    )
    ideas = (
        suggested_order_ideas(
            state,
            decision_inputs.traded_symbol,
            context=context,
            reviews=order_reviews,
            ladder=decision_inputs.ladder,
            risk_mode=risk_mode,
        )
        if decision_inputs is not None and context is not None
        else ()
    )
    topbar = _topbar(active_tab)
    global_controls = _global_controls(risk_mode, metadata, state)
    daily_tab = _daily_tab(
        active_tab,
        risk_mode,
        state,
        decision,
        traded_item,
        metadata,
        order_summary,
        advice,
        _snapshot_card(risk_mode),
        _outcome_card(risk_mode),
    )
    positions_tab = _positions_tab(
        active_tab,
        state,
        holding_reviews,
        decision["traded_symbol"],
        ideas,
    )
    orders_tab = _orders_tab(active_tab, state, order_reviews)
    edit_tab = _edit_tab(active_tab)

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Trading Lab Portfolio</title>
  <style>{CSS}</style>
</head>
<body>
<main>
  {topbar}
  {global_controls}
  {daily_tab}
  {positions_tab}
  {orders_tab}
  {edit_tab}
</main>
<script>{dashboard_script(active_tab, risk_mode)}</script>
</body>
</html>
"""


def _topbar(active_tab: str) -> str:
    return f"""
  <div class="topbar">
    <div>
      <h1>Trading Lab</h1>
      <div class="muted">Local decision dashboard. No broker connection.</div>
    </div>
    <nav class="tabs" aria-label="Dashboard tabs">
      {_tab_button("daily", "Daily", active_tab)}
      {_tab_button("positions", "Positions", active_tab)}
      {_tab_button("orders", "Open orders", active_tab)}
      {_tab_button("edit", "Edit local CSVs", active_tab)}
    </nav>
  </div>"""


def _global_controls(risk_mode: str, metadata: dict[str, str], state) -> str:
    return f"""
  <section class="global-controls" aria-label="Global dashboard controls">
    <div class="risk-control">
      <span>Risk mode</span>
      <div class="risk-segmented" role="radiogroup" aria-label="Risk mode">
        {_risk_pill("conservative", risk_mode)}
        {_risk_pill("balanced", risk_mode)}
        {_risk_pill("aggressive", risk_mode)}
      </div>
    </div>
    {_header_metric("Local time", metadata["local_time"], value_id="local-clock")}
    {_header_metric("Last local refresh", metadata["local_time"], value_id="last-refresh")}
    {_header_metric("Report updated", metadata["report_updated"])}
    {_header_metric("Account value", _money(state.account_value))}
    {_header_metric("Cash", _money(state.cash))}
  </section>"""


def _daily_tab(
    active_tab: str,
    risk_mode: str,
    state,
    decision: dict[str, object],
    traded_item,
    metadata: dict[str, str],
    order_summary,
    advice,
    snapshot_card: str,
    outcome_card: str,
) -> str:
    return f"""
  <section class="{_tab_panel_class("daily", active_tab)}" id="tab-daily">
    <p class="muted">Local dashboard refreshes hourly from existing files. Run tlfull to update market/model reports.</p>

    <section class="card tight">
      <h2>Daily decision</h2>
      <div class="action">{escape(decision["action"])}</div>
      <p><strong>Now:</strong> {escape(decision["now"])}</p>
      <p><strong>Decision:</strong> {escape(decision["sentence"])}</p>
      <div class="metric-grid">
        {_metric("Traded symbol", decision["traded_symbol"])}
        {_metric("Current position", _quantity(traded_item.quantity if traded_item else 0))}
        {_metric("Current allocation", _allocation(traded_item.allocation_pct if traded_item else None))}
        {_metric("Pending buys", _money(traded_item.pending_buy_value if traded_item else 0))}
        {_metric("Pending sells", _money(traded_item.pending_sell_value if traded_item else 0))}
        {_metric("Max exposure", decision["max_exposure"])}
        {_metric("Buy capacity", decision["buy_capacity"])}
        {_metric("Portfolio action", decision["portfolio_action"])}
        {_metric("Risk mode", risk_mode)}
        {_metric("Total buy orders", _money(order_summary.total_pending_buy_notional))}
        {_metric("Total sell orders", _money(order_summary.total_pending_sell_notional))}
        {_metric("Flagged orders", str(order_summary.cancel_reduce_review_count))}
      </div>
      {_top_order_actions(order_summary.top_actions)}
      {_advice_card(advice)}
      <p class="muted">Model probability: {escape(decision["probability"])} | Active target: {escape(decision["target"])}</p>
      {_blockers(decision["blockers"])}
    </section>

    <div class="grid">
      <section class="card">
        <h2>Portfolio summary</h2>
        <div class="metric-grid">
          {_metric("Total positions", str(len(state.positions)))}
          {_metric("Open orders", str(len(state.open_orders)))}
          {_metric("Known equity value", _money(state.total_market_value))}
          {_metric("Cash", _money(state.cash))}
          {_metric("Account value", _money(state.account_value))}
          {_metric("Missing prices", str(len(state.warnings)))}
        </div>
        {_warnings(state.warnings)}
      </section>

      <section class="card">
        <h2>Dates and updates</h2>
        <div class="table-scroll mini-scroll">
          <table>
            <tr><th>Item</th><th>Latest</th></tr>
            {_date_row("positions.csv modified", metadata["positions_mtime"])}
            {_date_row("open_orders.csv modified", metadata["orders_mtime"])}
            {_date_row("account.csv modified", metadata["account_mtime"])}
            {_date_row("Market CSV date", metadata["market_date"])}
            {_date_row("Daily report date", metadata["report_updated"])}
          </table>
        </div>
        <p class="muted">If prices are stale or missing, run market update or tlfull.</p>
      </section>
    </div>
    {snapshot_card}
    {outcome_card}
  </section>"""


def _positions_tab(active_tab: str, state, holding_reviews, traded_symbol: str, ideas) -> str:
    return f"""
  <section class="{_tab_panel_class("positions", active_tab)}" id="tab-positions">
    <section class="card">
      <h2>Positions</h2>
      <p class="muted">No model-backed buy/sell predictions are claimed for non-traded holdings.</p>
      <div class="table-scroll">
        <table>
          <tr><th>Symbol</th><th>Quantity</th><th>Price</th><th>Value</th><th>Allocation</th><th>Updated</th><th>Review status</th><th>Review note</th><th>Price date</th><th>Trend status</th><th>Trend note</th></tr>
          {_position_review_rows(state, holding_reviews, traded_symbol)}
        </table>
      </div>
      {_ideas_card(ideas)}
    </section>
  </section>"""


def _orders_tab(active_tab: str, state, order_reviews) -> str:
    return f"""
  <section class="{_tab_panel_class("orders", active_tab)}" id="tab-orders">
    <section class="card">
      <h2>Open orders</h2>
      <div class="table-scroll">
        <table class="open-orders-table">
          <colgroup>
            <col class="col-recommendation">
            <col class="col-symbol">
            <col class="col-side">
            <col class="col-type">
            <col class="col-quantity">
            <col class="col-money">
            <col class="col-money">
            <col class="col-status">
            <col class="col-submitted">
            <col class="col-relation">
            <col class="col-relation">
            <col class="col-projected">
            <col class="col-reason">
          </colgroup>
          <tr><th>Recommendation</th><th>Symbol</th><th>Side</th><th>Type</th><th>Quantity</th><th>Limit</th><th>Notional</th><th>Status</th><th>Submitted</th><th>Price relation</th><th>Ladder relation</th><th>Projected exposure</th><th>Reason</th></tr>
          {_combined_order_rows(state, order_reviews)}
        </table>
      </div>
    </section>
  </section>"""


def _edit_tab(active_tab: str) -> str:
    return f"""
  <section class="{_tab_panel_class("edit", active_tab)}" id="tab-edit">
    <section class="card">
      <h2>Edit local CSVs</h2>
      <div class="card warning">Local CSV update only. This does not place, cancel, or modify broker orders.</div>
      {render_forms()}
    </section>
  </section>"""


def _snapshot_card(risk_mode: str) -> str:
    return f"""
    <section class="card">
      <h2>Portfolio snapshots</h2>
      <p class="muted">Local CSV history only. This does not run daily, download data, or contact a broker.</p>
      <form method="post" action="/snapshot">
        <input type="hidden" name="risk_mode" value="{escape(risk_mode)}">
        <label class="span-2">Notes <input name="notes"></label>
        <button type="submit">Record snapshot</button>
      </form>
      <h3>Recent snapshots</h3>
      <div class="table-scroll mini-scroll">
        <table>
          <tr><th>Timestamp</th><th>Mode</th><th>Action</th><th>Traded</th><th>Value</th><th>Notes</th></tr>
          {_snapshot_rows(read_snapshots(limit=5))}
        </table>
      </div>
    </section>"""


def _snapshot_rows(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "<tr><td colspan='6'>No local snapshots recorded.</td></tr>"
    out = []
    for row in reversed(rows):
        out.append(
            "<tr>"
            f"<td>{escape(row.get('timestamp', ''))}</td>"
            f"<td>{escape(row.get('risk_mode', ''))}</td>"
            f"<td>{escape(row.get('action', ''))}</td>"
            f"<td>{escape(row.get('traded_symbol', ''))}</td>"
            f"<td>{_money(_float_or_none(row.get('traded_value')))}</td>"
            f"<td>{escape(row.get('notes', ''))}</td>"
            "</tr>"
        )
    return "\n".join(out)


def _outcome_card(risk_mode: str) -> str:
    return f"""
    <section class="card">
      <h2>Decision outcomes</h2>
      <p class="muted">Local outcome tracking only. This rereads existing CSVs and never runs daily or contacts a broker.</p>
      <form method="post" action="/outcome/record">
        <input type="hidden" name="risk_mode" value="{escape(risk_mode)}">
        <label class="span-2">Notes <input name="notes"></label>
        <button type="submit">Record outcome</button>
      </form>
      <form method="post" action="/outcome/update">
        <button type="submit">Update outcomes</button>
      </form>
      <h3>Recent outcomes</h3>
      <div class="table-scroll mini-scroll">
        <table>
          <tr><th>Timestamp</th><th>Mode</th><th>Action</th><th>Symbol</th><th>Price</th><th>5d return</th><th>Status</th></tr>
          {_outcome_rows(read_outcomes(limit=5))}
        </table>
      </div>
    </section>"""


def _outcome_rows(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "<tr><td colspan='7'>No local outcomes recorded.</td></tr>"
    out = []
    for row in reversed(rows):
        out.append(
            "<tr>"
            f"<td>{escape(row.get('decision_timestamp', ''))}</td>"
            f"<td>{escape(row.get('risk_mode', ''))}</td>"
            f"<td>{escape(row.get('action', ''))}</td>"
            f"<td>{escape(row.get('traded_symbol', ''))}</td>"
            f"<td>{_money(_float_or_none(row.get('traded_price_at_decision')))}</td>"
            f"<td>{_percent_text(row.get('return_5d', ''))}</td>"
            f"<td>{escape(row.get('outcome_status', ''))}</td>"
            "</tr>"
        )
    return "\n".join(out)


def _decision_view_model(decision_text: str, inputs) -> dict[str, object]:
    lines = decision_text.splitlines()
    selected = inputs.selected_signal if inputs is not None else {}
    traded = inputs.traded_symbol if inputs is not None else "TQQQ"
    blockers = list(inputs.blockers) if inputs is not None else []
    target = ""
    if inputs is not None:
        target = inputs.summary.get("active_target_column") or inputs.summary.get("active_target_mode") or ""
    return {
        "action": _line_value(lines, "ACTION") or "NO REPORT",
        "now": _line_value(lines, "Now") or "Reports are missing; run daily workflow when ready.",
        "sentence": _line_value(lines, "Decision") or "No local decision report available.",
        "traded_symbol": traded,
        "max_exposure": _line_value(lines, f"Max {traded} exposure") or "unknown",
        "buy_capacity": _line_value(lines, "Buy capacity now") or "unknown",
        "portfolio_action": _portfolio_action_line(lines),
        "probability": selected.get("probability", "unknown"),
        "target": target or "unknown",
        "blockers": blockers,
    }


def _line_value(lines: list[str], key: str) -> str:
    prefix = f"{key}:"
    for line in lines:
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return ""


def _portfolio_action_line(lines: list[str]) -> str:
    for line in lines:
        if line.startswith("- Portfolio action:"):
            return line.split(":", 1)[1].strip().rstrip(".")
    return "unknown"


def _metadata(traded_symbol: str) -> dict[str, str]:
    report_path = DEFAULT_REPORTS_DIR / SUMMARY_FILE
    return {
        "local_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "positions_mtime": _mtime(POSITIONS_PATH),
        "orders_mtime": _mtime(OPEN_ORDERS_PATH),
        "account_mtime": _mtime(ACCOUNT_PATH),
        "market_date": _latest_csv_date(Path("data/raw/market") / f"{traded_symbol}.csv"),
        "report_date": _report_date(report_path),
        "report_updated": _report_updated(report_path),
    }


def _normalize_tab(value: str) -> str:
    return value if value in {"daily", "positions", "orders", "edit"} else "daily"


def _tab_button(value: str, label: str, active_tab: str) -> str:
    active = " active" if value == active_tab else ""
    return (
        f'<button class="tab-button{active}" type="button" '
        f'data-tab="{escape(value)}">{escape(label)}</button>'
    )


def _tab_panel_class(value: str, active_tab: str) -> str:
    active = " active" if value == active_tab else ""
    return f"tab-panel{active}"


def _risk_pill(value: str, selected: str) -> str:
    active = " active" if value == selected else ""
    label = value.capitalize()
    return (
        f'<button class="risk-pill{active}" type="button" role="radio" '
        f'aria-checked="{str(value == selected).lower()}" '
        f'data-risk-mode="{escape(value)}">{escape(label)}</button>'
    )


def _position_review_rows(state, reviews, traded_symbol: str) -> str:
    review_map = {row.symbol: row for row in reviews}
    updated = {position.symbol: position.updated_at for position in state.positions}
    rows = []
    for symbol in sorted(state.symbols):
        item = state.symbols[symbol]
        review = review_map.get(symbol)
        if symbol == traded_symbol:
            status = "TRADED_SYMBOL"
            note = "Primary modeled symbol for daily decision."
        elif review is None:
            status = "REVIEW"
            note = "No non-traded holding review available."
        else:
            status = review.status
            note = f"Price {review.price_status}; no model-backed prediction."
        trend_status = review.trend_status if review is not None else "REVIEW"
        trend_note = review.trend_note if review is not None else "No trend review available."
        latest_price_date = review.latest_price_date if review is not None else ""
        rows.append(
            "<tr>"
            f"<td>{escape(symbol)}</td>"
            f"<td>{item.quantity:g}</td>"
            f"<td>{_money(item.latest_price)}</td>"
            f"<td>{_money(item.market_value)}</td>"
            f"<td>{_allocation(item.allocation_pct)}</td>"
            f"<td>{escape(updated.get(symbol, ''))}</td>"
            f"<td>{escape(status)}</td>"
            f"<td>{escape(note)}</td>"
            f"<td>{escape(latest_price_date)}</td>"
            f"<td>{escape(trend_status)}</td>"
            f"<td>{escape(trend_note)}</td>"
            "</tr>"
        )
    return "\n".join(rows) or "<tr><td colspan='11'>No local positions or orders.</td></tr>"


def _combined_order_rows(state, reviews) -> str:
    rows = []
    for order, review in zip(state.open_orders, reviews):
        rows.append(
            "<tr>"
            f"<td class=\"action-{escape(review.recommended_action)}\">"
            f"{escape(review.recommended_action)}</td>"
            f"<td>{escape(order.symbol)}</td>"
            f"<td>{escape(order.side)}</td>"
            f"<td>{escape(order.type)}</td>"
            f"<td>{order.quantity:g}</td>"
            f"<td>{_money(order.limit_price)}</td>"
            f"<td>{_money(order.exposure)}</td>"
            f"<td>{escape(order.status)}</td>"
            f"<td>{escape(order.submitted_at)}</td>"
            f"<td>{escape(review.price_relation)}</td>"
            f"<td>{escape(review.ladder_relation)}</td>"
            f"<td>{_money(review.projected_exposure)}</td>"
            f"<td class=\"reason-cell\">{escape(review.reason)}</td>"
            "</tr>"
        )
    return "\n".join(rows) or "<tr><td colspan='13'>No local open orders.</td></tr>"


def _top_order_actions(rows) -> str:
    if not rows:
        return '<p class="ok">No cancel/reduce/review order actions.</p>'
    items = "".join(
        f"<li>{escape(row.recommended_action)} {escape(row.side)} {escape(row.symbol)} "
        f"{row.quantity:g} @ {_money(row.limit_price)}: {escape(row.reason)}</li>"
        for row in rows
    )
    return (
        '<div class="card warning order-actions-card"><h3>Top order actions</h3>'
        f'<ul class="compact-list">{items}</ul></div>'
    )


def _advice_card(lines) -> str:
    if not lines:
        return ""
    items = "".join(f"<li>{escape(line)}</li>" for line in lines)
    return (
        '<div class="card order-actions-card"><h3>Advice and Interpretation</h3>'
        f'<ul class="compact-list">{items}</ul></div>'
    )


def _ideas_card(lines) -> str:
    if not lines:
        return ""
    items = "".join(f"<li>{escape(line)}</li>" for line in lines)
    return (
        '<div class="card order-actions-card"><h3>Suggested order ideas</h3>'
        '<p class="muted">Local advice only. These are not broker actions.</p>'
        f'<ul class="compact-list">{items}</ul></div>'
    )


def _warnings(warnings: tuple[str, ...]) -> str:
    if not warnings:
        return '<p class="ok">All held symbols with quantities have known local prices.</p>'
    items = "".join(f"<li>{escape(warning)}</li>" for warning in warnings)
    return f'<div class="card warning"><h3>Price warnings</h3><ul>{items}</ul></div>'


def _blockers(blockers: list[str]) -> str:
    if not blockers:
        return '<p class="ok">No blockers in existing reports.</p>'
    items = "".join(f"<li>{escape(blocker)}</li>" for blocker in blockers)
    return f'<div class="card warning"><h3>Blockers</h3><ul>{items}</ul></div>'


def _metric(label: str, value: str) -> str:
    return f'<div class="metric"><span>{escape(label)}</span><strong>{escape(value)}</strong></div>'


def _header_metric(label: str, value: str, value_id: str = "") -> str:
    attr = f' id="{escape(value_id)}"' if value_id else ""
    return f'<div class="metric"><span>{escape(label)}</span><strong{attr}>{escape(value)}</strong></div>'


def _date_row(label: str, value: str) -> str:
    return f"<tr><td>{escape(label)}</td><td>{escape(value)}</td></tr>"


def _mtime(path: Path) -> str:
    if not path.exists():
        return "missing"
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")


def _latest_csv_date(path: Path) -> str:
    if not path.exists():
        return "missing"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in reversed(rows):
        value = row.get("date", "").strip()
        if value:
            return value
    return "unknown"


def _report_date(path: Path) -> str:
    if not path.exists():
        return "missing"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("Date:"):
            return line.split(":", 1)[1].strip()
    return "unknown"


def _report_updated(path: Path) -> str:
    if path.exists():
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    return _report_date(path)


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


def _float_or_none(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value.replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def _money(value: float | None) -> str:
    if value is None:
        return "unavailable"
    return f"${value:,.2f}"


def _quantity(value: float | int) -> str:
    return f"{value:g}"


def _allocation(value: float | None) -> str:
    if value is None:
        return "unknown"
    return f"{value:.1%}"


def _percent_text(value: str) -> str:
    parsed = _float_or_none(value)
    return "" if parsed is None else f"{parsed:.1%}"
