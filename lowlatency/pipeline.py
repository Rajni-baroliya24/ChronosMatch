"""Three-process supervisor: ingestion, native matching, and ledger writer."""
from array import array
import argparse
import gc
import json
import multiprocessing as mp
from pathlib import Path
import sqlite3
import tempfile
from time import monotonic, perf_counter_ns, sleep

from .metrics import distribution, environment, save_samples
from .protocol import ORDER, TRADE
from .ring import MappedRing
from .simulator import producer_worker


def matching_worker(orders, trades, count, producer_done, matcher_done, ready, metrics, output):
    from ._native import NativeBook
    engine = NativeBook(count)
    native_samples, pipeline_samples = array('Q'), array('Q')
    processed = fills = whales = gc_collections = completed = 0

    def gc_observer(phase, info):
        nonlocal gc_collections
        if phase == 'stop':
            gc_collections += 1

    gc.callbacks.append(gc_observer)
    try:
        orders.attach()
        trades.attach()
        ready.set()
        while True:
            try:
                with orders.read(timeout=.1) as slot:
                    entered = ORDER.unpack_from(slot)[-1]
                    start = perf_counter_ns()
                    emitted = engine.submit(slot)
                    completed = perf_counter_ns()
            except TimeoutError:
                if producer_done.is_set() and orders.counts()['pending'] == 0:
                    break
                continue
            native_samples.append(completed - start)
            pipeline_samples.append(completed - entered)
            processed += 1
            fills += emitted
            if engine.levels_cleared >= 3:
                whales += 1
            for index in range(emitted):
                with trades.write() as target:
                    engine.write_trade(index, target, completed)
            if processed % 256 == 0:
                bid, bqty, ask, aqty = engine.quote(0)
                with metrics.get_lock():
                    metrics[0:10] = [processed, fills, metrics[2], completed - entered,
                                     completed - start, whales, bid, bqty, ask, aqty]
        bid, bqty, ask, aqty = engine.quote(0)
        with metrics.get_lock():
            metrics[0], metrics[1], metrics[5] = processed, fills, whales
            metrics[6:10] = [bid, bqty, ask, aqty]
            metrics[13] = completed
        report = {'orders_processed': processed, 'trades_emitted': fills, 'whale_sweeps': whales,
                  'native_call_latency': distribution(native_samples),
                  'enqueue_to_native_return_latency': distribution(pipeline_samples),
                  'matcher_process_gc_collections': gc_collections,
                  'gc_scope': 'Whole Python worker; native loops do not use Python objects. GC is not disabled.',
                  'latency_scope': 'Producer stamp to native return; excludes trade publication and SQLite commit.',
                  'whale_definition': 'Incoming order completely clearing at least three price levels.'}
        Path(output, 'matcher.json').write_text(json.dumps(report, indent=2) + '\n')
        save_samples(Path(output, 'latency_samples.u64'), native_samples, pipeline_samples)
    finally:
        gc.callbacks.remove(gc_observer)
        matcher_done.set()
        orders.close()
        trades.close()


def ledger_worker(trades, matcher_done, ready, metrics, database):
    connection = sqlite3.connect(database)
    try:
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('PRAGMA synchronous=FULL')
        connection.execute('''CREATE TABLE trades (
            trade_id INTEGER PRIMARY KEY, buy_order_id INTEGER, sell_order_id INTEGER,
            symbol INTEGER, price_ticks INTEGER, quantity INTEGER,
            entered_ns INTEGER, matched_ns INTEGER)''')
        connection.commit()
        trades.attach()
        ready.set()
        batch = []
        last_commit = monotonic()
        while True:
            try:
                with trades.read(timeout=.05) as slot:
                    batch.append(TRADE.unpack_from(slot))
            except TimeoutError:
                if matcher_done.is_set() and trades.counts()['pending'] == 0:
                    break
            if batch and (len(batch) >= 256 or monotonic() - last_commit >= .1):
                connection.executemany('INSERT INTO trades VALUES (?,?,?,?,?,?,?,?)', batch)
                connection.commit()
                with metrics.get_lock():
                    metrics[2] += len(batch)
                batch.clear()
                last_commit = monotonic()
        if batch:
            connection.executemany('INSERT INTO trades VALUES (?,?,?,?,?,?,?,?)', batch)
            connection.commit()
            with metrics.get_lock():
                metrics[2] += len(batch)
        connection.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    finally:
        connection.close()
        trades.close()


def supervise(processes, stop, metrics, orders, trades, terminal=False, max_seconds=300):
    started = monotonic()
    interrupted = False
    def poll(screen=None):
        nonlocal interrupted
        if screen is not None:
            screen.nodelay(True)
        history = []
        while any(p.is_alive() for p in processes):
            failed = [p for p in processes if p.exitcode not in (None, 0)]
            if failed:
                raise RuntimeError('Worker failed: ' + ', '.join(p.name for p in failed))
            if monotonic() - started > max_seconds:
                raise TimeoutError('Run exceeded the supervisor deadline')
            if screen is not None:
                from .terminal import draw
                draw(screen, metrics, orders, trades, history)
                if screen.getch() in (ord('q'), ord('Q')):
                    stop.set()
                    interrupted = True
            sleep(.1)
    try:
        if terminal:
            import curses
            curses.wrapper(poll)
        else:
            poll()
    except KeyboardInterrupt:
        stop.set()
        interrupted = True
        for process in processes:
            process.join(timeout=5)
        if any(p.is_alive() for p in processes):
            raise RuntimeError('Shutdown deadline exceeded')
    for process in processes:
        process.join()
        if process.exitcode != 0:
            raise RuntimeError(f'{process.name} exited with code {process.exitcode}')
    return interrupted


def run(count=10000, rate=100000, capacity=4096, output='lowlatency_output', source='direct', terminal=False):
    if not 1 <= count <= 10000000 or rate < 0:
        raise ValueError('orders must be 1..10,000,000; rate must be nonnegative')
    # Fail before starting children if the extension hasn't been built.
    from ._native import NativeBook
    if source not in ('direct', 'websocket'):
        raise ValueError('source must be direct or websocket')
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix='run-', dir=root))
    context = mp.get_context('spawn')
    stop, producer_done, matcher_done = context.Event(), context.Event(), context.Event()
    native_ready, ledger_ready = context.Event(), context.Event()
    metrics = context.Array('Q', 14)
    orders = MappedRing(folder / 'orders.mmap', capacity, ORDER.size, context)
    trades = MappedRing(folder / 'trades.mmap', capacity, TRADE.size, context)
    workers = [
        context.Process(name='ledger', target=ledger_worker,
                        args=(trades, matcher_done, ledger_ready, metrics, str(folder / 'ledger.sqlite3'))),
        context.Process(name='matcher', target=matching_worker,
                        args=(orders, trades, count, producer_done, matcher_done, native_ready, metrics, str(folder))),
        context.Process(name='simulator', target=producer_worker,
                        args=(orders, count, rate, stop, producer_done, metrics, source)),
    ]
    started = []
    try:
        for worker in workers[:2]:
            worker.start()
            started.append(worker)
        for event in (ledger_ready, native_ready):
            deadline = monotonic() + 30
            while not event.wait(.1):
                if any(p.exitcode not in (None, 0) for p in started) or monotonic() > deadline:
                    raise RuntimeError('Worker initialization failed or timed out')
        workers[2].start()
        started.append(workers[2])
        interrupted = supervise(workers, stop, metrics, orders, trades, terminal)
        if not interrupted and metrics[12] != count:
            raise RuntimeError('Producer finished before delivering the requested order count')
        report = json.loads((folder / 'matcher.json').read_text())
        with sqlite3.connect(folder / 'ledger.sqlite3') as connection:
            ledger_count = connection.execute('SELECT COUNT(*) FROM trades').fetchone()[0]
        if ledger_count != report['trades_emitted'] or report['orders_processed'] != metrics[12]:
            raise RuntimeError('Pipeline reconciliation failed')
        elapsed = (metrics[13] - metrics[10]) / 1e9 if metrics[10] and metrics[13] else 0
        report.update({'environment': environment(), 'source': source, 'requested_orders': count,
                       'target_rate': rate, 'interrupted': interrupted,
                       'ledger_trades': ledger_count, 'ring_capacity': capacity,
                       'orders_ring': orders.counts(), 'trades_ring': trades.counts(),
                       'pipeline_orders_per_second': round(report['orders_processed'] / elapsed, 2) if elapsed > 0 else 0,
                       'throughput_scope': 'First producer timestamp to final native return; excludes startup and final SQLite drain.',
                       'output_directory': str(folder),
                       'limitations': ['Synchronized SPSC rings; not lock-free.',
                         'Python wrappers, OS scheduling and native allocations remain.',
                         'No durable ingress journal or crash replay of resting native orders.',
                         'Performance targets are measurements to evaluate, not guarantees.']})
        report['targets_observed_in_this_run'] = {
            'pipeline_at_least_100k_orders_per_second': report['pipeline_orders_per_second'] >= 100000,
            'native_p99_below_50us': report['native_call_latency']['p99_us'] is not None and report['native_call_latency']['p99_us'] < 50,
            'all_native_calls_below_50us': report['native_call_latency']['max_us'] is not None and report['native_call_latency']['max_us'] < 50,
            'enqueue_to_native_return_p99_below_1ms': report['enqueue_to_native_return_latency']['p99_us'] is not None and report['enqueue_to_native_return_latency']['p99_us'] < 1000,
        }
        (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        return report
    finally:
        stop.set()
        for worker in started:
            if worker.is_alive():
                worker.terminate()
        for worker in started:
            worker.join(timeout=5)
        orders.close()
        trades.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--orders', type=int, default=10000)
    parser.add_argument('--rate', type=int, default=100000, help='Target orders/s; 0 means unpaced')
    parser.add_argument('--capacity', type=int, default=4096)
    parser.add_argument('--source', choices=['direct', 'websocket'], default='direct')
    parser.add_argument('--output', default='lowlatency_output')
    parser.add_argument('--terminal', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.orders, args.rate, args.capacity, args.output, args.source, args.terminal), indent=2))
    except ImportError as error:
        raise SystemExit('Install requirements-lowlatency.txt and build the extension first: ' + str(error))


if __name__ == '__main__':
    main()
