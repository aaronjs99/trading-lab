from pathlib import Path

from trading_lab.ingestion import load_robinhood_csv, normalize_robinhood_frame


def test_normalize_robinhood_activity_csv_columns():
    import pandas as pd

    raw = pd.DataFrame(
        [
            {
                "Activity Date": "2026-01-01",
                "Process Date": "2026-01-01",
                "Settle Date": "2026-01-02",
                "Instrument": "TQQQ",
                "Description": "Buy TQQQ",
                "Trans Code": "Buy",
                "Quantity": "1",
                "Price": "$50.00",
                "Amount": "($50.00)",
            },
            {
                "Activity Date": "2026-01-02",
                "Process Date": "2026-01-02",
                "Settle Date": "2026-01-03",
                "Instrument": "TQQQ",
                "Description": "Sell TQQQ",
                "Trans Code": "Sell",
                "Quantity": "1",
                "Price": "$55.00",
                "Amount": "$55.00",
            },
            {
                "Activity Date": "2026-01-03",
                "Process Date": "2026-01-03",
                "Settle Date": "2026-01-04",
                "Instrument": "",
                "Description": "ACAT transfer",
                "Trans Code": "ACATI",
                "Quantity": "",
                "Price": "",
                "Amount": "($40.44)",
            },
        ]
    )

    df = normalize_robinhood_frame(raw, source_file="example.csv")

    assert len(df) == 2
    assert list(df["side"]) == ["buy", "sell"]
    assert set(df["symbol"]) == {"TQQQ"}
    assert list(df["quantity"]) == [1.0, 1.0]
    assert list(df["price"]) == [50.0, 55.0]


def test_load_robinhood_csv_skips_malformed_rows(tmp_path: Path):
    csv_path = tmp_path / "bad_robinhood.csv"
    csv_path.write_text(
        "Activity Date,Process Date,Settle Date,Instrument,Description,Trans Code,Quantity,Price,Amount\n"
        "2026-01-01,2026-01-01,2026-01-02,TQQQ,Buy TQQQ,Buy,1,$50.00,($50.00)\n"
        "2026-01-02,2026-01-02,2026-01-03,TQQQ,Bad,row,with,too,many,fields,extra\n"
        "2026-01-03,2026-01-03,2026-01-04,TQQQ,Sell TQQQ,Sell,1,$55.00,$55.00\n"
    )

    df = load_robinhood_csv(csv_path)

    assert len(df) == 2
    assert set(df["symbol"]) == {"TQQQ"}
