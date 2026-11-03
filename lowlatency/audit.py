"""Two-process, sequence-checked mmap audit with an optional Pickle queue baseline."""
import argparse
import json
import multiprocessing as mp
from pathlib import Path
import tempfile
from time import perf_counter_ns
from .metrics import environment
from .protocol import ORDER, pack_order
from .ring import MappedRing
from .simulator import fields


def _send(bus, count, queued, result):
    try:
        result[0] = perf_counter_ns()
        for index in range(1, count + 1):
            if queued:
                bus.put((*fields(index), index * 1000), timeout=30)
            else:
                with bus.write(timeout=30) as slot:
                    pack_order(slot, *fields(index), index * 1000)
    finally:
        if queued:
            bus.close()
            bus.join_thread()
        else:
            bus.close()


def _receive(bus, count, queued, result):
    checksum = 0
    try:
        for expected in range(1, count + 1):
            if queued:
                record = bus.get(timeout=30)
            else:
                with bus.read(timeout=30) as slot:
                    record = ORDER.unpack_from(slot)
            if record != (*fields(expected), expected * 1000):
                raise ValueError(f'Corrupt, missing, duplicate, or out-of-order record at {expected}')
            checksum += record[0]
        result[1], result[2], result[3] = perf_counter_ns(), count, checksum
    finally:
        bus.close()


def _trial(folder, count, capacity, queued):
    context = mp.get_context('spawn')
    bus = context.Queue(maxsize=capacity) if queued else MappedRing(folder / 'audit.mmap', capacity, ORDER.size, context)
    result = context.Array('Q', 4, lock=False)
    consumer = context.Process(target=_receive, args=(bus, count, queued, result))
    producer = context.Process(target=_send, args=(bus, count, queued, result))
    started = []
    try:
        for worker in (consumer, producer):
            worker.start()
            started.append(worker)
        from .pipeline import supervise
        supervise(started, context.Event(), [], None, None, max_seconds=300)
        elapsed = (result[1] - result[0]) / 1e9
        if result[2] != count or result[3] != count * (count + 1) // 2:
            raise ValueError('Audit count/checksum mismatch')
        if not queued and bus.counts() != {'written': count, 'read': count, 'pending': 0}:
            raise ValueError('Audit ring cursors did not reconcile')
        return {'transport': 'multiprocessing.Queue (Pickle)' if queued else 'mmap + semaphore SPSC',
                'orders_verified': count, 'checksum': result[3], 'elapsed_seconds': round(elapsed, 6),
                'orders_per_second': round(count / elapsed, 2),
                'checks': 'Every field compared in sequence; duplicates, gaps and corruption fail the run.'}
    finally:
        for worker in started:
            if worker.is_alive():
                worker.terminate()
        for worker in started:
            worker.join(timeout=5)
        bus.close()
        if queued:
            bus.join_thread()


def run_audit(count=1000000, capacity=4096, output='lowlatency_output', compare_queue=False):
    if not 1 <= count <= 10000000:
        raise ValueError('count must be 1..10,000,000')
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix='audit-', dir=root))
    report = {'environment': environment(), 'capacity': capacity,
              'mmap': _trial(folder, count, capacity, False),
              'scope': 'IPC only; no native matching or persistence.',
              'timestamp_field': 'Deterministic index*1000 for exact payload verification; wall timing uses perf_counter_ns.',
              'serialization': 'No Pickle/JSON order payloads on mmap path. Spawn still serializes process configuration.',
              'output_directory': str(folder)}
    if compare_queue:
        report['queue_baseline'] = _trial(folder, count, capacity, True)
        report['mmap_to_queue_throughput_ratio'] = round(report['mmap']['orders_per_second'] / report['queue_baseline']['orders_per_second'], 3)
    (folder / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count', type=int, default=1000000)
    parser.add_argument('--capacity', type=int, default=4096)
    parser.add_argument('--output', default='lowlatency_output')
    parser.add_argument('--compare-queue', action='store_true')
    args = parser.parse_args()
    print(json.dumps(run_audit(args.count, args.capacity, args.output, args.compare_queue), indent=2))


if __name__ == '__main__':
    main()
