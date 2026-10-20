import pytest
from src.engine import ChronosMatchEngine
from src.market_data import encode_order
from src.models import Order


def test_duplicate_in_batch_rejected_before_any_submit():
    engine = ChronosMatchEngine()
    a = Order(1, "AAPL", "BUY", 10000, 1, 1)
    b = Order(1, "MSFT", "BUY", 10000, 1, 2)
    with pytest.raises(ValueError):
        engine.ingest(encode_order(a) + encode_order(b))
    assert engine.books == {}


def test_existing_id_late_in_batch_does_not_partially_apply():
    engine = ChronosMatchEngine()
    a = Order(1, "AAPL", "BUY", 10000, 1, 1)
    b = Order(2, "AAPL", "SELL", 10000, 1, 2)
    engine.submit(a)
    with pytest.raises(ValueError):
        engine.ingest(encode_order(b) + encode_order(a))
    assert engine.book("AAPL").remaining_quantity(1) == 1
    assert 2 not in engine._seen_ids
