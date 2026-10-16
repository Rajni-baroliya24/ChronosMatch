
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class TradeRecord:
    buy_order_id: int
    sell_order_id: int
    symbol: str
    price: int
    quantity: int


class TradeHistoryManager:
    def __init__(self):
        self.trades: List[TradeRecord] = []

    def add_trade(self, trade):
        if trade.price <= 0 or trade.quantity <= 0:
            raise ValueError("Invalid trade price or quantity")

        record = TradeRecord(
            buy_order_id=trade.buy_order_id,
            sell_order_id=trade.sell_order_id,
            symbol=trade.symbol,
            price=trade.price,
            quantity=trade.quantity,
        )

        self.trades.append(record)
        return record

    def get_all_trades(self):
        return list(self.trades)

    def get_trades_by_symbol(self, symbol):
        return [
            trade for trade in self.trades
            if trade.symbol == symbol
        ]

    def get_total_trades(self):
        return len(self.trades)

    def get_total_volume(self):
        return sum(trade.quantity for trade in self.trades)

    def get_total_traded_value(self):
        return sum(
            trade.price * trade.quantity
            for trade in self.trades
        )
