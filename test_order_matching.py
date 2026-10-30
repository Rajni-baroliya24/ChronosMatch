
import unittest


def can_match(buy_price, sell_price):
    """Return True when a buyer is willing to pay the seller's price."""
    return buy_price >= sell_price


class TestOrderMatching(unittest.TestCase):

    def test_matching_prices(self):
        self.assertTrue(can_match(100, 90))

    def test_equal_prices(self):
        self.assertTrue(can_match(100, 100))

    def test_non_matching_prices(self):
        self.assertFalse(can_match(90, 100))

    def test_higher_buy_price(self):
        self.assertTrue(can_match(150, 120))

    def test_lower_buy_price(self):
        self.assertFalse(can_match(80, 120))


if __name__ == "__main__":
    unittest.main()
