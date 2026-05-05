from __future__ import annotations

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
    if path == "/snapshot":
        from trading_lab.portfolio.snapshots import append_snapshot

        append_snapshot(
            risk_mode=fields.get("risk_mode", "conservative"),
            notes=fields.get("notes", "").strip(),
        )
        return "recorded local snapshot"
    raise ValueError(f"Unknown form action: {path}")


def render_forms() -> str:
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
