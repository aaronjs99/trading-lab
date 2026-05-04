from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


POSITIONS_PATH = Path("data/raw/portfolio/positions.csv")
OPEN_ORDERS_PATH = Path("data/raw/portfolio/open_orders.csv")
MARKET_DIR = Path("data/raw/market")

POSITION_COLUMNS = ("symbol", "quantity", "notes", "updated_at")
OPEN_ORDER_COLUMNS = (
    "symbol",
    "side",
    "type",
    "quantity",
    "limit_price",
    "time_in_force",
    "status",
    "submitted_at",
    "notes",
)


@dataclass(frozen=True)
class Position:
    symbol: str
    quantity: float
    notes: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class OpenOrder:
    symbol: str
    side: str
    type: str
    quantity: float
    limit_price: float
    time_in_force: str = ""
    status: str = ""
    submitted_at: str = ""
    notes: str = ""

    @property
    def exposure(self) -> float:
        return self.quantity * self.limit_price

    @property
    def is_placed_limit(self) -> bool:
        return self.status.lower() == "placed" and self.type.lower() == "limit"


@dataclass(frozen=True)
class SymbolPortfolioState:
    symbol: str
    quantity: float = 0.0
    latest_price: float | None = None
    market_value: float | None = None
    allocation_pct: float | None = None
    pending_buy_quantity: float = 0.0
    pending_buy_value: float = 0.0
    pending_sell_quantity: float = 0.0
    pending_sell_value: float = 0.0
    post_fill_quantity: float = 0.0
    post_fill_value: float | None = None


@dataclass(frozen=True)
class PortfolioState:
    positions: tuple[Position, ...] = ()
    open_orders: tuple[OpenOrder, ...] = ()
    symbols: dict[str, SymbolPortfolioState] = field(default_factory=dict)
    prices: dict[str, float] = field(default_factory=dict)
    account_value: float | None = None
    cash: float | None = None
    warnings: tuple[str, ...] = ()

    @property
    def total_market_value(self) -> float:
        return sum(symbol.market_value or 0.0 for symbol in self.symbols.values())


def read_positions(path: Path = POSITIONS_PATH) -> tuple[Position, ...]:
    if not path.exists():
        return ()
    rows = _read_csv_rows(path, set(POSITION_COLUMNS[:2]))
    positions: list[Position] = []
    for row in rows:
        symbol = row["symbol"].strip().upper()
        if not symbol:
            continue
        positions.append(
            Position(
                symbol=symbol,
                quantity=_parse_float(row["quantity"], f"{path}: quantity for {symbol}"),
                notes=row.get("notes", "").strip(),
                updated_at=row.get("updated_at", "").strip(),
            )
        )
    return tuple(positions)


def read_open_orders(path: Path = OPEN_ORDERS_PATH) -> tuple[OpenOrder, ...]:
    if not path.exists():
        return ()
    rows = _read_csv_rows(path, {"symbol", "side", "type", "quantity", "limit_price"})
    orders: list[OpenOrder] = []
    for row in rows:
        symbol = row["symbol"].strip().upper()
        side = row["side"].strip().lower()
        order_type = row["type"].strip().lower()
        if not symbol:
            continue
        orders.append(
            OpenOrder(
                symbol=symbol,
                side=side,
                type=order_type,
                quantity=_parse_float(row["quantity"], f"{path}: quantity for {symbol}"),
                limit_price=_parse_float(row["limit_price"], f"{path}: limit_price for {symbol}"),
                time_in_force=row.get("time_in_force", "").strip(),
                status=row.get("status", "").strip().lower(),
                submitted_at=row.get("submitted_at", "").strip(),
                notes=row.get("notes", "").strip(),
            )
        )
    return tuple(orders)


def latest_market_prices(market_dir: Path = MARKET_DIR) -> dict[str, float]:
    if not market_dir.exists():
        return {}
    prices: dict[str, float] = {}
    for path in sorted(market_dir.glob("*.csv")):
        price = _latest_price_from_csv(path)
        if price is not None:
            prices[path.stem.upper()] = price
    return prices


def build_portfolio_state(
    *,
    positions_path: Path = POSITIONS_PATH,
    open_orders_path: Path = OPEN_ORDERS_PATH,
    market_dir: Path = MARKET_DIR,
    account_value: float | None = None,
    cash: float | None = None,
) -> PortfolioState:
    positions = read_positions(positions_path)
    open_orders = read_open_orders(open_orders_path)
    prices = latest_market_prices(market_dir)
    warnings: list[str] = []

    symbols = {position.symbol for position in positions} | {order.symbol for order in open_orders}
    symbol_states: dict[str, SymbolPortfolioState] = {}

    for symbol in sorted(symbols):
        quantity = sum(position.quantity for position in positions if position.symbol == symbol)
        price = prices.get(symbol)
        market_value = quantity * price if price is not None else None
        if price is None and quantity:
            warnings.append(f"No latest market price found for {symbol}; market value unavailable.")

        buys = [
            order
            for order in open_orders
            if order.symbol == symbol and order.side == "buy" and order.is_placed_limit
        ]
        sells = [
            order
            for order in open_orders
            if order.symbol == symbol and order.side == "sell" and order.is_placed_limit
        ]
        pending_buy_quantity = sum(order.quantity for order in buys)
        pending_buy_value = sum(order.exposure for order in buys)
        pending_sell_quantity = sum(order.quantity for order in sells)
        pending_sell_value = sum(order.exposure for order in sells)
        post_fill_quantity = quantity + pending_buy_quantity - pending_sell_quantity
        post_fill_value = post_fill_quantity * price if price is not None else None
        allocation_pct = (
            market_value / account_value
            if market_value is not None and account_value is not None and account_value > 0
            else None
        )

        symbol_states[symbol] = SymbolPortfolioState(
            symbol=symbol,
            quantity=quantity,
            latest_price=price,
            market_value=market_value,
            allocation_pct=allocation_pct,
            pending_buy_quantity=pending_buy_quantity,
            pending_buy_value=pending_buy_value,
            pending_sell_quantity=pending_sell_quantity,
            pending_sell_value=pending_sell_value,
            post_fill_quantity=post_fill_quantity,
            post_fill_value=post_fill_value,
        )

    return PortfolioState(
        positions=positions,
        open_orders=open_orders,
        symbols=symbol_states,
        prices=prices,
        account_value=account_value,
        cash=cash,
        warnings=tuple(warnings),
    )


def summarize_portfolio_state(state: PortfolioState) -> str:
    lines = ["== Portfolio state =="]
    lines.append(f"Positions: {len(state.positions)}")
    lines.append(f"Open orders: {len(state.open_orders)}")
    if state.account_value is not None:
        lines.append(f"Account value: ${state.account_value:,.2f}")
    if state.cash is not None:
        lines.append(f"Cash: ${state.cash:,.2f}")
    if not state.symbols:
        lines.append("No local positions or open orders found.")
    else:
        lines.append("")
        lines.append("Symbol state:")
        for symbol in sorted(state.symbols):
            item = state.symbols[symbol]
            price = _money(item.latest_price) if item.latest_price is not None else "unavailable"
            value = _money(item.market_value) if item.market_value is not None else "unavailable"
            allocation = (
                f"{item.allocation_pct:.1%}" if item.allocation_pct is not None else "unknown"
            )
            post_value = (
                _money(item.post_fill_value) if item.post_fill_value is not None else "unavailable"
            )
            lines.append(
                f"- {symbol}: qty {item.quantity:g}, price {price}, value {value}, "
                f"allocation {allocation}, pending buys {item.pending_buy_quantity:g} "
                f"({_money(item.pending_buy_value)}), pending sells {item.pending_sell_quantity:g} "
                f"({_money(item.pending_sell_value)}), post-fill qty {item.post_fill_quantity:g}, "
                f"post-fill value {post_value}"
            )
    if state.warnings:
        lines.append("")
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in state.warnings)
    return "\n".join(lines)


def portfolio_files_exist(
    positions_path: Path = POSITIONS_PATH,
    open_orders_path: Path = OPEN_ORDERS_PATH,
) -> bool:
    return positions_path.exists() or open_orders_path.exists()


def write_position(path: Path, symbol: str, quantity: float) -> None:
    symbol = symbol.strip().upper()
    rows = [dict(row) for row in _read_csv_rows(path, set(), allow_missing=True)]
    found = False
    today = date.today().isoformat()
    for row in rows:
        if row.get("symbol", "").strip().upper() == symbol:
            row.update(
                {
                    "symbol": symbol,
                    "quantity": str(quantity),
                    "notes": row.get("notes", "current_position") or "current_position",
                    "updated_at": today,
                }
            )
            found = True
    if not found:
        rows.append(
            {
                "symbol": symbol,
                "quantity": str(quantity),
                "notes": "current_position",
                "updated_at": today,
            }
        )
    _write_csv(path, POSITION_COLUMNS, rows)


def append_open_order(
    path: Path,
    *,
    side: str,
    symbol: str,
    quantity: float,
    limit_price: float,
    time_in_force: str = "GTC",
    status: str = "placed",
    notes: str = "current_open_order",
) -> None:
    rows = [dict(row) for row in _read_csv_rows(path, set(), allow_missing=True)]
    rows.append(
        {
            "symbol": symbol.strip().upper(),
            "side": side.strip().lower(),
            "type": "limit",
            "quantity": str(quantity),
            "limit_price": f"{limit_price:.2f}",
            "time_in_force": time_in_force,
            "status": status,
            "submitted_at": date.today().isoformat(),
            "notes": notes,
        }
    )
    _write_csv(path, OPEN_ORDER_COLUMNS, rows)


def _read_csv_rows(
    path: Path,
    required: set[str],
    allow_missing: bool = False,
) -> list[dict[str, str]]:
    if not path.exists():
        return [] if allow_missing else []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or ())
        missing = required - columns
        if missing:
            raise ValueError(f"Missing required columns in {path}: {sorted(missing)}")
        return [
            {key: (value or "") for key, value in row.items() if key is not None}
            for row in reader
        ]


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _latest_price_from_csv(path: Path) -> float | None:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return None

    def price_column(row: dict[str, str]) -> str | None:
        normalized = {_normalize_column(key): key for key in row}
        for candidate in ("adj_close", "adjusted_close", "close"):
            if candidate in normalized:
                return normalized[candidate]
        return None

    for row in reversed(rows):
        column = price_column(row)
        if column is None:
            return None
        value = row.get(column, "")
        if value.strip():
            return _parse_float(value, f"{path}: latest close")
    return None


def _normalize_column(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def _parse_float(value: str, context: str) -> float:
    try:
        return float(str(value).replace("$", "").replace(",", "").strip())
    except ValueError as exc:
        raise ValueError(f"Invalid numeric value for {context}: {value!r}") from exc


def _money(value: float | None) -> str:
    if value is None:
        return "unavailable"
    return f"${value:,.2f}"
