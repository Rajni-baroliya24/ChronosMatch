
import unittest


class TestLimitOrderBook(unittest.TestCase):

    def test_order_book_initialization(self):
        """Check that the order book can be initialized."""
        from limit_order_book import LimitOrderBook

        order_book = LimitOrderBook()
        self.assertIsNotNone(order_book)

    def test_order_book_has_expected_methods(self):
        """Check that the order book provides order-management methods."""
        from limit_order_book import LimitOrderBook

        order_book = LimitOrderBook()

        self.assertTrue(
            any(
                callable(getattr(order_book, name, None))
                for name in ("add_order", "add_buy_order", "add_sell_order")
            ),
            "No recognized order-addition method was found."
        )


if __name__ == "__main__":
    unittest.main()
