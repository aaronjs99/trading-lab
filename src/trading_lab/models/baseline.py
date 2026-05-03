from __future__ import annotations

from pathlib import Path

import pandas as pd


BASELINE_PATH = Path("data/reports/model_baseline_snapshot.csv")


def write_manual_baseline(
    model: str,
    mean_roc_auc: float,
    mean_profit_factor: float,
    mean_win_rate: float,
    worst_fold_drawdown: float,
    output_path: Path = BASELINE_PATH,
) -> pd.DataFrame:
    row = pd.DataFrame(
        [
            {
                "model": model,
                "mean_roc_auc": mean_roc_auc,
                "mean_profit_factor": mean_profit_factor,
                "mean_win_rate": mean_win_rate,
                "worst_fold_drawdown": worst_fold_drawdown,
            }
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    row.to_csv(output_path, index=False)
    return row


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="random_forest_deeper")
    parser.add_argument("--mean-roc-auc", type=float, required=True)
    parser.add_argument("--mean-profit-factor", type=float, required=True)
    parser.add_argument("--mean-win-rate", type=float, required=True)
    parser.add_argument("--worst-fold-drawdown", type=float, required=True)
    args = parser.parse_args()

    out = write_manual_baseline(
        model=args.model,
        mean_roc_auc=args.mean_roc_auc,
        mean_profit_factor=args.mean_profit_factor,
        mean_win_rate=args.mean_win_rate,
        worst_fold_drawdown=args.worst_fold_drawdown,
    )

    print("== Wrote trusted model baseline ==")
    print(out.to_string(index=False))
    print(BASELINE_PATH)


if __name__ == "__main__":
    main()
