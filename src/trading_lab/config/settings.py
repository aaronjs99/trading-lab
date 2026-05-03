from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


DEFAULT_CONFIG_PATH = Path("config/trading.yaml")


@dataclass(frozen=True)
class TradingConfig:
    traded_symbol: str = "TQQQ"
    benchmark_symbol: str = "QQQ"
    core_symbol: str = "SPY"
    inverse_symbol: str = "SQQQ"
    account_value: float = 5000.0
    max_traded_allocation_wait: float = 0.05
    max_core_allocation_wait: float = 0.50

    @property
    def traded_upper(self) -> str:
        return self.traded_symbol.upper()

    @property
    def benchmark_upper(self) -> str:
        return self.benchmark_symbol.upper()


def load_trading_config(path: Path = DEFAULT_CONFIG_PATH) -> TradingConfig:
    if not path.exists():
        return TradingConfig()

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    symbols = data.get("symbols", {})
    account = data.get("account", {})
    allocation = data.get("allocation", {})

    return TradingConfig(
        traded_symbol=str(symbols.get("traded", TradingConfig.traded_symbol)),
        benchmark_symbol=str(symbols.get("benchmark", TradingConfig.benchmark_symbol)),
        core_symbol=str(symbols.get("core", TradingConfig.core_symbol)),
        inverse_symbol=str(symbols.get("inverse", TradingConfig.inverse_symbol)),
        account_value=float(account.get("value", TradingConfig.account_value)),
        max_traded_allocation_wait=float(
            allocation.get("max_traded_allocation_wait", TradingConfig.max_traded_allocation_wait)
        ),
        max_core_allocation_wait=float(
            allocation.get("max_core_allocation_wait", TradingConfig.max_core_allocation_wait)
        ),
    )
