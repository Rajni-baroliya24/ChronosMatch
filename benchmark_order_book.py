
import time
import statistics


def benchmark(operation, iterations=10000):
    latencies = []

    for _ in range(iterations):
        start = time.perf_counter_ns()
        operation()
        end = time.perf_counter_ns()

        latencies.append(end - start)

    average_ns = statistics.mean(latencies)
    max_ns = max(latencies)
    min_ns = min(latencies)
    throughput = 1_000_000_000 / average_ns if average_ns else 0

    print("\n--- Order Book Benchmark ---")
    print(f"Iterations       : {iterations}")
    print(f"Average latency  : {average_ns / 1000:.2f} us")
    print(f"Minimum latency  : {min_ns / 1000:.2f} us")
    print(f"Maximum latency  : {max_ns / 1000:.2f} us")
    print(f"Approx throughput: {throughput:.2f} ops/sec")


def sample_operation():
    # Replace this with a real order-book operation
    buy_price = 105
    sell_price = 100
    return buy_price >= sell_price


if __name__ == "__main__":
    benchmark(sample_operation)
