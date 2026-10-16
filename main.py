"""Demonstrate binary ingestion and matching."""
from src.engine import ChronosMatchEngine
from src.market_data import encode_order
from src.models import Order

engine = ChronosMatchEngine()
messages = [
    Order(1, 'AAPL', 'SELL', 9900, 10, 1),
    Order(2, 'AAPL', 'BUY', 10000, 6, 2),
    Order(3, 'AAPL', 'BUY', 9900, 4, 3),
]
for message in messages:
    trades = engine.ingest(encode_order(message))
    print('Order:', message)
    for trade in trades:
        print('TRADE:', trade)
print('Final book:', engine.book('AAPL').depth())
