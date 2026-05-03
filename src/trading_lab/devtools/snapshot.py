from __future__ import annotations

from datetime import datetime
from pathlib import Path
import zipfile


INCLUDE_ROOTS = [
    "README.md",
    "pyproject.toml",
    "pytest.ini",
    ".gitignore",
    ".gitattributes",
    "config",
    "docs",
    "scripts",
    "src",
    "tests",
]

EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

EXCLUDE_ROOTS = {
    "data",
    "reports",
    "plots",
}


def should_include(root: Path, path: Path) -> bool:
    rel = path.relative_to(root)
    if rel.parts and rel.parts[0] in EXCLUDE_ROOTS:
        return False
    if any(part in EXCLUDE_DIRS for part in rel.parts):
        return False
    if path.suffix in {".pyc", ".pyo"}:
        return False
    if any(part.endswith(".egg-info") for part in rel.parts):
        return False
    return True


def create_debug_snapshot(root: Path = Path("."), output_dir: Path | None = None) -> Path:
    root = root.resolve()
    output_dir = output_dir or Path.home() / "Engineering"
    output = output_dir / f"trading-lab-debug-snapshot-{datetime.now():%Y%m%d_%H%M%S}.zip"

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in INCLUDE_ROOTS:
            path = root / item
            if not path.exists():
                continue
            if path.is_file() and should_include(root, path):
                zf.write(path, path.relative_to(root))
            elif path.is_dir():
                for child in path.rglob("*"):
                    if child.is_file() and should_include(root, child):
                        zf.write(child, child.relative_to(root))

    return output


def main() -> None:
    print(create_debug_snapshot())


if __name__ == "__main__":
    main()
