from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

import pandas as pd


@dataclass
class Lot:
    quantity: float
    price: float
    executed_at: object
    basis_status: str = "known"


def calculate_fifo_realized_pnl(trades: pd.DataFrame, allow_unmatched_sells: bool = False) -> pd.DataFrame:
    """Calculate realized P&L using FIFO.

    Supports side values:
    - buy
    - sell
    - starting_lot

    By default, oversells raise ValueError.

    If allow_unmatched_sells=True, an unmatched sell portion is reported with
    basis_status='unknown_unmatched_sell' and realized_pnl=0.0 rather than
    crashing. This is useful for partial historical exports or transfers with
    missing basis.
    """
    columns = [
        "executed_at",
        "symbol",
        "side",
        "quantity",
        "sell_price",
        "buy_price",
        "matched_quantity",
        "proceeds",
        "cost_basis",
        "realized_pnl",
        "basis_status",
        "source_file",
    ]

    if trades.empty:
        return pd.DataFrame(columns=columns)

    lots: dict[str, deque[Lot]] = defaultdict(deque)
    rows: list[dict] = []

    work = trades.copy()
    work["executed_at"] = pd.to_datetime(work["executed_at"], errors="coerce")
    work = work.sort_values(["executed_at", "symbol", "side"]).reset_index(drop=True)

    for _, trade in work.iterrows():
        symbol = str(trade["symbol"]).upper()
        side = str(trade["side"]).lower()
        qty = float(trade["quantity"])
        price = float(trade["price"])
        source_file = trade.get("source_file", "")

        if qty <= 0:
            continue

        if side in {"buy", "starting_lot"}:
            basis_status = "unknown" if side == "starting_lot" and price == 0 else "known"
            lots[symbol].append(
                Lot(
                    quantity=qty,
                    price=price,
                    executed_at=trade["executed_at"],
                    basis_status=basis_status,
                )
            )
            continue

        if side != "sell":
            continue

        remaining = qty

        while remaining > 1e-12 and lots[symbol]:
            lot = lots[symbol][0]
            matched = min(remaining, lot.quantity)

            proceeds = matched * price
            cost_basis = matched * lot.price
            realized_pnl = proceeds - cost_basis

            rows.append(
                {
                    "executed_at": trade["executed_at"],
                    "symbol": symbol,
                    "side": "sell",
                    "quantity": matched,
                    "sell_price": price,
                    "buy_price": lot.price,
                    "matched_quantity": matched,
                    "proceeds": proceeds,
                    "cost_basis": cost_basis,
                    "realized_pnl": realized_pnl,
                    "basis_status": lot.basis_status,
                    "source_file": source_file,
                }
            )

            lot.quantity -= matched
            remaining -= matched

            if lot.quantity <= 1e-12:
                lots[symbol].popleft()

        if remaining > 1e-12:
            if not allow_unmatched_sells:
                raise ValueError(f"Sell quantity exceeds available FIFO lots for {symbol}: {remaining:g}")

            # Partial exports can contain sells for positions opened before the file.
            # Keep the pipeline alive and flag these explicitly.
            proceeds = remaining * price
            rows.append(
                {
                    "executed_at": trade["executed_at"],
                    "symbol": symbol,
                    "side": "sell",
                    "quantity": remaining,
                    "sell_price": price,
                    "buy_price": 0.0,
                    "matched_quantity": remaining,
                    "proceeds": proceeds,
                    "cost_basis": 0.0,
                    "realized_pnl": 0.0,
                    "basis_status": "unknown_unmatched_sell",
                    "source_file": source_file,
                }
            )

    return pd.DataFrame(rows, columns=columns)
