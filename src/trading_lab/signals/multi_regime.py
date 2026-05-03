from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from trading_lab.config import load_trading_config
from trading_lab.config.targets import PredictionTarget, default_prediction_targets
from trading_lab.models.dataset import (
    feature_columns,
    latest_feature_row,
    load_market_features,
    supervised_frame,
    target_column,
)


FEATURE_PATH = Path("data/processed/market/market_features.csv")
OUT_PATH = Path("data/reports/multi_horizon_signal.csv")


def _target_column(target: PredictionTarget) -> str:
    return target_column(target)


def _fit_probability(
    df: pd.DataFrame,
    target_col: str,
    feature_cols: list[str],
) -> tuple[float, int, float]:
    work = df[["date", target_col] + feature_cols].replace([np.inf, -np.inf], np.nan)
    train = work.dropna(subset=[target_col] + feature_cols).copy()
    if train.empty:
        raise ValueError(f"No training rows for target {target_col}")

    train["target"] = (train[target_col] == 1).astype(int)
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
    return proba, len(train), float(train["target"].mean())


def score_multi_horizon(
    feature_path: Path = FEATURE_PATH,
    out_path: Path = OUT_PATH,
    targets: list[PredictionTarget] | None = None,
) -> pd.DataFrame:
    config = load_trading_config()
    targets = targets or default_prediction_targets(config)

    df = load_market_features(feature_path)
    feature_cols = feature_columns(df, config)
    latest_date = df.dropna(subset=feature_cols).iloc[-1]["date"]

    rows = []
    for target in targets:
        target_col = _target_column(target)
        supervised_frame(df, target=target, config=config)
        proba, train_rows, positive_rate = _fit_probability(
            df=df,
            target_col=target_col,
            feature_cols=feature_cols,
        )
        rows.append(
            {
                "date": latest_date,
                "signal": target.name,
                "description": target.description,
                "probability": proba,
                "train_rows": train_rows,
                "target_positive_rate": positive_rate,
            }
        )

    out = pd.DataFrame(rows)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    return out


def main() -> None:
    out = score_multi_horizon()
    print("== Multi-horizon signal ==")
    print(out.to_string(index=False))
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
