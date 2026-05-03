from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from trading_lab.models.dataset import load_market_features, supervised_frame, train_test_split_time


FEATURE_PATH = Path("data/processed/market/market_features.csv")
REPORT_DIR = Path("data/reports")


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    if not FEATURE_PATH.exists():
        raise SystemExit(f"{FEATURE_PATH} not found. Run ./scripts/run_market_feature_pipeline.sh first.")

    df = load_market_features(FEATURE_PATH)
    try:
        work, feature_cols, target_col = supervised_frame(df)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if len(work) < 500:
        raise SystemExit(f"Not enough rows after cleaning: {len(work)}")

    train, test = train_test_split_time(work, test_fraction=0.30)

    X_train = train[feature_cols]
    y_train = train["target"]
    X_test = test[feature_cols]
    y_test = test["target"]

    models = {
        "logistic_regression": Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", LogisticRegression(max_iter=2000, class_weight="balanced")),
            ]
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=300,
            max_depth=5,
            min_samples_leaf=30,
            random_state=42,
            class_weight="balanced_subsample",
        ),
    }

    rows = []
    predictions = test[["date", target_col]].copy()

    for name, model in models.items():
        model.fit(X_train, y_train)

        pred = model.predict(X_test)
        proba = model.predict_proba(X_test)[:, 1]

        acc = accuracy_score(y_test, pred)
        try:
            auc = roc_auc_score(y_test, proba)
        except ValueError:
            auc = float("nan")

        rows.append(
            {
                "model": name,
                "train_rows": len(train),
                "test_rows": len(test),
                "accuracy": acc,
                "roc_auc": auc,
                "positive_rate_train": y_train.mean(),
                "positive_rate_test": y_test.mean(),
                "test_start": test["date"].min(),
                "test_end": test["date"].max(),
            }
        )

        predictions[f"{name}_proba"] = proba
        predictions[f"{name}_pred"] = pred

        print(f"\n== {name} ==")
        print("accuracy:", round(acc, 4))
        print("roc_auc:", round(auc, 4))
        print("confusion matrix:")
        print(confusion_matrix(y_test, pred))
        print("classification report:")
        print(classification_report(y_test, pred, digits=3))

        if name == "random_forest":
            importances = pd.DataFrame(
                {"feature": feature_cols, "importance": model.feature_importances_}
            ).sort_values("importance", ascending=False)
            importances.to_csv(REPORT_DIR / "regime_feature_importance.csv", index=False)
            print("\nTop feature importances:")
            print(importances.head(20).to_string(index=False))

    summary = pd.DataFrame(rows)
    summary.to_csv(REPORT_DIR / "regime_model_summary.csv", index=False)
    predictions.to_csv(REPORT_DIR / "regime_model_predictions.csv", index=False)

    print("\n== Summary ==")
    print(summary.to_string(index=False))
    print("\nWrote:")
    print(REPORT_DIR / "regime_model_summary.csv")
    print(REPORT_DIR / "regime_model_predictions.csv")
    print(REPORT_DIR / "regime_feature_importance.csv")


if __name__ == "__main__":
    main()
