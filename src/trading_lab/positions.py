from __future__ import annotations

import pandas as pd


def reconstruct_positions(trades: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for symbol, group in trades.sort_values("executed_at").groupby("symbol", sort=True):
        signed_qty = group["quantity"].where(group["side"].str.lower().eq("buy"), -group["quantity"])
        buy_cost = (group.loc[group["side"].str.lower().eq("buy"), "quantity"] * group.loc[group["side"].str.lower().eq("buy"), "price"]).sum()
        buy_qty = group.loc[group["side"].str.lower().eq("buy"), "quantity"].sum()
        sell_proceeds = (group.loc[group["side"].str.lower().eq("sell"), "quantity"] * group.loc[group["side"].str.lower().eq("sell"), "price"]).sum()

        rows.append(
            {
                "symbol": symbol,
                "quantity": signed_qty.sum(),
                "buy_quantity": buy_qty,
                "sell_quantity": group.loc[group["side"].str.lower().eq("sell"), "quantity"].sum(),
                "gross_buy_cost": buy_cost,
                "gross_sell_proceeds": sell_proceeds,
                "average_buy_price": buy_cost / buy_qty if buy_qty else 0.0,
                "last_trade_at": group["executed_at"].max(),
            }
        )

    return pd.DataFrame(rows).sort_values("symbol").reset_index(drop=True)
