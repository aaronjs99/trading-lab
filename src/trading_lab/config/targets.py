from __future__ import annotations

from dataclasses import dataclass

from trading_lab.config.settings import TradingConfig
from trading_lab.config.symbols import SymbolPair


@dataclass(frozen=True)
class PredictionTarget:
    name: str
    symbol: str
    horizon_days: int
    up_threshold: float
    down_threshold: float

    @property
    def label_col(self) -> str:
        return f"{self.symbol.upper()}_{self.horizon_days}d_up{self.up_threshold:.0%}_before_down{abs(self.down_threshold):.0%}"

    @property
    def description(self) -> str:
        return (
            f"{self.symbol.upper()} hits +{self.up_threshold:.0%} before "
            f"-{abs(self.down_threshold):.0%} within {self.horizon_days} trading days"
        )


def default_prediction_targets(config: TradingConfig) -> list[PredictionTarget]:
    traded = config.traded_symbol.upper()
    return [
        PredictionTarget(
            name=f"{traded.lower()}_5d_up5_before_down5",
            symbol=traded,
            horizon_days=5,
            up_threshold=0.05,
            down_threshold=-0.05,
        ),
        PredictionTarget(
            name=f"{traded.lower()}_10d_up8_before_down8",
            symbol=traded,
            horizon_days=10,
            up_threshold=0.08,
            down_threshold=-0.08,
        ),
    ]


def default_symbol_pair(config: TradingConfig) -> SymbolPair:
    return SymbolPair(
        traded=config.traded_symbol,
        benchmark=config.benchmark_symbol,
    )
