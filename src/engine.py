"""Route binary market data to order books and record executed trades."""

from .market_data import iter_orders
from .models import Order, Trade
from .order_book import OrderBook
from .trade_history import TradeHistoryManager


class ChronosMatchEngine:
    def __init__(self):
        self.books: dict[str, OrderBook] = {}
        self._seen_ids: set[int] = set()
        self.trade_history = TradeHistoryManager()

    def submit(self, order: Order) -> list[Trade]:
        if order.order_id in self._seen_ids:
            raise ValueError("duplicate global order id")

        self._seen_ids.add(order.order_id)
        book = self.books.setdefault(
            order.symbol, OrderBook(order.symbol)
        )

        trades = book.submit(order)

        for trade in trades:
            self.trade_history.add_trade(trade)

        return trades

    def ingest(
        self, buffer: bytes | bytearray | memoryview
    ) -> list[Trade]:
        # Decode before changing any order books.
        orders = list(iter_orders(buffer))

        # Reject duplicate IDs before submitting any batch orders.
        batch_ids: set[int] = set()
        for order in orders:
            if (
                order.order_id in self._seen_ids
                or order.order_id in batch_ids
            ):
                raise ValueError("duplicate global order id")

            batch_ids.add(order.order_id)

        trades: list[Trade] = []
        for order in orders:
            trades.extend(self.submit(order))

        return trades

    def book(self, symbol: str) -> OrderBook:
        return self.books.setdefault(symbol, OrderBook(symbol))