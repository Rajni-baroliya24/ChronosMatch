
class OrderMatcher:
    def match_orders(self, buy_orders, sell_orders):
        trades = []

        # Highest buy price first
        buy_orders.sort(
            key=lambda order: order["price"],
            reverse=True
        )

        # Lowest sell price first
        sell_orders.sort(
            key=lambda order: order["price"]
        )

        while buy_orders and sell_orders:
            buy = buy_orders[0]
            sell = sell_orders[0]

            # Stop if prices do not match
            if buy["price"] < sell["price"]:
                break

            quantity = min(
                buy["quantity"],
                sell["quantity"]
            )

            trades.append({
                "price": sell["price"],
                "quantity": quantity
            })

            buy["quantity"] -= quantity
            sell["quantity"] -= quantity

            if buy["quantity"] == 0:
                buy_orders.pop(0)

            if sell["quantity"] == 0:
                sell_orders.pop(0)

        return trades


if __name__ == "__main__":
    buy_orders = [
        {"price": 100, "quantity": 10},
        {"price": 95, "quantity": 5}
    ]

    sell_orders = [
        {"price": 98, "quantity": 6},
        {"price": 100, "quantity": 4}
    ]

    matcher = OrderMatcher()
    trades = matcher.match_orders(
        buy_orders, sell_orders
    )

    print("Matched Trades:")
    for trade in trades:
        print(
            f"Price: {trade['price']}, "
            f"Quantity: {trade['quantity']}"
        )
