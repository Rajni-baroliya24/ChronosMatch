import pytest

from src.models import Order
from src.engine import ChronosMatchEngine


def make_order(order_id, side, price, quantity, timestamp):
    return Order(
        order_id=order_id,
        symbol="AAPL",
        side=side,
        price=price,
        quantity=quantity,
        timestamp=timestamp,
    )


def test_no_match_when_buy_price_is_lower():
    engine = ChronosMatchEngine()

    engine.submit(make_order(1, "BUY", 100, 10, 1))
    trades = engine.submit(make_order(2, "SELL", 110, 5, 2))

    assert trades == []


def test_partial_fill():
    engine = ChronosMatchEngine()

    engine.submit(make_order(1, "SELL", 100, 10, 1))
    trades = engine.submit(make_order(2, "BUY", 100, 4, 2))

    assert len(trades) == 1
    assert trades[0].quantity == 4
    assert trades[0].price == 100


def test_reject_zero_quantity():
    with pytest.raises(ValueError):
        make_order(3, "BUY", 100, 0, 3)


def test_reject_negative_price():
    with pytest.raises(ValueError):
        make_order(4, "SELL", -100, 5, 4)