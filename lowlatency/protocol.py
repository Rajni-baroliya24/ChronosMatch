"""Version 1 wire records. Prices are integer cents; timestamps are monotonic ns."""
from struct import Struct

SYMBOLS = ("AAPL", "MSFT", "NVDA", "TSLA")
BUY, SELL = 1, 2
# id, symbol index, side, price ticks, quantity, producer timestamp
ORDER = Struct("<QIB3xqQQ")
# trade id, buy id, sell id, symbol index, price, quantity, entered ns, completed ns
TRADE = Struct("<QQQI4xqQQQ")


def pack_order(buffer, order_id, symbol, side, price, quantity, entered_ns):
    """Pack directly into a writable ring slot, without an intermediate bytes record."""
    if not (0 < order_id < 2**63 and 0 <= symbol < len(SYMBOLS)
            and side in (BUY, SELL) and 0 < price < 2**48
            and 0 < quantity < 2**32 and 0 <= entered_ns < 2**63):
        raise ValueError("Invalid native order fields")
    ORDER.pack_into(buffer, 0, order_id, symbol, side, price, quantity, entered_ns)
