
import pytest
from src.models import Order


def test_valid_order():
    order = Order(1, "AAPL", "BUY", 15000, 10, 100001)
    assert order.quantity == 10
    assert order.side == "BUY"


def test_invalid_quantity():
    with pytest.raises(ValueError):
        Order(2, "AAPL", "SELL", 15000, 0, 100002)


def test_invalid_side():
    with pytest.raises(ValueError):
        Order(3, "AAPL", "HOLD", 15000, 10, 100003)
