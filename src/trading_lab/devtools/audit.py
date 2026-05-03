from __future__ import annotations

from pathlib import Path

from trading_lab.devtools.clean import clean_local_cruft
import subprocess


ROOT = Path(".").resolve()

GENERATED_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
PRIVATE_TOP_LEVEL = {"data", "reports", "plots"}


def tracked_files() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    return set(result.stdout.splitlines())


def main() -> None:
    tracked = tracked_files()

    clean_local_cruft()
    print("== Repo audit ==")

    print()
    print("== Tracked private/generated files ==")
    bad_tracked = [
        path
        for path in sorted(tracked)
        if path.split("/", 1)[0] in PRIVATE_TOP_LEVEL
        or any(part in GENERATED_DIR_NAMES for part in Path(path).parts)
        or path.endswith((".pyc", ".pyo"))
        or ".egg-info" in Path(path).parts
    ]
    if bad_tracked:
        for path in bad_tracked:
            print(f"BAD_TRACKED {path}")
    else:
        print("OK: no private/generated files tracked")

    print()
    print("== Local generated cruft ==")
    cruft = []
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if ".git" in rel.parts:
            continue
        if any(part in GENERATED_DIR_NAMES for part in rel.parts):
            cruft.append(rel)
        elif path.suffix in {".pyc", ".pyo"}:
            cruft.append(rel)
        elif any(part.endswith(".egg-info") for part in rel.parts):
            cruft.append(rel)

    if cruft:
        for path in sorted(set(cruft)):
            print(f"LOCAL_CRUFT {path}")
    else:
        print("OK: no local generated cruft found")

    print()
    print("== Overlapping legacy modules to review ==")
    candidates = [
        "src/trading_lab/backtest.py",
        "src/trading_lab/market_data.py",
        "src/trading_lab/models.py",
    ]
    leftovers = [candidate for candidate in candidates if Path(candidate).exists()]
    if leftovers:
        for candidate in leftovers:
            print(f"EXISTS {candidate}")
    else:
        print("OK: no known legacy overlap modules found")

    print()
    print("== Script inventory ==")
    scripts = sorted(p for p in Path("scripts").glob("*") if p.is_file())
    print(f"scripts: {len(scripts)}")
    for script in scripts:
        line_count = sum(1 for _ in script.open("r", encoding="utf-8", errors="ignore"))
        kind = "thin" if line_count <= 6 else "logic"
        print(f"{kind.upper()} {script} lines={line_count}")

    print()
    print("== Done ==")


if __name__ == "__main__":
    main()
