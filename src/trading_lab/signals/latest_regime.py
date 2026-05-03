from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from trading_lab.models.dataset import (
    feature_columns,
    latest_feature_row,
    load_market_features,
    supervised_frame,
)


FEATURE_PATH = Path("data/processed/market/market_features.csv")
OUT_PATH = Path("data/reports/latest_regime_signal.csv")


def regime_feature_columns(df: pd.DataFrame) -> list[str]:
    return feature_columns(df)


def score_latest_regime(
    feature_path: Path = FEATURE_PATH,
    out_path: Path = OUT_PATH,
) -> pd.DataFrame:
    df = load_market_features(feature_path)
    train, feature_cols, _ = supervised_frame(df)
    latest, _ = latest_feature_row(df)

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
