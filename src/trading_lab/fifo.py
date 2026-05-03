from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

import pandas as pd


@dataclass
class Lot:
    acquired_at: pd.Timestamp
    quantity: float
    price: float
    fees_remaining: float = 0.0


def calculate_fifo_realized_pnl(trades: pd.DataFrame) -> pd.DataFrame:
    lots: dict[str, deque[Lot]] = defaultdict(deque)
    realized_rows: list[dict[str, object]] = []

    ordered = trades.sort_values(["executed_at", "symbol"]).reset_index(drop=True)
    for _, trade in ordered.iterrows():
        symbol = str(trade["symbol"]).upper()
        side = str(trade["side"]).lower()
        quantity = float(trade["quantity"])
        price = float(trade["price"])
        fees = float(trade.get("fees", 0.0) or 0.0)

        if side == "buy":
            lots[symbol].append(Lot(trade["executed_at"], quantity, price, fees))
            continue

        if side != "sell":
            continue

        remaining = quantity
        sell_fee_remaining = fees
        while remaining > 1e-12 and lots[symbol]:
            lot = lots[symbol][0]
            matched = min(remaining, lot.quantity)
            buy_fee = lot.fees_remaining * (matched / lot.quantity) if lot.quantity else 0.0
            sell_fee = sell_fee_remaining * (matched / remaining) if remaining else 0.0
            proceeds = matched * price
            cost_basis = matched * lot.price
            realized_rows.append(
                {
                    "symbol": symbol,
                    "acquired_at": lot.acquired_at,
                    "sold_at": trade["executed_at"],
                    "quantity": matched,
                    "buy_price": lot.price,
                    "sell_price": price,
                    "cost_basis": cost_basis + buy_fee,
                    "proceeds": proceeds - sell_fee,
                    "realized_pnl": (proceeds - sell_fee) - (cost_basis + buy_fee),
                    "holding_days": (trade["executed_at"] - lot.acquired_at).days,
                }
            )
            lot.quantity -= matched
            lot.fees_remaining -= buy_fee
            remaining -= matched
            sell_fee_remaining -= sell_fee
            if lot.quantity <= 1e-12:
                lots[symbol].popleft()

        if remaining > 1e-9:
            raise ValueError(f"Sell quantity exceeds available FIFO lots for {symbol}: {remaining:g}")

    return pd.DataFrame(
        realized_rows,
        columns=[
            "symbol",
            "acquired_at",
            "sold_at",
            "quantity",
            "buy_price",
            "sell_price",
            "cost_basis",
            "proceeds",
            "realized_pnl",
            "holding_days",
        ],
    )
