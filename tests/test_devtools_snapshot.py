from trading_lab.devtools.snapshot import should_include
from pathlib import Path


def test_snapshot_excludes_only_root_data_dir():
    root = Path(".").resolve()

    assert not should_include(root, root / "data" / "secret.csv")
    assert should_include(root, root / "src" / "trading_lab" / "data" / "market.py")
