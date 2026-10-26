
import unittest
import time


def measure_latency(operation, iterations=1000):
    """Measure average operation latency in microseconds."""
    if iterations <= 0:
        raise ValueError("iterations must be positive")

    start = time.perf_counter()

    for _ in range(iterations):
        operation()

    elapsed = time.perf_counter() - start
    return (elapsed / iterations) * 1_000_000


def sample_operation():
    """A simple operation used to validate the benchmark."""
    return 10 + 20


class TestBenchmarkOrderBook(unittest.TestCase):

    def test_latency_is_non_negative(self):
        latency = measure_latency(sample_operation, 100)
        self.assertGreaterEqual(latency, 0)

    def test_invalid_iterations(self):
        with self.assertRaises(ValueError):
            measure_latency(sample_operation, 0)

    def test_operation_runs(self):
        self.assertEqual(sample_operation(), 30)


if __name__ == "__main__":
    unittest.main()
