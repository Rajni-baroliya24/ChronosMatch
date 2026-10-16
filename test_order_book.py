import unittest
from order_book import OrderBook


class TestOrderBook(unittest.TestCase):

    def setUp(self):
        self.book = OrderBook()

    def test_add_buy_order(self):
        self.book.add_buy_order(100, 5)
        self.assertEqual(len(self.book.buy_orders), 1)

    def test_add_sell_order(self):
        self.book.add_sell_order(105, 3)
        self.assertEqual(len(self.book.sell_orders), 1)


if __name__ == "__main__":
    unittest.main()
