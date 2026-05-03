from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from trading_lab.metrics import equity_curve_metrics


@dataclass(frozen=True)
class LadderConfig:
    initial_cash: float = 100_000.0
    base_allocation: float = 0.55
    dip_step: float = 0.05
    ladder_increment: float = 0.08
    max_allocation: float = 0.95
    symbol: str = "TQQQ"
    hedge_symbol: str = "SPY"


def run_tqqq_ladder_backtest(market_data: pd.DataFrame, config: LadderConfig | None = None) -> tuple[pd.DataFrame, dict[str, float]]:
    config = config or LadderConfig()
    prices = (
        market_data.pivot(index="date", columns="symbol", values="close")
        .sort_index()
        .dropna(subset=[config.symbol])
    )
    target = prices[config.symbol]
    rolling_high = target.cummax()
    drawdown = target / rolling_high - 1

    cash = config.initial_cash
    shares = 0.0
    rows: list[dict[str, float | str]] = []

    for date, price in target.items():
        dip_levels = max(0, int(abs(drawdown.loc[date]) / config.dip_step))
        target_allocation = min(
            config.max_allocation,
            config.base_allocation + dip_levels * config.ladder_increment,
        )
        equity = cash + shares * price
        current_allocation = (shares * price / equity) if equity else 0.0
        trade_value = (target_allocation - current_allocation) * equity
        shares_delta = trade_value / price
        shares += shares_delta
        cash -= trade_value
        equity = cash + shares * price
        rows.append(
            {
                "date": date,
                "price": price,
                "drawdown": drawdown.loc[date],
                "target_allocation": target_allocation,
                "shares": shares,
                "cash": cash,
                "equity": equity,
                "trade_value": trade_value,
            }
        )

    results = pd.DataFrame(rows)
    metrics = equity_curve_metrics(results["equity"] if not results.empty else pd.Series(dtype=float))
    return results, metrics
