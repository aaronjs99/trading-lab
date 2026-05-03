from __future__ import annotations

from pathlib import Path
import re
import warnings
from typing import Iterable

import pandas as pd


NORMALIZED_COLUMNS = [
    "executed_at",
    "symbol",
    "side",
    "quantity",
    "price",
    "amount",
    "fees",
    "source_file",
]


def _canonical_columns(columns: Iterable[str]) -> dict[str, str]:
    """Map normalized lowercase column names to original dataframe column names."""
    out: dict[str, str] = {}
    for col in columns:
        key = re.sub(r"[^a-z0-9]+", "_", str(col).strip().lower()).strip("_")
        out[key] = col
    return out


def _pick_column(mapping: dict[str, str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        key = re.sub(r"[^a-z0-9]+", "_", candidate.strip().lower()).strip("_")
        if key in mapping:
            return mapping[key]
    return None


def _parse_money(value) -> float:
    """Parse Robinhood money fields like '$9.92', '($396.64)', '', or None."""
    if pd.isna(value):
        return 0.0

    text = str(value).strip()
    if not text:
        return 0.0

    neg = False
    if text.startswith("(") and text.endswith(")"):
        neg = True
        text = text[1:-1]

    text = text.replace("$", "").replace(",", "").strip()

    if text.startswith("-"):
        neg = True
        text = text[1:]

    if not text:
        return 0.0

    try:
        num = float(text)
    except ValueError:
        return 0.0

    return -num if neg else num


def _parse_number(value) -> float:
    if pd.isna(value):
        return 0.0
    text = str(value).replace(",", "").strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _normalize_side(value) -> str | None:
    text = str(value).strip().lower()

    # Robinhood exports commonly use Trans Code = Buy / Sell.
    if text in {"buy", "bought"}:
        return "buy"
    if text in {"sell", "sold"}:
        return "sell"

    # ACATI rows with an instrument and quantity represent incoming transferred shares.
    # Treat them as starting-position lots. Cost basis is usually unknown in the export,
    # so price may be zero unless the CSV provides enough information to infer it.
    if text in {"acati", "acat in", "acat_in", "rec", "receive", "received"}:
        return "starting_lot"

    # Ignore other transfers, dividends, interest, fees, etc. for now.
    return None


def normalize_robinhood_frame(df: pd.DataFrame, source_file: str = "") -> pd.DataFrame:
    """Normalize Robinhood CSV export rows into trade rows.

    Expected Robinhood-style columns include:
    Activity Date, Process Date, Settle Date, Instrument, Description,
    Trans Code, Quantity, Price, Amount.

    Non-trade rows are intentionally ignored.
    """
    if df.empty:
        return pd.DataFrame(columns=NORMALIZED_COLUMNS)

    mapping = _canonical_columns(df.columns)

    date_col = _pick_column(mapping, ["Activity Date", "Process Date", "Trade Date", "Date", "Executed At"])
    symbol_col = _pick_column(mapping, ["Instrument", "Symbol", "Ticker"])
    side_col = _pick_column(mapping, ["Trans Code", "Transaction Type", "Side", "Action", "Type"])
    quantity_col = _pick_column(mapping, ["Quantity", "Qty", "Shares"])
    price_col = _pick_column(mapping, ["Price", "Price Per Share", "Average Price", "Average Cost"])
    amount_col = _pick_column(mapping, ["Amount", "Net Amount", "Value"])

    required = {
        "date": date_col,
        "symbol": symbol_col,
        "side": side_col,
        "quantity": quantity_col,
        "price": price_col,
    }
    missing = [name for name, col in required.items() if col is None]
    if missing:
        print(
            "Warning: could not normalize "
            f"{source_file or '<dataframe>'}; missing columns: {missing}. "
            f"Available columns: {list(df.columns)}"
        )
        return pd.DataFrame(columns=NORMALIZED_COLUMNS)

    rows: list[dict] = []

    for _, row in df.iterrows():
        side = _normalize_side(row[side_col])
        if side is None:
            continue

        symbol = str(row[symbol_col]).strip().upper()
        if not symbol or symbol == "NAN":
            continue

        quantity = abs(_parse_number(row[quantity_col]))
        price = abs(_parse_money(row[price_col]))
        amount = _parse_money(row[amount_col]) if amount_col is not None else 0.0

        if quantity <= 0:
            continue

        if price <= 0 and quantity > 0 and amount != 0:
            price = abs(amount) / quantity

        if amount == 0 and quantity > 0 and price > 0:
            gross = quantity * price
            amount = -gross if side in {"buy", "starting_lot"} else gross

        # Starting lots from ACAT transfers are treated like buys for position purposes.
        # If price/amount is missing, basis is unknown and remains zero.
        if side == "starting_lot":
            amount = -abs(amount) if amount != 0 else 0.0

        rows.append(
            {
                "executed_at": pd.to_datetime(row[date_col], errors="coerce"),
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "amount": amount,
                "fees": 0.0,
                "source_file": source_file,
            }
        )

    out = pd.DataFrame(rows, columns=NORMALIZED_COLUMNS)

    if not out.empty:
        out = out.dropna(subset=["executed_at"])
        out = out.sort_values(["executed_at", "symbol", "side"]).reset_index(drop=True)

    return out


def load_robinhood_csv(path: str | Path) -> pd.DataFrame:
    path = Path(path)

    try:
        raw = pd.read_csv(path)
    except pd.errors.ParserError as exc:
        print(
            f"Warning: standard CSV parse failed for {path.name}: {exc}. "
            "Retrying with python engine and skipping malformed rows."
        )
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=pd.errors.ParserWarning)
            raw = pd.read_csv(path, engine="python", on_bad_lines="warn")

    return normalize_robinhood_frame(raw, source_file=path.name)


def load_robinhood_folder(folder: str | Path) -> pd.DataFrame:
    folder = Path(folder)
    csvs = sorted(folder.glob("*.csv"))

    if not csvs:
        return pd.DataFrame(columns=NORMALIZED_COLUMNS)

    frames = [load_robinhood_csv(path) for path in csvs]
    frames = [frame for frame in frames if not frame.empty]

    if not frames:
        return pd.DataFrame(columns=NORMALIZED_COLUMNS)

    return pd.concat(frames, ignore_index=True)
