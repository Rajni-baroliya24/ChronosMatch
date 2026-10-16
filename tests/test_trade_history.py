
import pytest

from src.models import Trade
from src.trade_history import TradeHistoryManager


def sample_trade(symbol="AAPL", price=100, quantity=5):
    return Trade(
        buy_order_id=1,
        sell_order_id=2,
        symbol=symbol,
        price=price,
        quantity=quantity,
    )


def test_add_trade():
    history = TradeHistoryManager()
    history.add_trade(sample_trade())

    assert history.get_total_trades() == 1


def test_total_volume():
    history = TradeHistoryManager()
    history.add_trade(sample_trade(quantity=5))
    history.add_trade(sample_trade(quantity=10))

    assert history.get_total_volume() == 15


def test_filter_by_symbol():
    history = TradeHistoryManager()
    history.add_trade(sample_trade("AAPL"))
    history.add_trade(sample_trade("GOOG"))

    result = history.get_trades_by_symbol("AAPL")

    assert len(result) == 1
    assert result[0].symbol == "AAPL"


def test_total_traded_value():
    history = TradeHistoryManager()
    history.add_trade(sample_trade(price=100, quantity=5))
    history.add_trade(sample_trade(price=200, quantity=3))

    assert history.get_total_traded_value() == 1100
