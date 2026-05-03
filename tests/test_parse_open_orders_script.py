import subprocess
import sys
from pathlib import Path


def test_parse_open_orders_missing_input_creates_file(tmp_path: Path):
    input_path = tmp_path / "manual" / "upcoming_activity.txt"
    output_path = tmp_path / "manual" / "open_orders.csv"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/parse_open_orders.py",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert input_path.exists()
    assert "Created empty paste file" in result.stdout
