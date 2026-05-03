from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from trading_lab.models.selection import select_model_zoo_winner
from trading_lab.models.zoo import ModelFactory
from trading_lab.signals.latest_regime import regime_feature_columns


FEATURE_PATH = Path("data/processed/market/market_features.csv")
OUT_PATH = Path("data/reports/selected_model_latest_signal.csv")


def score_selected_model_latest(
    feature_path: Path = FEATURE_PATH,
    out_path: Path = OUT_PATH,
) -> pd.DataFrame:
    df = pd.read_csv(feature_path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    selected = select_model_zoo_winner()
    target_col = "TQQQ_hit_up_before_down_5d"
    feature_cols = regime_feature_columns(df)

    work = df[["date", target_col] + feature_cols].replace([np.inf, -np.inf], np.nan)
    train = work.dropna(subset=[target_col] + feature_cols).copy()
    train["target"] = (train[target_col] == 1).astype(int)

    latest = df.dropna(subset=feature_cols).iloc[-1:].copy()

    model = ModelFactory.build(selected.model)
    model.fit(train[feature_cols], train["target"])

    probability = float(model.predict_proba(latest[feature_cols])[:, 1][0])

    out = pd.DataFrame(
        [
            {
                "date": latest["date"].iloc[0],
                "model": selected.model,
                "probability": probability,
                "train_rows": len(train),
                "target_positive_rate": float(train["target"].mean()),
                "selected_model_profit_factor": selected.mean_profit_factor,
                "selected_model_worst_drawdown": selected.worst_fold_drawdown,
            }
        ]
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    return out


def main() -> None:
    out = score_selected_model_latest()
    print("== Selected model latest signal ==")
    print(out.to_string(index=False))
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
