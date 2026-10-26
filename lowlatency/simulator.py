"""Deterministic synthetic orders; no exchange credentials or live trading."""
import asyncio
from time import perf_counter_ns
from .protocol import ORDER, pack_order

PATTERN = ((2, 10000, 5), (2, 10001, 5), (2, 10002, 5), (1, 10002, 20), (2, 10002, 5))


def fields(index):
    """Every five orders produce a three-level whale sweep and its final fill."""
    phase = (index - 1) % 5
    symbol = ((index - 1) // 5) % 4
    side, price, quantity = PATTERN[phase]
    return index, symbol, side, price, quantity


async def pace(sent, start, rate):
    if sent % 128 == 0:
        delay = sent / rate - (perf_counter_ns() - start) / 1e9 if rate else 0
        await asyncio.sleep(max(0, delay))


async def produce(ring, count, rate, stop, metrics, source):
    started = perf_counter_ns()
    sent = 0
    if source == 'direct':
        for index in range(1, count + 1):
            if stop.is_set():
                break
            with ring.write() as slot:
                entered = perf_counter_ns()
                pack_order(slot, *fields(index), entered)
            if not sent:
                with metrics.get_lock():
                    metrics[10] = entered
            sent += 1
            await pace(sent, started, rate)
    else:
        from websockets.asyncio.server import serve
        from websockets.asyncio.client import connect

        async def firehose(socket):
            for index in range(1, count + 1):
                if stop.is_set():
                    break
                await socket.send(ORDER.pack(*fields(index), perf_counter_ns()))
                await pace(index, started, rate)

        async with serve(firehose, '127.0.0.1', 0, compression=None) as server:
            port = server.sockets[0].getsockname()[1]
            async with connect(f'ws://127.0.0.1:{port}', compression=None,
                               proxy=None, max_size=ORDER.size) as socket:
                async for payload in socket:
                    if len(payload) != ORDER.size:
                        raise ValueError('Malformed mock feed message')
                    with ring.write() as slot:
                        # WebSocket libraries provide a bytes payload; this network-to-ring
                        # copy is explicit. IPC consumption still uses the mapped slot.
                        slot[:] = payload
                    if not sent:
                        with metrics.get_lock():
                            metrics[10] = ORDER.unpack_from(payload)[-1]
                    sent += 1
    with metrics.get_lock():
        metrics[11] = perf_counter_ns()
        metrics[12] = sent


def producer_worker(ring, count, rate, stop, done, metrics, source):
    try:
        ring.attach()
        asyncio.run(produce(ring, count, rate, stop, metrics, source))
    finally:
        done.set()
        ring.close()
