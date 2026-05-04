from __future__ import annotations

from datetime import datetime
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs
import csv
import webbrowser

from trading_lab.decision import (
    DEFAULT_REPORTS_DIR,
    SUMMARY_FILE,
    format_decision,
    load_decision_inputs,
)
from trading_lab.portfolio.state import (
    ACCOUNT_PATH,
    OPEN_ORDERS_PATH,
    POSITIONS_PATH,
    append_open_order,
    build_portfolio_state,
    clear_open_orders,
    update_position_quantity,
    write_account_value,
    write_position,
)
from trading_lab.portfolio.review import (
    advice_lines,
    exposure_context,
    review_holdings,
    review_open_orders,
    suggested_order_ideas,
    summarize_order_reviews,
)


def render_status_page() -> str:
    state = build_portfolio_state()
    decision_inputs = load_decision_inputs()
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
        )
        if decision_inputs is not None and context is not None
        else ()
    )

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Trading Lab Portfolio</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #0b0711;
      --panel: #16101f;
      --panel-2: #1f1730;
      --line: #35284c;
      --text: #f4efff;
      --muted: #b9abc9;
      --accent: #b48cff;
      --danger: #ff8fa3;
      --ok: #7ee7b8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: radial-gradient(circle at top left, #211333 0, var(--bg) 36%);
      color: var(--text);
      font-family: system-ui, -apple-system, Segoe UI, sans-serif;
      line-height: 1.4;
    }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 24px; }}
    header {{
      display: grid;
      grid-template-columns: 1fr repeat(5, minmax(120px, auto));
      gap: 12px;
      align-items: end;
      margin-bottom: 18px;
    }}
    h1, h2, h3 {{ margin: 0; }}
    h1 {{ font-size: 28px; }}
    h2 {{ font-size: 18px; margin-bottom: 12px; }}
    h3 {{ font-size: 14px; margin-bottom: 8px; color: var(--muted); }}
    .muted {{ color: var(--muted); }}
    .grid {{ display: grid; grid-template-columns: 1.2fr .8fr; gap: 12px; }}
    .card {{
      background: color-mix(in srgb, var(--panel) 94%, #6f42c1 6%);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      box-shadow: 0 16px 50px rgba(0,0,0,.28);
      margin-bottom: 12px;
    }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(145px, 1fr)); gap: 8px; }}
    .metric {{ background: var(--panel-2); border: 1px solid var(--line); border-radius: 8px; padding: 9px; }}
    .metric span {{ display: block; color: var(--muted); font-size: 12px; }}
    .metric strong {{ display: block; margin-top: 2px; font-size: 15px; }}
    .action {{ font-size: 34px; color: var(--accent); letter-spacing: 0; line-height: 1; }}
    .tight p {{ margin: 8px 0; }}
    .order-actions-card {{ margin-top: 14px; }}
    .compact-list {{ margin: 8px 0 0; padding-left: 20px; }}
    .compact-list li {{ margin: 4px 0; }}
    .danger {{ color: var(--danger); }}
    .ok {{ color: var(--ok); }}
    .review {{ color: #e5c07b; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; overflow: hidden; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 9px 8px; text-align: left; }}
    th {{
      color: var(--muted);
      font-weight: 600;
      background: #171123;
      position: sticky;
      top: 0;
      z-index: 1;
    }}
    .table-scroll {{
      max-height: 360px;
      overflow-y: auto;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 8px;
      min-height: 230px;
    }}
    .mini-scroll {{
      max-height: 138px;
      min-height: 118px;
    }}
    .table-scroll table {{ margin-top: 0; }}
    .tabs {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 16px 0 12px; }}
    .tab-button {{
      width: auto;
      margin: 0;
      padding: 9px 14px;
      background: #120c1c;
      color: var(--muted);
    }}
    .tab-button.active {{ background: #6f42c1; color: var(--text); }}
    .tab-panel {{ display: none; }}
    .tab-panel.active {{ display: block; }}
    .action-CANCEL, .action-REDUCE {{ color: var(--danger); font-weight: 700; }}
    .action-KEEP {{ color: var(--ok); font-weight: 700; }}
    .action-REVIEW, .action-MOVE_LOWER {{ color: #e5c07b; font-weight: 700; }}
    form {{
      display: grid;
      grid-template-columns: repeat(5, minmax(120px, 1fr));
      gap: 8px;
      border-top: 1px solid var(--line);
      padding-top: 12px;
      margin-top: 12px;
    }}
    label {{ color: var(--muted); font-size: 12px; }}
    input, select, button {{
      width: 100%;
      margin-top: 4px;
      border-radius: 6px;
      border: 1px solid var(--line);
      background: #0f0a17;
      color: var(--text);
      padding: 8px;
    }}
    button {{ background: #6f42c1; border-color: #8e62df; cursor: pointer; font-weight: 700; }}
    .warning {{ border-color: #704155; color: #ffd3dc; background: #27121e; }}
    .span-2 {{ grid-column: span 2; }}
    .span-5 {{ grid-column: 1 / -1; }}
    @media (max-width: 860px) {{
      header, .grid, .metric-grid, form {{ grid-template-columns: 1fr; }}
      .span-2, .span-5 {{ grid-column: auto; }}
    }}
  </style>
</head>
<body>
<main>
  <h1>Trading Lab</h1>
  <div class="muted">Local decision dashboard. No broker connection.</div>
  <nav class="tabs" aria-label="Dashboard tabs">
    <button class="tab-button active" type="button" data-tab="daily">Daily</button>
    <button class="tab-button" type="button" data-tab="positions">Positions</button>
    <button class="tab-button" type="button" data-tab="orders">Open orders</button>
    <button class="tab-button" type="button" data-tab="edit">Edit local CSVs</button>
  </nav>

  <section class="tab-panel active" id="tab-daily">
    <header>
      {_header_metric("Local time", metadata["local_time"], value_id="local-clock")}
      {_header_metric("Last local refresh", metadata["local_time"], value_id="last-refresh")}
      {_header_metric("Report updated", metadata["report_updated"])}
      {_header_metric("Account value", _money(state.account_value))}
      {_header_metric("Cash", _money(state.cash))}
    </header>
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
  </section>

  <section class="tab-panel" id="tab-positions">
    <section class="card">
      <h2>Positions</h2>
      <p class="muted">No model-backed buy/sell predictions are claimed for non-traded holdings.</p>
      <div class="table-scroll">
        <table>
          <tr><th>Symbol</th><th>Quantity</th><th>Price</th><th>Value</th><th>Allocation</th><th>Updated</th><th>Review status</th><th>Review note</th></tr>
          {_position_review_rows(state, holding_reviews, decision["traded_symbol"])}
        </table>
      </div>
      {_ideas_card(ideas)}
    </section>
  </section>

  <section class="tab-panel" id="tab-orders">
    <section class="card">
      <h2>Open orders</h2>
      <div class="table-scroll">
        <table>
          <tr><th>Recommendation</th><th>Symbol</th><th>Side</th><th>Type</th><th>Quantity</th><th>Limit</th><th>Notional</th><th>Status</th><th>Submitted</th><th>Price relation</th><th>Ladder relation</th><th>Projected exposure</th><th>Reason</th></tr>
          {_combined_order_rows(state, order_reviews)}
        </table>
      </div>
    </section>
  </section>

  <section class="tab-panel" id="tab-edit">
    <section class="card">
      <h2>Edit local CSVs</h2>
      <div class="card warning">Local CSV update only. This does not place, cancel, or modify broker orders.</div>
      {_forms()}
    </section>
  </section>
</main>
<script>
  function pad(n) {{ return String(n).padStart(2, '0'); }}
  function formatLocalTime(d) {{
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) +
      ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
  }}
  function updateLocalClock() {{
    var node = document.getElementById('local-clock');
    if (node) {{ node.textContent = formatLocalTime(new Date()); }}
  }}
  updateLocalClock();
  setInterval(updateLocalClock, 1000);
  setTimeout(function () {{ window.location.reload(); }}, 60 * 60 * 1000);
  document.querySelectorAll('.tab-button').forEach(function (button) {{
    button.addEventListener('click', function () {{
      document.querySelectorAll('.tab-button').forEach(function (node) {{ node.classList.remove('active'); }});
      document.querySelectorAll('.tab-panel').forEach(function (node) {{ node.classList.remove('active'); }});
      button.classList.add('active');
      var panel = document.getElementById('tab-' + button.dataset.tab);
      if (panel) {{ panel.classList.add('active'); }}
    }});
  }});
</script>
</body>
</html>
"""


def apply_form_action(path: str, fields: dict[str, str]) -> str:
    if path == "/account":
        if fields.get("cash", "").strip():
            write_account_value(ACCOUNT_PATH, "cash", float(fields["cash"]))
        if fields.get("account_value", "").strip():
            write_account_value(ACCOUNT_PATH, "account_value", float(fields["account_value"]))
        return "updated account.csv locally"
    if path == "/position/set":
        write_position(POSITIONS_PATH, fields["symbol"], float(fields["quantity"]))
        return "set local position"
    if path == "/position/update":
        side = fields.get("side", "buy")
        quantity = float(fields["quantity"])
        delta = quantity if side == "buy" else -quantity
        update_position_quantity(
            POSITIONS_PATH,
            fields["symbol"],
            delta,
            allow_negative=fields.get("allow_negative") == "1",
        )
        return "updated local position"
    if path == "/order/add":
        append_open_order(
            OPEN_ORDERS_PATH,
            side=fields.get("side", "buy"),
            symbol=fields["symbol"],
            quantity=float(fields["quantity"]),
            limit_price=float(fields["limit_price"]),
        )
        return "added local order"
    if path == "/order/clear":
        symbol = fields.get("symbol", "").strip()
        clear_open_orders(OPEN_ORDERS_PATH, None if fields.get("all") == "1" else symbol)
        return "cleared local orders"
    raise ValueError(f"Unknown form action: {path}")


def run_gui(host: str = "127.0.0.1", port: int = 8765) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            body = render_status_page().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            fields = {key: values[-1] for key, values in parse_qs(raw).items()}
            try:
                apply_form_action(self.path, fields)
                self.send_response(303)
                self.send_header("Location", "/")
                self.end_headers()
            except Exception as exc:
                body = escape(str(exc)).encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:
            return

    server = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{server.server_port}/"
    print(f"Local-only portfolio GUI: {url}")
    print("Press Ctrl+C to stop.")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping portfolio GUI.")
    finally:
        server.server_close()


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


def _forms() -> str:
    return """
    <form method="post" action="/account">
      <label>Cash <input name="cash" type="number" step="any"></label>
      <label>Account value <input name="account_value" type="number" step="any"></label>
      <button type="submit">Save account</button>
    </form>
    <form method="post" action="/position/set">
      <label>Symbol <input name="symbol" required></label>
      <label>Quantity <input name="quantity" type="number" step="any" required></label>
      <button type="submit">Set position</button>
    </form>
    <form method="post" action="/position/update">
      <label>Side <select name="side"><option>buy</option><option>sell</option></select></label>
      <label>Symbol <input name="symbol" required></label>
      <label>Quantity <input name="quantity" type="number" step="any" required></label>
      <label><input name="allow_negative" type="checkbox" value="1"> allow negative</label>
      <button type="submit">Apply update</button>
    </form>
    <form method="post" action="/order/add">
      <label>Side <select name="side"><option>buy</option><option>sell</option></select></label>
      <label>Symbol <input name="symbol" required></label>
      <label>Quantity <input name="quantity" type="number" step="any" required></label>
      <label>Limit <input name="limit_price" type="number" step="any" required></label>
      <button type="submit">Add limit order</button>
    </form>
    <form method="post" action="/order/clear">
      <label>Symbol <input name="symbol"></label>
      <button type="submit">Clear symbol orders</button>
      <button type="submit" name="all" value="1">Clear all orders</button>
    </form>
    """


def _position_rows(state) -> str:
    rows = []
    updated = {position.symbol: position.updated_at for position in state.positions}
    for symbol in sorted(state.symbols):
        item = state.symbols[symbol]
        rows.append(
            "<tr>"
            f"<td>{escape(symbol)}</td>"
            f"<td>{item.quantity:g}</td>"
            f"<td>{_money(item.latest_price)}</td>"
            f"<td>{_money(item.market_value)}</td>"
            f"<td>{_allocation(item.allocation_pct)}</td>"
            f"<td>{escape(updated.get(symbol, ''))}</td>"
            "</tr>"
        )
    return "\n".join(rows) or "<tr><td colspan='6'>No local positions or orders.</td></tr>"


def _order_rows(state) -> str:
    rows = []
    for order in state.open_orders:
        rows.append(
            "<tr>"
            f"<td>{escape(order.symbol)}</td>"
            f"<td>{escape(order.side)}</td>"
            f"<td>{escape(order.type)}</td>"
            f"<td>{order.quantity:g}</td>"
            f"<td>{_money(order.limit_price)}</td>"
            f"<td>{_money(order.exposure)}</td>"
            f"<td>{escape(order.status)}</td>"
            f"<td>{escape(order.submitted_at)}</td>"
            "</tr>"
        )
    return "\n".join(rows) or "<tr><td colspan='8'>No local open orders.</td></tr>"


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
            "</tr>"
        )
    return "\n".join(rows) or "<tr><td colspan='8'>No local positions or orders.</td></tr>"


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
            f"<td>{escape(review.reason)}</td>"
            "</tr>"
        )
    return "\n".join(rows) or "<tr><td colspan='13'>No local open orders.</td></tr>"


def _holding_review_rows(rows) -> str:
    out = []
    for row in rows:
        out.append(
            "<tr>"
            f"<td>{escape(row.symbol)}</td>"
            f"<td>{row.quantity:g}</td>"
            f"<td>{_money(row.value)}</td>"
            f"<td>{_allocation(row.allocation)}</td>"
            f"<td>{escape(row.price_status)}</td>"
            f"<td>{escape(row.status)}</td>"
            "</tr>"
        )
    return "\n".join(out) or "<tr><td colspan='6'>No non-traded holdings.</td></tr>"


def _order_review_rows(rows) -> str:
    out = []
    for row in rows:
        out.append(
            "<tr>"
            f"<td>{escape(row.recommended_action)}</td>"
            f"<td>{escape(row.symbol)}</td>"
            f"<td>{escape(row.side)}</td>"
            f"<td>{row.quantity:g}</td>"
            f"<td>{_money(row.limit_price)}</td>"
            f"<td>{_money(row.notional)}</td>"
            f"<td>{escape(row.status)}</td>"
            f"<td>{escape(row.price_relation)}</td>"
            f"<td>{escape(row.ladder_relation)}</td>"
            f"<td>{_money(row.projected_exposure)}</td>"
            f"<td>{escape(row.reason)}</td>"
            "</tr>"
        )
    return "\n".join(out) or "<tr><td colspan='11'>No local open orders.</td></tr>"


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
