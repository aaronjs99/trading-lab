from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


CANONICAL_COLUMNS = [
    "executed_at",
    "symbol",
    "side",
    "quantity",
    "price",
    "amount",
    "fees",
    "source_file",
]

COLUMN_ALIASES = {
    "executed_at": [
        "executed_at",
        "executed at",
        "date",
        "trade date",
        "transact date",
        "created at",
        "activity date",
        "timestamp",
        "time",
    ],
    "symbol": ["symbol", "ticker", "instrument", "underlying symbol"],
    "side": ["side", "transaction type", "type", "action", "order side"],
    "quantity": ["quantity", "qty", "shares", "amount shares", "share quantity"],
    "price": ["price", "average price", "avg price", "execution price", "price per share"],
    "amount": ["amount", "total", "net amount", "net cash", "value", "notional"],
    "fees": ["fees", "fee", "commission", "regulatory fees", "sec fee"],
}

BUY_WORDS = {"buy", "bought", "purchase", "debit", "assigned"}
SELL_WORDS = {"sell", "sold", "sale", "credit", "expired", "exercised"}


def _clean_column_name(name: object) -> str:
    return str(name).strip().lower().replace("_", " ")


def _find_column(columns: Iterable[str], aliases: list[str]) -> str | None:
    normalized = {_clean_column_name(col): col for col in columns}
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]
    for clean_name, original in normalized.items():
        if any(alias in clean_name for alias in aliases):
            return original
    return None


def _normalize_side(value: object) -> str | None:
    text = str(value).strip().lower()
    if not text or text == "nan":
        return None
    if any(word in text for word in BUY_WORDS):
        return "buy"
    if any(word in text for word in SELL_WORDS):
        return "sell"
    return text


def _to_number(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("(", "-", regex=False)
        .str.replace(")", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="coerce")


def inspect_csv_columns(path: str | Path) -> list[str]:
    return list(pd.read_csv(path, nrows=0).columns)


def normalize_robinhood_frame(frame: pd.DataFrame, source_file: str | None = None) -> pd.DataFrame:
    """Normalize a Robinhood-like CSV into canonical trade rows.

    The function intentionally accepts broad column names because brokerage exports change over
    time and account activity exports often differ from order-history exports.
    """

    output = pd.DataFrame(index=frame.index)
    for canonical, aliases in COLUMN_ALIASES.items():
        column = _find_column(frame.columns, aliases)
        output[canonical] = frame[column] if column is not None else np.nan

    output["executed_at"] = pd.to_datetime(output["executed_at"], errors="coerce", utc=True)
    output["symbol"] = output["symbol"].astype(str).str.strip().str.upper()
    output["side"] = output["side"].map(_normalize_side)
    output["quantity"] = _to_number(output["quantity"]).abs()
    output["price"] = _to_number(output["price"])
    output["amount"] = _to_number(output["amount"])
    output["fees"] = _to_number(output["fees"]).fillna(0.0)
    output["source_file"] = source_file

    missing_price = output["price"].isna() & output["amount"].notna() & output["quantity"].gt(0)
    output.loc[missing_price, "price"] = (output.loc[missing_price, "amount"].abs() / output.loc[missing_price, "quantity"])

    inferred_amount = output["amount"].isna() & output["price"].notna() & output["quantity"].notna()
    output.loc[inferred_amount, "amount"] = output.loc[inferred_amount, "price"] * output.loc[inferred_amount, "quantity"]

    valid = (
        output["executed_at"].notna()
        & output["symbol"].ne("")
        & output["symbol"].ne("NAN")
        & output["side"].isin(["buy", "sell"])
        & output["quantity"].gt(0)
        & output["price"].notna()
    )

    return (
        output.loc[valid, CANONICAL_COLUMNS]
        .sort_values(["executed_at", "symbol", "side"])
        .reset_index(drop=True)
    )


def load_robinhood_csv(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    return normalize_robinhood_frame(pd.read_csv(path), source_file=path.name)


def load_robinhood_folder(folder: str | Path) -> pd.DataFrame:
    folder = Path(folder)
    frames = [load_robinhood_csv(path) for path in sorted(folder.glob("*.csv"))]
    if not frames:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)
    return pd.concat(frames, ignore_index=True).sort_values("executed_at").reset_index(drop=True)
