from __future__ import annotations

from dataclasses import dataclass

from trading_lab.config.settings import TradingConfig
from trading_lab.config.symbols import SymbolPair


@dataclass(frozen=True)
class TradingColumns:
    config: TradingConfig

    @property
    def pair(self) -> SymbolPair:
        return SymbolPair(
            traded=self.config.traded_symbol,
            benchmark=self.config.benchmark_symbol,
        )

    @property
    def traded_price(self) -> str:
        return self.pair.price_col(self.config.traded_symbol)

    @property
    def benchmark_price(self) -> str:
        return self.pair.price_col(self.config.benchmark_symbol)

    @property
    def benchmark_uptrend(self) -> str:
        return self.pair.uptrend_col(self.config.benchmark_symbol)

    @property
    def benchmark_dist_ma_20(self) -> str:
        return self.pair.distance_to_ma_col(self.config.benchmark_symbol, 20)

    @property
    def benchmark_dist_ma_50(self) -> str:
        return self.pair.distance_to_ma_col(self.config.benchmark_symbol, 50)

    @property
    def traded_drawdown_20d(self) -> str:
        return self.pair.drawdown_col(self.config.traded_symbol, 20)

    def traded_target(self, days: int) -> str:
        return self.pair.hit_up_before_down_col(self.config.traded_symbol, days)

    def traded_forward_return(self, days: int) -> str:
        return self.pair.forward_return_col(self.config.traded_symbol, days)
