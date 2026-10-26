import random
from time import perf_counter_ns
import pytest
from lowlatency.protocol import ORDER, TRADE, SYMBOLS, pack_order
from src.models import Order
from src.order_book import OrderBook


def submit(book, oid, side, price, quantity, symbol=0):
    source = bytearray(ORDER.size)
    pack_order(source, oid, symbol, side, price, quantity, perf_counter_ns())
    emitted = book.submit(source)
    records = []
    for index in range(emitted):
        target = bytearray(TRADE.size)
        book.write_trade(index, target, perf_counter_ns())
        records.append(TRADE.unpack_from(target))
    return records


def test_fifo_partial_fills_and_whale_levels(native_book):
    book = native_book(10)
    submit(book, 1, 2, 10000, 3)
    submit(book, 2, 2, 10000, 4)
    submit(book, 3, 2, 10001, 5)
    submit(book, 4, 2, 10002, 6)
    trades = submit(book, 5, 1, 10002, 14)
    assert [(t[2], t[4], t[5]) for t in trades] == [(1, 10000, 3), (2, 10000, 4), (3, 10001, 5), (4, 10002, 2)]
    assert book.remaining(4) == 4
    assert book.levels_cleared == 2
    assert book.quote() == (0, 0, 10002, 4)
    assert all(t[7] >= t[6] for t in trades)


def test_three_fills_at_one_price_are_not_three_levels(native_book):
    book = native_book(10)
    for oid in range(1, 4):
        submit(book, oid, 2, 10000, 1)
    assert len(submit(book, 4, 1, 10000, 3)) == 3
    assert book.levels_cleared == 1


@pytest.mark.parametrize('seed', [1, 42, 103])
def test_random_workload_matches_original_python_order_book(native_book, seed):
    rng = random.Random(seed)
    native = native_book(1200)
    reference = [OrderBook(symbol) for symbol in SYMBOLS]
    order_symbols = {}
    next_trade = 1
    for oid in range(1, 1001):
        symbol, side = rng.randrange(4), rng.choice([1, 2])
        price, quantity = rng.randrange(9995, 10006), rng.randrange(1, 20)
        order_symbols[oid] = symbol
        expected = reference[symbol].submit(Order(oid, SYMBOLS[symbol], 'BUY' if side == 1 else 'SELL', price, quantity, oid))
        actual = submit(native, oid, side, price, quantity, symbol)
        assert [(t[1], t[2], t[3], t[4], t[5]) for t in actual] == [
            (t.buy_order_id, t.sell_order_id, symbol, t.price, t.quantity) for t in expected]
        assert [t[0] for t in actual] == list(range(next_trade, next_trade + len(expected)))
        next_trade += len(expected)
    for oid, symbol in order_symbols.items():
        assert native.remaining(oid) == reference[symbol].remaining_quantity(oid)
    for symbol, book in enumerate(reference):
        depth = book.depth()
        bid = depth['bids'][0] if depth['bids'] else (0, 0)
        ask = depth['asks'][0] if depth['asks'] else (0, 0)
        assert native.quote(symbol) == (*bid, *ask)


def test_duplicate_and_capacity_errors_preserve_book(native_book):
    book = native_book(2)
    submit(book, 1, 1, 10000, 3)
    with pytest.raises(ValueError, match='Duplicate'):
        submit(book, 1, 2, 10000, 3)
    assert book.quote() == (10000, 3, 0, 0)
    submit(book, 2, 1, 10000, 2)
    with pytest.raises(ValueError, match='capacity'):
        submit(book, 3, 2, 10000, 5)
    assert book.order_count == 2
    assert book.quote() == (10000, 5, 0, 0)


@pytest.mark.parametrize('fields', [
    (0, 0, 1, 100, 1, 1), (1, 4, 1, 100, 1, 1),
    (1, 0, 0, 100, 1, 1), (1, 0, 3, 100, 1, 1),
    (1, 0, 1, -100, 1, 1), (1, 0, 1, 2**48, 1, 1),
    (1, 0, 1, 100, 0, 1), (1, 0, 1, 100, 2**32, 1),
    (2**63, 0, 1, 100, 1, 1),
])
def test_native_validates_raw_bytes_before_mutation(native_book, fields):
    book = native_book(2)
    with pytest.raises(ValueError):
        book.submit(ORDER.pack(*fields))
    assert book.order_count == 0
    assert book.quote() == (0, 0, 0, 0)


@pytest.mark.parametrize('length', [0, 39, 41])
def test_invalid_record_length(native_book, length):
    with pytest.raises(ValueError, match='40 bytes'):
        native_book(2).submit(bytes(length))
