"""Gauri benchmark: actual submission, not a dummy loop.
Run from project root: python -m benchmarks.benchmark
"""
from statistics import median
from time import perf_counter_ns
from src.models import Order
from src.order_book import OrderBook

def benchmark(count=5000):
    book = OrderBook('AAPL')
    durations = []
    wall_start = perf_counter_ns()
    for i in range(count):
        order = Order(i + 1, 'AAPL', 'BUY', 100, 1, i)
        start = perf_counter_ns()
        book.submit(order)
        durations.append(perf_counter_ns() - start)
    elapsed = (perf_counter_ns() - wall_start) / 1e9
    sorted_ns = sorted(durations)
    print(f'Orders: {count}')
    print(f'Wall-clock throughput: {count / elapsed:,.0f} orders/s')
    print(f'Median submit: {median(durations) / 1000:.2f} us')
    print(f'P95 submit: {sorted_ns[int(.95 * (count - 1))] / 1000:.2f} us')
    print(f'P99 submit: {sorted_ns[int(.99 * (count - 1))] / 1000:.2f} us')
    print('Scenario: same-price resting BUY insertions; no matching or network I/O.')
    print('This is a Python reference benchmark, not an HFT latency guarantee.')

if __name__ == '__main__':
    benchmark()
