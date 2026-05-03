from datetime import date, datetime, timedelta
from pathlib import Path
import os
import time

import pandas as pd

from trading_lab.data.market import csv_has_today_data, update_market_data


def _set_mtime(path: Path, day: date) -> None:
    ts = time.mktime(datetime.combine(day, datetime.min.time()).timetuple())
    os.utime(path, (ts, ts))


def test_csv_has_today_data_true_when_file_refreshed_today(tmp_path: Path):
    path = tmp_path / "TQQQ.csv"
    pd.DataFrame({"date": ["2000-01-01"], "close": [1.0]}).to_csv(path, index=False)
    _set_mtime(path, date.today())

    assert csv_has_today_data(path)


def test_csv_has_today_data_false_for_stale_file_mtime(tmp_path: Path):
    path = tmp_path / "TQQQ.csv"
    pd.DataFrame({"date": [date.today().isoformat()], "close": [1.0]}).to_csv(path, index=False)
    _set_mtime(path, date.today() - timedelta(days=2))

    assert not csv_has_today_data(path)


def test_csv_has_today_data_false_for_missing_file(tmp_path: Path):
    assert not csv_has_today_data(tmp_path / "missing.csv")


def test_update_market_data_skips_fresh_files_without_downloading(tmp_path: Path):
    out_dir = tmp_path / "market"
    out_dir.mkdir()
    path = out_dir / "TQQQ.csv"
    pd.DataFrame({"date": ["2000-01-01"], "close": [1.0]}).to_csv(path, index=False)
    _set_mtime(path, date.today())

    result = update_market_data(symbols=["TQQQ"], out_dir=out_dir)

    assert result == {"downloaded": 0, "skipped": 1, "failed": 0}
