from pathlib import Path

from trading_lab.devtools.clean import clean_local_cruft, iter_local_cruft


def test_clean_local_cruft_removes_pycache(tmp_path: Path):
    pycache = tmp_path / "src" / "__pycache__"
    pycache.mkdir(parents=True)
    (pycache / "x.pyc").write_bytes(b"fake")

    assert pycache in iter_local_cruft(tmp_path)
    removed = clean_local_cruft(tmp_path)

    assert removed >= 1
    assert not pycache.exists()
