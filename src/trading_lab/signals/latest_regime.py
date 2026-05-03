from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier


FEATURE_PATH = Path("data/processed/market/market_features.csv")
OUT_PATH = Path("data/reports/latest_regime_signal.csv")


def regime_feature_columns(df: pd.DataFrame) -> list[str]:
    return [
        c
        for c in df.columns
        if (
            c.startswith("SPY_ret_")
            or c.startswith("QQQ_ret_")
            or c.startswith("TQQQ_ret_")
            or c.startswith("SPY_dist_ma_")
            or c.startswith("QQQ_dist_ma_")
            or c.startswith("TQQQ_dist_ma_")
            or c.startswith("SPY_vol_")
            or c.startswith("QQQ_vol_")
            or c.startswith("TQQQ_vol_")
            or c.startswith("SPY_drawdown_")
            or c.startswith("QQQ_drawdown_")
            or c.startswith("TQQQ_drawdown_")
            or c == "QQQ_uptrend_20_50"
        )
    ]


def score_latest_regime(
    feature_path: Path = FEATURE_PATH,
    out_path: Path = OUT_PATH,
) -> pd.DataFrame:
    df = pd.read_csv(feature_path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    target_col = "TQQQ_hit_up_before_down_5d"
    feature_cols = regime_feature_columns(df)

    work = df[["date", target_col] + feature_cols].copy()
    work = work.replace([np.inf, -np.inf], np.nan)

    train = work.dropna(subset=[target_col] + feature_cols).copy()
    train["target"] = (train[target_col] == 1).astype(int)

    latest = df.dropna(subset=feature_cols).iloc[-1:].copy()

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=5,
        min_samples_leaf=30,
        random_state=42,
        class_weight="balanced_subsample",
    )
    model.fit(train[feature_cols], train["target"])

    proba = float(model.predict_proba(latest[feature_cols])[:, 1][0])

    out = pd.DataFrame(
        [
            {
                "date": latest["date"].iloc[0],
                "random_forest_proba": proba,
                "train_rows": len(train),
                "target_positive_rate": float(train["target"].mean()),
            }
        ]
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    return out


def main() -> None:
    out = score_latest_regime()
    print("== Latest regime signal ==")
    print(out.to_string(index=False))
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
