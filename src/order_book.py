"""Varsha module: deterministic single-symbol price-time-priority limit order book.

Orders are processed in arrival order (submit call order). Timestamps are
metadata; caller must submit messages in intended arrival sequence.
"""
from collections import deque
from dataclasses import dataclass
from .models import Order, Trade

@dataclass(slots=True)
class _Resting:
    order: Order
    remaining: int

class OrderBook:
    def __init__(self, symbol: str):
        if not symbol:
            raise ValueError("symbol is required")
        self.symbol = symbol
        self.bids: dict[int, deque[_Resting]] = {}
        self.asks: dict[int, deque[_Resting]] = {}
        self._active: dict[int, _Resting] = {}
        self._seen_ids: set[int] = set()

    def submit(self, order: Order) -> list[Trade]:
        if order.symbol != self.symbol:
            raise ValueError("order symbol does not match book")
        if order.order_id in self._seen_ids:
            raise ValueError("duplicate order id")
        self._seen_ids.add(order.order_id)
        incoming = _Resting(order, order.quantity)
        trades: list[Trade] = []
        opposite = self.asks if order.side == "BUY" else self.bids
        own = self.bids if order.side == "BUY" else self.asks
        while incoming.remaining and opposite:
            best_price = min(opposite) if order.side == "BUY" else max(opposite)
            crosses = order.price >= best_price if order.side == "BUY" else order.price <= best_price
            if not crosses:
                break
            queue = opposite[best_price]
            resting = queue[0]
            qty = min(incoming.remaining, resting.remaining)
            if order.side == "BUY":
                buy_id, sell_id = order.order_id, resting.order.order_id
            else:
                buy_id, sell_id = resting.order.order_id, order.order_id
            trades.append(Trade(buy_id, sell_id, self.symbol, best_price, qty))
            incoming.remaining -= qty
            resting.remaining -= qty
            if resting.remaining == 0:
                queue.popleft()
                del self._active[resting.order.order_id]
                if not queue:
                    del opposite[best_price]
        if incoming.remaining:
            own.setdefault(order.price, deque()).append(incoming)
            self._active[order.order_id] = incoming
        return trades

    def cancel(self, order_id: int) -> bool:
        resting = self._active.pop(order_id, None)
        if resting is None:
            return False
        levels = self.bids if resting.order.side == "BUY" else self.asks
        queue = levels[resting.order.price]
        queue.remove(resting)
        if not queue:
            del levels[resting.order.price]
        return True

    def remaining_quantity(self, order_id: int) -> int:
        resting = self._active.get(order_id)
        return resting.remaining if resting else 0

    def best_bid(self) -> int | None:
        return max(self.bids) if self.bids else None

    def best_ask(self) -> int | None:
        return min(self.asks) if self.asks else None

    def depth(self) -> dict[str, list[tuple[int, int]]]:
        return {
            "bids": [(p, sum(x.remaining for x in self.bids[p])) for p in sorted(self.bids, reverse=True)],
            "asks": [(p, sum(x.remaining for x in self.asks[p])) for p in sorted(self.asks)],
        }
