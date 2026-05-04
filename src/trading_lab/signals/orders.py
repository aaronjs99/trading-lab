from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from trading_lab.config import TradingConfig, load_trading_config
from trading_lab.signals.ladder import LadderOrder
from trading_lab.portfolio.state import OPEN_ORDERS_PATH


@dataclass(frozen=True)
class OrderCheck:
    status: str
    message: str


def load_open_orders(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"Missing open-order CSV: {path}")

    df = pd.read_csv(path)
    required = {"symbol", "side", "quantity", "limit_price"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"Missing columns in {path}: {sorted(missing)}")

    df = df.copy()
    df["symbol"] = df["symbol"].astype(str).str.upper()
    df["side"] = df["side"].astype(str).str.lower()
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["limit_price"] = pd.to_numeric(df["limit_price"], errors="coerce")
    return df.dropna(subset=["quantity", "limit_price"])


def reconcile_tqqq_orders(
    open_orders: pd.DataFrame,
    ladder: list[LadderOrder],
    account_value: float,
    current_price: float,
    config: TradingConfig | None = None,
) -> list[OrderCheck]:
    checks: list[OrderCheck] = []
    traded = (config or load_trading_config()).traded_symbol.upper()

    buys = open_orders[
        (open_orders["symbol"] == traded) & (open_orders["side"] == "buy")
    ].copy()

    pending_buy_value = float((buys["quantity"] * buys["limit_price"]).sum())
    pending_buy_allocation = pending_buy_value / account_value if account_value > 0 else 0.0
    recommended_allocation = sum(order.allocation_fraction for order in ladder)

    if pending_buy_allocation > recommended_allocation * 1.25 and recommended_allocation > 0:
        checks.append(
            OrderCheck(
                status="TOO_AGGRESSIVE",
                message=(
                    f"Pending {traded} buys are {pending_buy_allocation:.1%} of account, "
                    f"but recommendation is {recommended_allocation:.1%}. Reduce/cancel orders."
                ),
            )
        )
    else:
        checks.append(
            OrderCheck(
                status="OK_SIZE",
                message=(
                    f"Pending {traded} buys are {pending_buy_allocation:.1%}; "
                    f"recommended max ladder is {recommended_allocation:.1%}."
                ),
            )
        )

    if not buys.empty:
        highest_buy = float(buys["limit_price"].max())
        first_ladder = ladder[0].limit_price if ladder else None

        if first_ladder is not None and highest_buy > first_ladder * 1.01:
            checks.append(
                OrderCheck(
                    status="BUY_TOO_HIGH",
                    message=(
                        f"Highest pending buy ${highest_buy:.2f} is above first recommended "
                        f"ladder level ${first_ladder:.2f}."
                    ),
                )
            )

    deep_orders = buys[buys["limit_price"] < current_price * 0.88]
    if len(deep_orders) > 0:
        checks.append(
            OrderCheck(
                status="DEEP_ORDERS",
                message=(
                    f"{len(deep_orders)} pending buys are more than 12% below current price. "
                    "These may be low-probability tail orders."
                ),
            )
        )

    return checks


def suggest_tqqq_order_adjustments(
    open_orders: pd.DataFrame,
    ladder: list[LadderOrder],
    account_value: float,
    config: TradingConfig | None = None,
) -> pd.DataFrame:
    """Suggest simple order adjustments against the recommended ladder.

    Output is intentionally conservative:
    - sell orders are kept as-is
    - buy orders above recommended allocation are reduced/cancelled by price priority
    - cheapest buy levels are kept first only if they fit the allocation budget
    """

    if account_value <= 0:
        raise ValueError("account_value must be positive")

    rows: list[dict] = []
    traded = (config or load_trading_config()).traded_symbol.upper()
    recommended_budget = sum(o.allocation_fraction for o in ladder) * account_value

    orders = open_orders.copy()
    orders["notional"] = orders["quantity"] * orders["limit_price"]

    sells = orders[(orders["symbol"] == traded) & (orders["side"] == "sell")]
    for _, order in sells.iterrows():
        rows.append(
            {
                "symbol": order["symbol"],
                "side": order["side"],
                "current_quantity": order["quantity"],
                "limit_price": order["limit_price"],
                "current_notional": order["notional"],
                "suggested_quantity": order["quantity"],
                "suggested_notional": order["notional"],
                "recommendation": "KEEP_SELL_ORDER",
                "reason": "Sell orders reduce risk or take profit; review manually but do not count against buy budget.",
            }
        )

    buys = orders[(orders["symbol"] == traded) & (orders["side"] == "buy")].copy()
    buys = buys.sort_values("limit_price", ascending=False)

    remaining_budget = recommended_budget

    for _, order in buys.iterrows():
        current_qty = float(order["quantity"])
        price = float(order["limit_price"])
        current_notional = float(order["notional"])

        if remaining_budget <= 0:
            suggested_qty = 0.0
            recommendation = "CANCEL_BUY"
            reason = f"Recommended {traded} buy budget is already used."
        else:
            max_qty = int(remaining_budget // price)
            suggested_qty = float(min(current_qty, max_qty))
            suggested_notional_tmp = suggested_qty * price
            remaining_budget -= suggested_notional_tmp

            if suggested_qty == current_qty:
                recommendation = "KEEP_BUY"
                reason = f"Order fits within recommended {traded} buy budget."
            elif suggested_qty > 0:
                recommendation = "REDUCE_BUY"
                reason = f"Reduce quantity to fit recommended {traded} buy budget."
            else:
                recommendation = "CANCEL_BUY"
                reason = f"Order exceeds recommended {traded} buy budget."

        rows.append(
            {
                "symbol": order["symbol"],
                "side": order["side"],
                "current_quantity": current_qty,
                "limit_price": price,
                "current_notional": current_notional,
                "suggested_quantity": suggested_qty,
                "suggested_notional": suggested_qty * price,
                "recommendation": recommendation,
                "reason": reason,
            }
        )

    return pd.DataFrame(rows)


# CLI entrypoint moved from scripts/reconcile_orders.py
def main() -> None:
    from argparse import ArgumentParser
    from dataclasses import asdict, is_dataclass
    from pathlib import Path

    import pandas as pd
    import yaml

    from trading_lab.config import TradingColumns, load_trading_config
    from trading_lab.signals.allocation import display_action, recommend_allocation
    from trading_lab.signals.ladder import build_tqqq_ladder

    parser = ArgumentParser()
    parser.add_argument("--orders")
    parser.add_argument("--account", default="config/account.yaml")
    parser.add_argument("--config", default="config/trading.yaml")
    args = parser.parse_args()

    trading_cfg = load_trading_config(Path(args.config))
    cols = TradingColumns(trading_cfg)

    portfolio_orders_path = OPEN_ORDERS_PATH
    if args.orders:
        orders_path = Path(args.orders)
    elif portfolio_orders_path.exists():
        orders_path = portfolio_orders_path
    else:
        orders_path = Path("data/manual/open_orders.csv")
    account_path = Path(args.account)

    if account_path.exists():
        account_cfg = yaml.safe_load(account_path.read_text(encoding="utf-8")) or {}
    else:
        account_cfg = {}

    account_value = float(
        account_cfg.get("account_value")
        or account_cfg.get("value")
        or trading_cfg.account_value
    )

    if not orders_path.exists():
        orders_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(columns=["symbol", "side", "quantity", "limit_price"]).to_csv(
            orders_path,
            index=False,
        )

    open_orders = pd.read_csv(orders_path)

    selected_signal_path = Path("data/reports/selected_model_latest_signal.csv")
    fallback_signal_path = Path("data/reports/latest_regime_signal.csv")
    market_features_path = Path("data/processed/market/market_features.csv")

    if selected_signal_path.exists():
        latest_signal = pd.read_csv(selected_signal_path).iloc[-1]
        probability = float(latest_signal["probability"])
    else:
        latest_signal = pd.read_csv(fallback_signal_path).iloc[-1]
        probability = float(latest_signal["random_forest_proba"])

    features = pd.read_csv(market_features_path)
    latest_features = features.dropna(subset=[cols.traded_price, cols.benchmark_price]).iloc[-1]

    current_price = float(latest_features[cols.traded_price])

    signal = recommend_allocation(
        rf_probability=probability,
        qqq_uptrend=bool(latest_features[cols.benchmark_uptrend]),
        qqq_dist_ma20=float(latest_features[cols.benchmark_dist_ma_20]),
        qqq_dist_ma50=float(latest_features[cols.benchmark_dist_ma_50]),
        tqqq_drawdown_20d=float(latest_features[cols.traded_drawdown_20d]),
        traded_symbol=trading_cfg.traded_symbol,
        benchmark_symbol=trading_cfg.benchmark_symbol,
        core_symbol=trading_cfg.core_symbol,
    )

    ladder = build_tqqq_ladder(
        current_price=current_price,
        max_tqqq_allocation=signal.max_tqqq_allocation,
        action=signal.action,
    )

    checks = reconcile_tqqq_orders(
        open_orders=open_orders,
        ladder=ladder,
        account_value=account_value,
        current_price=current_price,
        config=trading_cfg,
    )

    print("== Order reconciliation ==")
    print(f"Using orders: {orders_path}")
    print(f"Assumed account value: ${account_value:,.2f}")
    print(f"Signal: {display_action(signal.action, trading_cfg.traded_symbol, trading_cfg.core_symbol)}")
    print(f"{trading_cfg.traded_upper}: ${current_price:.2f}")
    print(f"Max {trading_cfg.traded_upper} allocation: {signal.max_tqqq_allocation:.1%}")
    print()

    if open_orders.empty:
        print("No open orders found.")
    else:
        print("== Open orders ==")
        print(open_orders.to_string(index=False))
        print()

    if ladder:
        print("== Suggested ladder ==")
        for order in ladder:
            print(
                f"- {order.level}: {trading_cfg.traded_upper} "
                f"{order.allocation_fraction:.1%} at ${order.limit_price:.2f} "
                f"({order.reason})"
            )
        print()
    else:
        print("No buy ladder suggested.")
        print()

    print("== Checks ==")
    if not checks:
        print("No issues.")
        return

    for check in checks:
        if is_dataclass(check):
            payload = asdict(check)
            status = payload.get("status") or payload.get("level") or payload.get("name") or "CHECK"
            message = payload.get("message") or payload.get("reason") or str(payload)
            print(f"{status}: {message}")
        else:
            print(str(check))


if __name__ == "__main__":
    main()
