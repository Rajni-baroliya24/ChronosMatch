
class OrderBook:
    def __init__(self):
        self.buy_orders = []
        self.sell_orders = []

    def add_buy_order(self, price, quantity):
        self.buy_orders.append({
            "price": price,
            "quantity": quantity
        })
        self.buy_orders.sort(
            key=lambda order: order["price"],
            reverse=True
        )

    def add_sell_order(self, price, quantity):
        self.sell_orders.append({
            "price": price,
            "quantity": quantity
        })
        self.sell_orders.sort(
            key=lambda order: order["price"]
        )

    def match_orders(self):
        while self.buy_orders and self.sell_orders:
            buy = self.buy_orders[0]
            sell = self.sell_orders[0]

            if buy["price"] < sell["price"]:
                break

            traded_quantity = min(
                buy["quantity"],
                sell["quantity"]
            )

            print(
                f"Matched {traded_quantity} units "
                f"at price {sell['price']}"
            )

            buy["quantity"] -= traded_quantity
            sell["quantity"] -= traded_quantity

            if buy["quantity"] == 0:
                self.buy_orders.pop(0)

            if sell["quantity"] == 0:
                self.sell_orders.pop(0)


if __name__ == "__main__":
    book = OrderBook()
    book.add_buy_order(100, 10)
    book.add_sell_order(95, 5)
    book.match_orders()
