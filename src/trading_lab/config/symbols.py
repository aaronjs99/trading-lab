from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SymbolPair:
    traded: str
    benchmark: str

    @property
    def traded_upper(self) -> str:
        return self.traded.upper()

    @property
    def benchmark_upper(self) -> str:
        return self.benchmark.upper()

    def price_col(self, symbol: str) -> str:
        return symbol.upper()

    def return_col(self, symbol: str, days: int) -> str:
        return f"{symbol.upper()}_ret_{days}d"

    def moving_average_col(self, symbol: str, days: int) -> str:
        return f"{symbol.upper()}_ma_{days}"

    def distance_to_ma_col(self, symbol: str, days: int) -> str:
        return f"{symbol.upper()}_dist_ma_{days}"

    def volatility_col(self, symbol: str, days: int) -> str:
        return f"{symbol.upper()}_vol_{days}d"

    def drawdown_col(self, symbol: str, days: int) -> str:
        return f"{symbol.upper()}_drawdown_from_{days}d_high"

    def forward_return_col(self, symbol: str, days: int) -> str:
        return f"{symbol.upper()}_fwd_ret_{days}d"

    def hit_up_before_down_col(self, symbol: str, days: int) -> str:
        return f"{symbol.upper()}_hit_up_before_down_{days}d"

    def uptrend_col(self, symbol: str, fast: int = 20, slow: int = 50) -> str:
        return f"{symbol.upper()}_uptrend_{fast}_{slow}"
