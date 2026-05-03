from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Trade:
    executed_at: datetime
    symbol: str
    side: str
    quantity: float
    price: float
    fees: float = 0.0
    source_file: str | None = None

    @property
    def notional(self) -> float:
        return self.quantity * self.price
