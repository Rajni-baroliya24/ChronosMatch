"""Gauri tests for Akash's binary market-data processing."""
import pytest
from src.models import Order
from src.market_data import encode_order, decode_order, iter_orders, MESSAGE_SIZE
from src.engine import ChronosMatchEngine

def test_wire_round_trip():
    order = Order(1, 'AAPL', 'BUY', 100, 5, 123)
    data = encode_order(order)
    assert len(data) == MESSAGE_SIZE == 37
    assert decode_order(memoryview(data)) == order

def test_multiple_messages():
    a = Order(1, 'AAPL', 'BUY', 100, 5, 1)
    b = Order(2, 'AAPL', 'SELL', 99, 5, 2)
    assert list(iter_orders(bytearray(encode_order(a) + encode_order(b)))) == [a, b]

def test_truncated_message():
    with pytest.raises(ValueError):
        decode_order(b'\x00')
    with pytest.raises(ValueError):
        list(iter_orders(b'\x00'))

def test_invalid_side_code():
    data = bytearray(encode_order(Order(1, 'AAPL', 'BUY', 100, 5, 1)))
    data[16] = 3
    with pytest.raises(ValueError):
        decode_order(data)

def test_buffer_backed_view():
    data = bytearray(encode_order(Order(1, 'AAPL', 'BUY', 100, 5, 1)))
    view = memoryview(data)
    assert view.obj is data
    assert decode_order(view).order_id == 1

def test_end_to_end_binary_ingestion():
    engine = ChronosMatchEngine()
    a = Order(1, 'AAPL', 'SELL', 99, 5, 1)
    b = Order(2, 'AAPL', 'BUY', 100, 5, 2)
    trades = engine.ingest(encode_order(a) + encode_order(b))
    assert len(trades) == 1
    assert (trades[0].price, trades[0].quantity) == (99, 5)
