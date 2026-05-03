from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from trading_lab.metrics import summarize_realized_by_symbol


def write_edge_report(realized: pd.DataFrame, output_dir: str | Path) -> pd.DataFrame:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = summarize_realized_by_symbol(realized)
    summary.to_csv(output_dir / "symbol_summary.csv", index=False)

    if not realized.empty:
        curve = realized.sort_values("sold_at")["realized_pnl"].cumsum()
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(pd.to_datetime(realized.sort_values("sold_at")["sold_at"]), curve)
        ax.set_title("Cumulative Realized P&L")
        ax.set_xlabel("Date")
        ax.set_ylabel("P&L")
        fig.tight_layout()
        fig.savefig(output_dir / "realized_pnl_curve.png", dpi=150)
        plt.close(fig)

    return summary
