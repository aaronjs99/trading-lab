from __future__ import annotations

from pathlib import Path
import re

import pandas as pd


ORDER_START_RE = re.compile(r"ProShares UltraPro QQQ limit (buy|sell)", re.IGNORECASE)


def _parse_float(text: str) -> float:
    return float(text.replace("$", "").replace(",", "").strip())


def _split_order_blocks(lines: list[str]) -> list[list[str]]:
    starts = [i for i, line in enumerate(lines) if ORDER_START_RE.search(line)]
    blocks: list[list[str]] = []

    for idx, start in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else len(lines)
        blocks.append(lines[start:end])

    return blocks


def parse_robinhood_upcoming_activity(text: str) -> pd.DataFrame:
    """Parse pasted Robinhood upcoming-activity text into open-order rows."""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    rows: list[dict] = []

    for block in _split_order_blocks(lines):
        if not block:
            continue

        match = ORDER_START_RE.search(block[0])
        if not match:
            continue

        side = match.group(1).lower()
        symbol = "TQQQ"
        limit_price = None
        quantity = None

        for i, line in enumerate(block):
            low = line.lower()

            if low == "symbol" and i + 1 < len(block):
                symbol = block[i + 1].upper()

            elif low == "limit price" and i + 1 < len(block):
                limit_price = _parse_float(block[i + 1])

            elif low == "entered quantity" and i + 1 < len(block):
                quantity = _parse_float(block[i + 1])

        if limit_price is not None and quantity is not None:
            rows.append(
                {
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "limit_price": limit_price,
                }
            )

    return pd.DataFrame(rows, columns=["symbol", "side", "quantity", "limit_price"])


def parse_file(input_path: Path, output_path: Path) -> pd.DataFrame:
    text = input_path.read_text(encoding="utf-8")
    df = parse_robinhood_upcoming_activity(text)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return df


def main() -> None:
    from argparse import ArgumentParser
    from pathlib import Path

    parser = ArgumentParser()
    parser.add_argument("--input", default="data/manual/upcoming_activity.txt")
    parser.add_argument("--output", default="data/manual/open_orders.csv")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        input_path.parent.mkdir(parents=True, exist_ok=True)
        input_path.write_text("", encoding="utf-8")
        print(f"No input file found. Created empty paste file: {input_path}")
        print("Paste Robinhood Upcoming activity into that file, save it, then rerun this command.")
        return

    df = parse_file(input_path, output_path)
    print(f"Wrote {len(df)} open orders to {output_path}")

    if df.empty:
        print("No open orders parsed.")
    else:
        print(df.to_string(index=False))


if __name__ == "__main__":
    main()
