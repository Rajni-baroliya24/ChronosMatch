"""Isolated native-call benchmark; never presented as IPC throughput."""
import argparse
from array import array
import gc
import json
from pathlib import Path
import tempfile
from time import perf_counter_ns
from .metrics import distribution, environment
from .protocol import ORDER, pack_order
from .simulator import fields


def benchmark(count=100000, output='lowlatency_output'):
    from ._native import NativeBook
    if not 1 <= count <= 10000000:
        raise ValueError('count must be 1..10,000,000')
    book = NativeBook(count)
    record = bytearray(ORDER.size)
    samples = array('Q')
    fills = 0
    started = perf_counter_ns()
    collections_before = sum(s['collections'] for s in gc.get_stats())
    for index in range(1, count + 1):
        pack_order(record, *fields(index), perf_counter_ns())
        before = perf_counter_ns()
        fills += book.submit(record)
        samples.append(perf_counter_ns() - before)
    elapsed = (perf_counter_ns() - started) / 1e9
    report = {'environment': environment(), 'orders': count, 'trades': fills,
              'latency': distribution(samples), 'orders_per_second': round(count / elapsed, 2),
              'gc_collections_during_python_benchmark': sum(s['collections'] for s in gc.get_stats()) - collections_before,
              'scope': 'Native submit wrapper latency; throughput also includes Python record packing and sample recording. No IPC, network or SQLite.',
              'target_50us_p99_met_in_this_run': distribution(samples)['p99_us'] < 50,
              'hard_latency_guarantee': False}
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix='native-', dir=root))
    report['output_directory'] = str(folder)
    (folder / 'benchmark.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count', type=int, default=100000)
    parser.add_argument('--output', default='lowlatency_output')
    options = parser.parse_args()
    print(json.dumps(benchmark(options.count, options.output), indent=2))
