"""Shared order and trade data types. Prices are integer ticks, not floats."""
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True, slots=True)
class Order:
    order_id: int
    symbol: str
    side: Literal["BUY", "SELL"]
    price: int
    quantity: int
    timestamp: int

    def __post_init__(self):
        if not isinstance(self.order_id, int) or isinstance(self.order_id, bool) or self.order_id < 0:
            raise ValueError("order_id must be a nonnegative integer")
        if not isinstance(self.symbol, str) or not self.symbol or len(self.symbol.encode('ascii', errors='ignore')) != len(self.symbol) or len(self.symbol) > 8:
            raise ValueError("symbol must be 1-8 ASCII characters")
        if self.side not in ("BUY", "SELL"):
            raise ValueError("side must be BUY or SELL")
        for name in ("price", "quantity"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if not isinstance(self.timestamp, int) or isinstance(self.timestamp, bool) or self.timestamp < 0:
            raise ValueError("timestamp must be a nonnegative integer")

@dataclass(frozen=True, slots=True)
class Trade:
    buy_order_id: int
    sell_order_id: int
    symbol: str
    price: int
    quantity: int
