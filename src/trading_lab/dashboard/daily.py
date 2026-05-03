from __future__ import annotations

from pathlib import Path

import pandas as pd

from trading_lab.config import TradingColumns, load_trading_config
from trading_lab.dashboard.personal_edge import build_personal_edge_summary
from trading_lab.signals.allocation import recommend_allocation
from trading_lab.signals.ladder import build_tqqq_ladder
from trading_lab.strategy.select import select_strategy


SUMMARY_PATH = Path("data/reports/daily_decision_summary.txt")


def _fmt_pct(value: float) -> str:
    return f"{value:.2%}"


def _read_optional_csv(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)


def build_daily_decision_summary() -> str:
    cfg = load_trading_config()
    cols = TradingColumns(cfg)

    features = pd.read_csv("data/processed/market/market_features.csv")
    latest_signal = pd.read_csv("data/reports/latest_regime_signal.csv")
    selected_model_signal = pd.read_csv("data/reports/selected_model_latest_signal.csv")
    multi_signal = _read_optional_csv("data/reports/multi_horizon_signal.csv")
    ranking = _read_optional_csv("data/reports/walk_forward_strategy_ranking.csv")
    model_zoo = _read_optional_csv("data/reports/model_zoo_ranking.csv")
    model_quality_path = Path("data/reports/model_quality_gate.txt")
    model_comparison_path = Path("data/reports/model_comparison.md")

    latest_features = features.dropna(
        subset=[
            cols.traded_price,
            cols.benchmark_price,
            cols.benchmark_uptrend,
            cols.benchmark_dist_ma_20,
            cols.benchmark_dist_ma_50,
            cols.traded_drawdown_20d,
        ]
    ).iloc[-1]

    baseline_pred = latest_signal.iloc[-1]
    selected_pred = selected_model_signal.iloc[-1]

    if ranking.empty:
        raise FileNotFoundError(
            "Missing data/reports/walk_forward_strategy_ranking.csv. "
            "Run scripts/walk_forward_optimize.py before building the daily summary."
        )

    selected_strategy = select_strategy(ranking)

    traded_price = float(latest_features[cols.traded_price])
    benchmark_price = float(latest_features[cols.benchmark_price])
    trend = bool(latest_features[cols.benchmark_uptrend])
    benchmark_ext20 = float(latest_features[cols.benchmark_dist_ma_20])
    benchmark_ext50 = float(latest_features[cols.benchmark_dist_ma_50])
    traded_dd20 = float(latest_features[cols.traded_drawdown_20d])

    baseline_prob = float(baseline_pred["random_forest_proba"])
    selected_model_prob = float(selected_pred["probability"])
    selected_model_name = str(selected_pred["model"])
    configured_target_mode = str(selected_pred.get("configured_target_mode", "barrier_first_hit"))
    active_target_mode = str(selected_pred.get("active_target_mode", configured_target_mode))
    active_target_col = str(selected_pred.get("active_target_col", cols.traded_target(5)))
    target_source = str(selected_pred.get("target_source", "default_config"))

    allocation = recommend_allocation(
        rf_probability=selected_model_prob,
        qqq_uptrend=trend,
        qqq_dist_ma20=benchmark_ext20,
        qqq_dist_ma50=benchmark_ext50,
        tqqq_drawdown_20d=traded_dd20,
    )

    ladder = build_tqqq_ladder(
        current_price=traded_price,
        max_tqqq_allocation=allocation.max_tqqq_allocation,
        action=allocation.action,
    )

    lines: list[str] = [
        f"Date: {latest_features['date']}",
        f"{cfg.benchmark_symbol}: {benchmark_price:.2f}",
        f"{cfg.traded_symbol}: {traded_price:.2f}",
        f"RF probability: {baseline_prob:.3f}",
        f"Selected model probability ({selected_model_name}): {selected_model_prob:.3f}",
        f"Profile: {cfg.active_profile}",
        f"Configured target mode: {configured_target_mode}",
        f"Active target mode: {active_target_mode}",
        f"Active target column: {active_target_col}",
        f"Target source: {target_source}",
        f"{cfg.benchmark_symbol} uptrend 20/50: {trend}",
        f"{cfg.benchmark_symbol} distance from 20DMA: {_fmt_pct(benchmark_ext20)}",
        f"{cfg.benchmark_symbol} distance from 50DMA: {_fmt_pct(benchmark_ext50)}",
        f"{cfg.traded_symbol} drawdown from 20d high: {_fmt_pct(traded_dd20)}",
        f"Suggested action: {allocation.action}",
        f"Max {cfg.traded_symbol} allocation: {allocation.max_tqqq_allocation:.0%}",
        f"Max {cfg.core_symbol} allocation: {allocation.max_spy_allocation:.0%}",
        f"Reason: {allocation.reason}",
    ]

    if not multi_signal.empty:
        lines.extend(["", "Multi-horizon probabilities:"])
        for _, row in multi_signal.iterrows():
            lines.append(
                f"- {row['signal']}: {float(row['probability']):.3f} "
                f"({row['description']})"
            )

    if not model_zoo.empty:
        best_model = model_zoo.iloc[0]
        lines.extend(
            [
                "",
                "Selected prediction model:",
                f"- model: {best_model['model']}",
                f"- trades: {int(best_model['trades'])}",
                f"- mean ROC AUC: {float(best_model['mean_roc_auc']):.3f}",
                f"- mean Brier: {float(best_model['mean_brier']):.3f}",
                f"- mean avg trade return: {float(best_model['mean_avg_return']):.2%}",
                f"- mean win rate: {float(best_model['mean_win_rate']):.2%}",
                f"- mean profit factor: {float(best_model['mean_profit_factor']):.2f}",
                f"- worst fold return: {float(best_model['worst_fold_return']):.2%}",
                f"- worst fold drawdown: {float(best_model['worst_fold_drawdown']):.2%}",
                f"- score: {float(best_model['score']):.3f}",
            ]
        )

    if model_quality_path.exists():
        lines.extend(["", model_quality_path.read_text(encoding="utf-8").strip()])
    if model_comparison_path.exists():
        lines.extend(["", model_comparison_path.read_text(encoding="utf-8").strip()])

    lines.extend(
        [
            "",
            "Selected walk-forward strategy:",
            f"- RF threshold: {selected_strategy.threshold:.2f}",
            f"- take profit: {selected_strategy.take_profit:.0%}",
            f"- stop loss: {selected_strategy.stop_loss:.0%}",
            f"- max hold: {selected_strategy.max_hold} days",
            f"- require trend: {selected_strategy.require_trend}",
            f"- max {cfg.benchmark_symbol} 20DMA extension: "
            f"{'None' if selected_strategy.max_ext20 is None else f'{selected_strategy.max_ext20:.2%}'}",
            f"- mean win rate: {selected_strategy.mean_win_rate:.2%}",
            f"- mean profit factor: {selected_strategy.mean_profit_factor:.2f}",
            f"- worst fold drawdown: {selected_strategy.worst_fold_drawdown:.2%}",
            "",
            "Selected strategy eligible today: "
            f"{'YES' if selected_model_prob >= selected_strategy.threshold and trend else 'NO'}",
        ]
    )

    if selected_model_prob < selected_strategy.threshold:
        lines.append(
            f"- NO: selected model probability {selected_model_prob:.3f} "
            f"< threshold {selected_strategy.threshold:.2f}"
        )
    else:
        lines.append(
            f"- OK: selected model probability {selected_model_prob:.3f} "
            f">= threshold {selected_strategy.threshold:.2f}"
        )

    if selected_strategy.require_trend:
        lines.append(
            f"- {'OK' if trend else 'NO'}: {cfg.benchmark_symbol} trend required "
            f"and current trend is {str(trend).lower()}"
        )

    if selected_strategy.max_ext20 is None:
        lines.append(f"- OK: no {cfg.benchmark_symbol} 20DMA extension cap")
    elif benchmark_ext20 <= selected_strategy.max_ext20:
        lines.append(
            f"- OK: {cfg.benchmark_symbol} 20DMA extension {_fmt_pct(benchmark_ext20)} "
            f"<= cap {_fmt_pct(selected_strategy.max_ext20)}"
        )
    else:
        lines.append(
            f"- NO: {cfg.benchmark_symbol} 20DMA extension {_fmt_pct(benchmark_ext20)} "
            f"> cap {_fmt_pct(selected_strategy.max_ext20)}"
        )

    edge_lines = build_personal_edge_summary()
    if edge_lines and edge_lines[0] == "Personal trading edge:":
        lines.extend([""] + edge_lines)
    else:
        lines.extend(["", "Personal trading edge:"] + edge_lines)

    lines.extend(["", f"Suggested {cfg.traded_symbol} ladder:"])
    if ladder:
        for order in ladder:
            lines.append(
                f"- {order.level}: limit ${order.limit_price:.2f}, "
                f"allocation {order.allocation_fraction:.1%}, {order.reason}"
            )
    else:
        lines.append("- No buy ladder suggested.")

    lines.extend(
        [
            "",
            "Plots:",
            f"- data/reports/plots/{cfg.traded_symbol.lower()}_price_context.png",
            f"- data/reports/plots/{cfg.benchmark_symbol.lower()}_regime_context.png",
            f"- data/reports/plots/{cfg.traded_symbol.lower()}_drawdown_context.png",
            "- data/reports/plots/model_probability_history.png",
            "- data/reports/plots/strategy_equity_curves.png",
            "- data/reports/plots/walk_forward_top_strategies.png",
        ]
    )

    text = "\n".join(lines)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(text + "\n", encoding="utf-8")
    return text


def main() -> None:
    print(build_daily_decision_summary())


if __name__ == "__main__":
    main()
