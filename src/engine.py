
"""Integration module: route binary market-data messages to symbol order books."""

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
        # IDs are globally unique across symbols in this reference engine.
        if order.order_id in self._seen_ids:
            raise ValueError("duplicate global order id")

        self._seen_ids.add(order.order_id)
        book = self.books.setdefault(order.symbol, OrderBook(order.symbol))

        # Match orders using the existing order-book logic.
        trades = book.submit(order)

        # Automatically record every executed trade.
        for trade in trades:
            self.trade_history.add_trade(trade)

        return trades

    def ingest(self, buffer: bytes | bytearray | memoryview) -> list[Trade]:
        # Decode first to reject malformed streams before submitting orders.
        orders = list(iter_orders(buffer))
        trades: list[Trade] = []

        for order in orders:
            trades.extend(self.submit(order))

        return trades

    def book(self, symbol: str) -> OrderBook:
        return self.books.setdefault(symbol, OrderBook(symbol))
