from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from trading_lab.config.profiles import (
    DEFAULT_PROFILE,
    active_profile,
    bool_env_override,
    profile_from_env,
    profile_uses_experiment_target,
)


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
    use_experiment_selected_target: bool = False
    selected_target_mode: str | None = None
    selected_target_name: str | None = None
    active_profile: str = "default"

    @property
    def traded_upper(self) -> str:
        return self.traded_symbol.upper()

    @property
    def benchmark_upper(self) -> str:
        return self.benchmark_symbol.upper()


def load_trading_config(path: Path = DEFAULT_CONFIG_PATH) -> TradingConfig:
    profile = active_profile()
    selected_profile = profile_from_env()
    override = bool_env_override()
    if not path.exists():
        return TradingConfig(
            use_experiment_selected_target=(
                override
                if override is not None
                else profile_uses_experiment_target(selected_profile or DEFAULT_PROFILE)
            ),
            active_profile=profile,
        )

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    symbols = data.get("symbols", {})
    account = data.get("account", {})
    allocation = data.get("allocation", {})
    modeling = data.get("modeling", {})
    file_use_experiment = bool(
        modeling.get(
            "use_experiment_selected_target",
            TradingConfig.use_experiment_selected_target,
        )
    )
    use_experiment = (
        override
        if override is not None
        else profile_uses_experiment_target(selected_profile)
        if selected_profile is not None
        else file_use_experiment
    )

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
        use_experiment_selected_target=use_experiment,
        selected_target_mode=modeling.get("selected_target_mode"),
        selected_target_name=modeling.get("selected_target_name"),
        active_profile=profile,
    )
