"""Gauri module: functional integration tests (pytest)."""
import pytest
from src.models import Order
from src.order_book import OrderBook
from src.engine import ChronosMatchEngine

def order(oid, side, price, qty, symbol='AAPL'):
    return Order(oid, symbol, side, price, qty, oid)

def test_initialization():
    book = OrderBook('AAPL')
    assert book.depth() == {'bids': [], 'asks': []}

def test_no_cross():
    book = OrderBook('AAPL')
    assert book.submit(order(1, 'BUY', 100, 10)) == []
    assert book.submit(order(2, 'SELL', 101, 10)) == []
    assert book.best_bid() == 100 and book.best_ask() == 101

def test_full_fill_at_resting_price():
    book = OrderBook('AAPL')
    book.submit(order(1, 'SELL', 99, 10))
    trades = book.submit(order(2, 'BUY', 100, 10))
    assert len(trades) == 1
    assert (trades[0].price, trades[0].quantity) == (99, 10)
    assert (trades[0].buy_order_id, trades[0].sell_order_id) == (2, 1)
    assert book.depth() == {'bids': [], 'asks': []}

def test_partial_fill():
    book = OrderBook('AAPL')
    book.submit(order(1, 'BUY', 100, 10))
    trades = book.submit(order(2, 'SELL', 100, 6))
    assert [t.quantity for t in trades] == [6]
    assert book.remaining_quantity(1) == 4
    assert book.remaining_quantity(2) == 0

def test_price_priority():
    book = OrderBook('AAPL')
    book.submit(order(1, 'SELL', 102, 5))
    book.submit(order(2, 'SELL', 101, 5))
    trades = book.submit(order(3, 'BUY', 103, 5))
    assert [t.sell_order_id for t in trades] == [2]
    assert book.remaining_quantity(1) == 5

def test_time_priority():
    book = OrderBook('AAPL')
    book.submit(order(1, 'SELL', 100, 5))
    book.submit(order(2, 'SELL', 100, 5))
    trades = book.submit(order(3, 'BUY', 100, 7))
    assert [(t.sell_order_id, t.quantity) for t in trades] == [(1, 5), (2, 2)]
    assert book.remaining_quantity(2) == 3

def test_cancel():
    book = OrderBook('AAPL')
    book.submit(order(1, 'BUY', 100, 5))
    assert book.cancel(1) is True
    assert book.cancel(1) is False
    assert book.remaining_quantity(1) == 0
    assert book.best_bid() is None

def test_invalid_order():
    with pytest.raises(ValueError):
        order(1, 'BUY', 100, 0)
    with pytest.raises(ValueError):
        order(1, 'HOLD', 100, 5)

def test_duplicate_id():
    engine = ChronosMatchEngine()
    engine.submit(order(1, 'BUY', 100, 5))
    with pytest.raises(ValueError):
        engine.submit(order(1, 'SELL', 100, 5))

def test_multi_symbol_isolation():
    engine = ChronosMatchEngine()
    engine.submit(order(1, 'BUY', 100, 5, 'AAPL'))
    assert engine.submit(order(2, 'SELL', 99, 5, 'MSFT')) == []
    assert engine.book('AAPL').remaining_quantity(1) == 5
