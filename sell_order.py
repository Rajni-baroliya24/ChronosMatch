
class SellOrderManager:
    def __init__(self):
        self.sell_orders = []

    def add_sell_order(self, price, quantity):
        if price <= 0 or quantity <= 0:
            raise ValueError(
                "Price and quantity must be positive"
            )

        order = {
            "price": price,
            "quantity": quantity
        }

        # Add the sell order
        self.sell_orders.append(order)

        # Lowest sell price comes first
        self.sell_orders.sort(
            key=lambda order: order["price"]
        )

    def display_sell_orders(self):
        print("Sell Orders:")

        for order in self.sell_orders:
            print(
                f"Price: {order['price']}, "
                f"Quantity: {order['quantity']}"
            )


if __name__ == "__main__":
    manager = SellOrderManager()

    manager.add_sell_order(110, 8)
    manager.add_sell_order(90, 5)
    manager.add_sell_order(100, 10)

    manager.display_sell_orders()
