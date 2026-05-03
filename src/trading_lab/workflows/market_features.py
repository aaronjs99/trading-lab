from __future__ import annotations

from trading_lab.data.market import update_market_data
from trading_lab.features.market import main as build_market_features_main


def main() -> None:
    print("== Market feature workflow ==")
    update_market_data()
    print()
    build_market_features_main()


if __name__ == "__main__":
    main()
