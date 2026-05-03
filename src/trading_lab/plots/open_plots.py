from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys


DEFAULT_PLOTS = [
    Path("data/reports/plots/tqqq_price_context.png"),
    Path("data/reports/plots/qqq_regime_context.png"),
    Path("data/reports/plots/tqqq_drawdown_context.png"),
    Path("data/reports/plots/model_probability_history.png"),
    Path("data/reports/plots/strategy_equity_curves.png"),
    Path("data/reports/plots/walk_forward_top_strategies.png"),
]


def open_file(path: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


def open_dashboard_plots(paths: list[Path] | None = None) -> None:
    for path in paths or DEFAULT_PLOTS:
        if path.exists():
            print(f"Opening {path}")
            open_file(path)
        else:
            print(f"Missing {path}")


def main() -> None:
    print("== Open dashboard plots ==")
    open_dashboard_plots()


if __name__ == "__main__":
    main()
