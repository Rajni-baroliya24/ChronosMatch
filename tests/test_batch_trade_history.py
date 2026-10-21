"""Regression checks for rejected binary batches and recorded trade history."""

import pytest

from src.engine import ChronosMatchEngine
from src.market_data import encode_order
from src.models import Order


@pytest.mark.parametrize(
    "conflicting_id",
    [
        pytest.param(12, id="duplicate-within-batch"),
        pytest.param(11, id="id-already-used"),
    ],
)
def test_rejected_batch_preserves_book_history_and_retry(conflicting_id):
    engine = ChronosMatchEngine()

    # Record one real trade and leave three SELL units available to match.
    engine.submit(Order(10, "AAPL", "SELL", 10000, 5, 1))
    engine.submit(Order(11, "AAPL", "BUY", 10000, 2, 2))
    assert engine.trade_history.get_total_trades() == 1
    assert engine.trade_history.get_total_volume() == 2

    before_depth = engine.book("AAPL").depth()
    before_history = list(engine.trade_history.get_all_trades())

    # The first order would execute a trade if applied before validation.
    first = Order(12, "AAPL", "BUY", 10000, 1, 3)
    conflicting = Order(conflicting_id, "MSFT", "BUY", 10000, 1, 4)
    payload = memoryview(encode_order(first) + encode_order(conflicting))

    with pytest.raises(ValueError, match="duplicate"):
        engine.ingest(payload)

    # Rejection must preserve the existing book, history and global ID state.
    assert set(engine.books) == {"AAPL"}
    assert engine.book("AAPL").depth() == before_depth
    assert engine.book("AAPL").remaining_quantity(10) == 3
    assert engine.trade_history.get_all_trades() == before_history
    assert engine.trade_history.get_total_trades() == 1
    assert engine.trade_history.get_total_volume() == 2

    # A rejected batch must not consume the first order's ID.
    trades = engine.submit(first)
    assert len(trades) == 1
    assert trades[0].quantity == 1
    assert engine.book("AAPL").remaining_quantity(10) == 2
    assert engine.trade_history.get_total_trades() == 2
    assert engine.trade_history.get_total_volume() == 3
