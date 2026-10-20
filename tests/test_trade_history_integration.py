
from src.engine import ChronosMatchEngine
from src.models import Order


def test_engine_automatically_records_trades():
    engine = ChronosMatchEngine()

    sell_order = Order(
        order_id=1,
        symbol="AAPL",
        side="SELL",
        price=9900,
        quantity=10,
        timestamp=1,
    )

    buy_order = Order(
        order_id=2,
        symbol="AAPL",
        side="BUY",
        price=10000,
        quantity=6,
        timestamp=2,
    )

    # First order rests in the book.
    assert engine.submit(sell_order) == []
    assert engine.trade_history.get_total_trades() == 0

    # Second order matches and automatically records a trade.
    trades = engine.submit(buy_order)

    assert len(trades) == 1
    assert engine.trade_history.get_total_trades() == 1
    assert engine.trade_history.get_total_volume() == 6
    assert engine.trade_history.get_total_traded_value() == 9900 * 6

    recorded_trade = engine.trade_history.get_all_trades()[0]

    assert recorded_trade.buy_order_id == 2
    assert recorded_trade.sell_order_id == 1
    assert recorded_trade.symbol == "AAPL"
