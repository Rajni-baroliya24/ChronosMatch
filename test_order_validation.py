
import unittest
from order_validation import validate_order


class TestOrderValidation(unittest.TestCase):

    def test_valid_buy_order(self):
        self.assertTrue(validate_order("BUY", 100, 10))

    def test_valid_sell_order(self):
        self.assertTrue(validate_order("SELL", 150, 5))

    def test_invalid_side(self):
        with self.assertRaises(ValueError):
            validate_order("HOLD", 100, 10)

    def test_zero_price(self):
        with self.assertRaises(ValueError):
            validate_order("BUY", 0, 10)

    def test_negative_price(self):
        with self.assertRaises(ValueError):
            validate_order("BUY", -100, 10)

    def test_zero_quantity(self):
        with self.assertRaises(ValueError):
            validate_order("SELL", 100, 0)

    def test_negative_quantity(self):
        with self.assertRaises(ValueError):
            validate_order("SELL", 100, -5)

    def test_decimal_quantity(self):
        with self.assertRaises(ValueError):
            validate_order("BUY", 100, 2.5)


if __name__ == "__main__":
    unittest.main()
