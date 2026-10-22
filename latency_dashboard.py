
import time
import random
from collections import deque
from statistics import mean


class LatencyDashboard:
    def __init__(self, max_samples=100):
        self.latencies = deque(maxlen=max_samples)

    def record_latency(self, latency_ns):
        """Record order-processing latency in nanoseconds."""
        self.latencies.append(latency_ns)

    def get_statistics(self):
        if not self.latencies:
            return {
                "count": 0,
                "average_us": 0.0,
                "max_us": 0.0,
                "min_us": 0.0,
            }

        # Convert nanoseconds to microseconds
        values_us = [value / 1000 for value in self.latencies]

        return {
            "count": len(values_us),
            "average_us": mean(values_us),
            "max_us": max(values_us),
            "min_us": min(values_us),
        }

    def display(self):
        stats = self.get_statistics()

        print("\n" + "=" * 42)
        print("       CHRONOSMATCH LATENCY DASHBOARD")
        print("=" * 42)
        print(f"Orders measured : {stats['count']}")
        print(f"Average latency : {stats['average_us']:.2f} us")
        print(f"Maximum latency : {stats['max_us']:.2f} us")
        print(f"Minimum latency : {stats['min_us']:.2f} us")
        print("=" * 42)


def main():
    dashboard = LatencyDashboard()

    print("Measuring sample order-processing latency...")

    for _ in range(20):
        start = time.perf_counter_ns()

        # Simulate a small order-processing operation
        order = {
            "side": random.choice(["BUY", "SELL"]),
            "price": random.randint(100, 200),
            "quantity": random.randint(1, 10),
        }
        _ = order["price"] * order["quantity"]

        end = time.perf_counter_ns()
        dashboard.record_latency(end - start)

    dashboard.display()


if __name__ == "__main__":
    main()
