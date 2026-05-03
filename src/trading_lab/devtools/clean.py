from __future__ import annotations

from pathlib import Path
import shutil


CRUFT_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

CRUFT_SUFFIXES = {
    ".pyc",
    ".pyo",
}


def iter_local_cruft(root: Path = Path(".")) -> list[Path]:
    paths: list[Path] = []

    for path in root.rglob("*"):
        if any(part == ".git" for part in path.parts):
            continue
        if path.is_dir() and path.name in CRUFT_DIR_NAMES:
            paths.append(path)
        elif path.is_file() and path.suffix in CRUFT_SUFFIXES:
            paths.append(path)
        elif path.is_dir() and path.name.endswith(".egg-info"):
            paths.append(path)

    return sorted(paths, key=lambda p: len(p.parts), reverse=True)


def clean_local_cruft(root: Path = Path(".")) -> int:
    removed = 0
    for path in iter_local_cruft(root):
        if not path.exists():
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        removed += 1
    return removed


def main() -> None:
    removed = clean_local_cruft()
    print(f"Removed local cruft paths: {removed}")


if __name__ == "__main__":
    main()
