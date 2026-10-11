
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Order:
    """Shared order model for ChronosMatch."""

    order_id: int
    symbol: str
    side: Literal["BUY", "SELL"]
    price: int
    quantity: int
    timestamp: int

    def __post_init__(self):
        if self.side not in ("BUY", "SELL"):
            raise ValueError("Invalid order side")

        if self.price <= 0:
            raise ValueError("Price must be positive")

        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")


if __name__ == "__main__":
    order = Order(
        order_id=1,
        symbol="AAPL",
        side="BUY",
        price=15000,
        quantity=10,
        timestamp=100001,
    )

    print(order)
