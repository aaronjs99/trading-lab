from __future__ import annotations

from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
import webbrowser

from trading_lab.portfolio.state import (
    ACCOUNT_PATH,
    OPEN_ORDERS_PATH,
    POSITIONS_PATH,
    append_open_order,
    build_portfolio_state,
    clear_open_orders,
    summarize_portfolio_state,
    update_position_quantity,
    write_account_value,
    write_position,
)


def render_status_page() -> str:
    state = build_portfolio_state()
    position_rows = "\n".join(_position_row(item) for item in state.symbols.values())
    if not position_rows:
        position_rows = "<tr><td colspan='5'>No local positions or orders.</td></tr>"

    order_rows = "\n".join(
        "<tr>"
        f"<td>{escape(order.symbol)}</td>"
        f"<td>{escape(order.side)}</td>"
        f"<td>{escape(order.type)}</td>"
        f"<td>{order.quantity:g}</td>"
        f"<td>{order.limit_price:.2f}</td>"
        f"<td>{escape(order.status)}</td>"
        "</tr>"
        for order in state.open_orders
    )
    if not order_rows:
        order_rows = "<tr><td colspan='6'>No local open orders.</td></tr>"

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>trading-lab portfolio</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 24px; max-width: 1100px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0 24px; }}
    th, td {{ border: 1px solid #ccc; padding: 6px 8px; text-align: left; }}
    form {{ border: 1px solid #ccc; padding: 12px; margin: 12px 0; }}
    input, select, button {{ margin: 4px; }}
    pre {{ background: #f6f6f6; padding: 12px; overflow: auto; }}
  </style>
</head>
<body>
  <h1>Local portfolio</h1>
  <p>Cash: {_money(state.cash)} | Account value: {_money(state.account_value)}</p>
  <pre>{escape(summarize_portfolio_state(state))}</pre>

  <h2>Positions</h2>
  <table>
    <tr><th>Symbol</th><th>Quantity</th><th>Price</th><th>Value</th><th>Allocation</th></tr>
    {position_rows}
  </table>

  <h2>Open orders</h2>
  <table>
    <tr><th>Symbol</th><th>Side</th><th>Type</th><th>Quantity</th><th>Limit</th><th>Status</th></tr>
    {order_rows}
  </table>

  <h2>Edit local CSVs</h2>
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
    <select name="side"><option>buy</option><option>sell</option></select>
    <label>Symbol <input name="symbol" required></label>
    <label>Quantity <input name="quantity" type="number" step="any" required></label>
    <label><input name="allow_negative" type="checkbox" value="1"> allow negative</label>
    <button type="submit">Apply position update</button>
  </form>
  <form method="post" action="/order/add">
    <select name="side"><option>buy</option><option>sell</option></select>
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


def _position_row(item) -> str:
    allocation = f"{item.allocation_pct:.1%}" if item.allocation_pct is not None else "unknown"
    return (
        "<tr>"
        f"<td>{escape(item.symbol)}</td>"
        f"<td>{item.quantity:g}</td>"
        f"<td>{_money(item.latest_price)}</td>"
        f"<td>{_money(item.market_value)}</td>"
        f"<td>{allocation}</td>"
        "</tr>"
    )


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


def _money(value: float | None) -> str:
    if value is None:
        return "unavailable"
    return f"${value:,.2f}"
