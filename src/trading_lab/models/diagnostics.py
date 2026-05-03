from __future__ import annotations

from pathlib import Path

import pandas as pd

from trading_lab.signals.latest_regime import regime_feature_columns


FEATURE_PATH = Path("data/processed/market/market_features.csv")
OUT_PATH = Path("data/reports/model_diagnostics.md")


def build_model_diagnostics(feature_path: Path = FEATURE_PATH) -> str:
    df = pd.read_csv(feature_path)
    feature_cols = regime_feature_columns(df)
    target_cols = [c for c in df.columns if "hit_up_before_down" in c]

    lines = [
        "# Model Diagnostics",
        "",
        f"- rows: {len(df)}",
        f"- columns: {len(df.columns)}",
        f"- feature_columns: {len(feature_cols)}",
        f"- target_columns: {len(target_cols)}",
        f"- first_date: {df['date'].iloc[0]}",
        f"- last_date: {df['date'].iloc[-1]}",
        "",
        "## Target availability",
    ]

    for col in target_cols:
        valid = int(df[col].notna().sum())
        positive = float((df[col] == 1).mean())
        first_valid = df.loc[df[col].notna(), "date"].iloc[0] if valid else "n/a"
        last_valid = df.loc[df[col].notna(), "date"].iloc[-1] if valid else "n/a"
        lines.append(
            f"- {col}: valid={valid}, positive_rate={positive:.3f}, "
            f"first_valid={first_valid}, last_valid={last_valid}"
        )

    lines.extend(["", "## Feature missingness top 25"])
    missing = df[feature_cols].isna().mean().sort_values(ascending=False).head(25)
    for col, frac in missing.items():
        lines.append(f"- {col}: {frac:.2%}")

    complete_features = int(df.dropna(subset=feature_cols).shape[0])
    lines.extend(
        [
            "",
            "## Complete-row counts",
            f"- complete_feature_rows: {complete_features}",
        ]
    )

    for col in target_cols:
        complete_target_rows = int(df.dropna(subset=feature_cols + [col]).shape[0])
        lines.append(f"- complete_rows_for_{col}: {complete_target_rows}")

    return "\n".join(lines) + "\n"


def write_model_diagnostics(output_path: Path = OUT_PATH) -> str:
    text = build_model_diagnostics()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    return text


def main() -> None:
    print(write_model_diagnostics())


if __name__ == "__main__":
    main()
