
# limit_order_book.pyx

cdef class LimitOrderBook:
    cdef list buy_orders
    cdef list sell_orders

    def __cinit__(self):
        self.buy_orders = []
        self.sell_orders = []

    cpdef add_order(
        self,
        unsigned long long order_id,
        long long price,
        unsigned long long quantity,
        unsigned long long timestamp,
        bint is_buy
    ):
        cdef dict order

        if price <= 0 or quantity == 0:
            raise ValueError("Price and quantity must be positive")

        order = {
            "order_id": order_id,
            "price": price,
            "quantity": quantity,
            "timestamp": timestamp
        }

        if is_buy:
            self.buy_orders.append(order)
            self.buy_orders.sort(
                key=lambda x: (-x["price"], x["timestamp"])
            )
        else:
            self.sell_orders.append(order)
            self.sell_orders.sort(
                key=lambda x: (x["price"], x["timestamp"])
            )

    cpdef list get_bids(self):
        return self.buy_orders.copy()

    cpdef list get_asks(self):
        return self.sell_orders.copy()
