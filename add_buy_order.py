
class BuyOrderManager:
    def __init__(self):
        self.buy_orders = []

    def add_buy_order(self, price, quantity):
        if price <= 0 or quantity <= 0:
            raise ValueError(
                "Price and quantity must be positive"
            )

        self.buy_orders.append({
            "price": price,
            "quantity": quantity
        })

        self.buy_orders.sort(
            key=lambda order: order["price"],
            reverse=True
        )


if __name__ == "__main__":
    manager = BuyOrderManager()

    manager.add_buy_order(100, 10)
    manager.add_buy_order(120, 5)
    manager.add_buy_order(110, 8)

    print(manager.buy_orders)
