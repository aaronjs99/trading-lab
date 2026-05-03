from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_ingest_robinhood_fails_cleanly_when_no_csvs(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    input_dir = tmp_path / "data" / "raw" / "robinhood"
    output_dir = tmp_path / "data" / "processed"
    input_dir.mkdir(parents=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ingest_robinhood.py"),
            "--input",
            str(input_dir),
            "--output",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode != 0
    assert "No Robinhood CSV files found under" in result.stderr
    assert "Export your Robinhood history CSV and place it there." in result.stderr
    assert "Traceback" not in result.stderr
    assert not output_dir.exists()
