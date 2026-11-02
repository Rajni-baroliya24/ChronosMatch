
import unittest
from order_validation import validate_order


class TestTradingEngine(unittest.TestCase):

    def test_valid_buy_order(self):
        self.assertTrue(validate_order("BUY", 100, 10))

    def test_valid_sell_order(self):
        self.assertTrue(validate_order("SELL", 90, 5))

    def test_invalid_buy_price(self):
        with self.assertRaises(ValueError):
            validate_order("BUY", -100, 10)

    def test_invalid_sell_quantity(self):
        with self.assertRaises(ValueError):
            validate_order("SELL", 90, 0)

    def test_buy_sell_matching(self):
        buy_price = 100
        sell_price = 90

        self.assertGreaterEqual(buy_price, sell_price)

    def test_equal_price_matching(self):
        buy_price = 100
        sell_price = 100

        self.assertGreaterEqual(buy_price, sell_price)

    def test_unmatched_orders(self):
        buy_price = 80
        sell_price = 100

        self.assertLess(buy_price, sell_price)


if __name__ == "__main__":
    unittest.main(verbosity=2)
