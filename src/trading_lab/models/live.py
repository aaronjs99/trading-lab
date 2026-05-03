from __future__ import annotations

from pathlib import Path

import pandas as pd

from trading_lab.config import TradingConfig, load_trading_config
from trading_lab.models.dataset import (
    latest_feature_row,
    load_market_features,
    primary_prediction_target,
    supervised_frame,
)
from trading_lab.models.selection import select_model_zoo_winner
from trading_lab.models.target_selection import SelectedTarget, selected_prediction_target
from trading_lab.models.zoo import ModelFactory


FEATURE_PATH = Path("data/processed/market/market_features.csv")
OUT_PATH = Path("data/reports/selected_model_latest_signal.csv")


def score_selected_model_latest(
    feature_path: Path = FEATURE_PATH,
    out_path: Path = OUT_PATH,
    config: TradingConfig | None = None,
    selected_target: SelectedTarget | None = None,
) -> pd.DataFrame:
    cfg = config or load_trading_config()
    df = load_market_features(feature_path)
    selected = select_model_zoo_winner()
    target_selection = selected_target or selected_prediction_target(cfg)
    train, feature_cols, target_col = supervised_frame(df, target=target_selection.target, config=cfg)
    latest, _ = latest_feature_row(df, cfg)

    active_model = target_selection.model if target_selection.source == "experiment_report" else selected.model
    active_model = active_model or selected.model
    model = ModelFactory.build(active_model)
    model.fit(train[feature_cols], train["target"])

    probability = float(model.predict_proba(latest[feature_cols])[:, 1][0])

    out = pd.DataFrame(
        [
            {
                "date": latest["date"].iloc[0],
                "model": active_model,
                "probability": probability,
                "train_rows": len(train),
                "target_positive_rate": float(train["target"].mean()),
                "selected_model_profit_factor": selected.mean_profit_factor,
                "selected_model_worst_drawdown": selected.worst_fold_drawdown,
                "configured_target_mode": primary_prediction_target(cfg).mode,
                "active_target_mode": target_selection.target_mode,
                "active_target_col": target_col,
                "target_source": target_selection.source,
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
