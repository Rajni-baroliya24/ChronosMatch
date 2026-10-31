
def validate_order(side, price, quantity):
    """
    Validate an order before adding it to the order book.

    side: BUY or SELL
    price: Order price
    quantity: Number of shares
    """

    if side not in ("BUY", "SELL"):
        raise ValueError("Order side must be BUY or SELL")

    if not isinstance(price, (int, float)) or isinstance(price, bool):
        raise ValueError("Price must be a number")

    if price <= 0:
        raise ValueError("Price must be greater than zero")

    if not isinstance(quantity, int) or isinstance(quantity, bool):
        raise ValueError("Quantity must be an integer")

    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero")

    return True


if __name__ == "__main__":

    print("Valid Order:", validate_order("BUY", 100, 10))
    print("Valid Order:", validate_order("SELL", 150, 5))

    try:
        validate_order("BUY", 0, 10)
    except ValueError as error:
        print("Invalid Order:", error)
