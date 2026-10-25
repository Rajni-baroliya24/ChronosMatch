
import unittest
from latency_dashboard import LatencyDashboard


class TestLatencyDashboard(unittest.TestCase):

    def setUp(self):
        self.dashboard = LatencyDashboard()

    def test_initial_statistics(self):
        stats = self.dashboard.get_statistics()

        self.assertEqual(stats["count"], 0)
        self.assertEqual(stats["average_us"], 0.0)
        self.assertEqual(stats["max_us"], 0.0)
        self.assertEqual(stats["min_us"], 0.0)

    def test_record_single_latency(self):
        self.dashboard.record_latency(5000)

        stats = self.dashboard.get_statistics()

        self.assertEqual(stats["count"], 1)
        self.assertAlmostEqual(stats["average_us"], 5.0)
        self.assertAlmostEqual(stats["max_us"], 5.0)
        self.assertAlmostEqual(stats["min_us"], 5.0)

    def test_multiple_latencies(self):
        self.dashboard.record_latency(1000)
        self.dashboard.record_latency(3000)
        self.dashboard.record_latency(5000)

        stats = self.dashboard.get_statistics()

        self.assertEqual(stats["count"], 3)
        self.assertAlmostEqual(stats["average_us"], 3.0)
        self.assertAlmostEqual(stats["max_us"], 5.0)
        self.assertAlmostEqual(stats["min_us"], 1.0)

    def test_display(self):
        self.dashboard.record_latency(2000)
        self.dashboard.display()


if __name__ == "__main__":
    unittest.main()
