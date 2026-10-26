# Native low-latency pipeline

This is an additive experimental path. The existing Flask website, Python engine,
trade-history manager and database remain separate and unchanged.

## Components

1. `lowlatency.simulator`: deterministic synthetic limit orders, either packed
   directly by an asyncio producer or received through a local mock WebSocket feed.
2. `lowlatency.ring`: fixed-size mmap slots shared by spawned processes. Separate
   free/ready semaphores prevent overwrite and premature reads. This is SPSC and
   synchronized, not lock-free. Processes must share handles from one supervisor.
3. `lowlatency._native`: Cython `.pyx` matcher compiled as C++. Orders and temporary
   executions use preallocated C-struct arrays accessed through pointers. Price
   levels use native C++ maps/deques; duplicate IDs use a native hash map. Native
   containers can allocate memory. The matching loops release the GIL and have
   no normal-path Python-object operations. Python wrappers still hold the GIL.
4. `lowlatency.pipeline`: starts ingestion, matching and SQLite-writer processes.
5. `lowlatency.terminal`: curses monitor in the supervisor, outside matching.
6. `lowlatency.audit`: separate two-process audit and optional Queue/Pickle baseline.

## Interface and ownership

`protocol.ORDER` is a 40-byte little-endian record, version 1:

| Offset | Field | Encoding |
| --- | --- | --- |
| 0 | Order ID | unsigned 64-bit; accepted range 1 through 2^63-1 |
| 8 | Symbol index | unsigned 32-bit; 0 AAPL, 1 MSFT, 2 NVDA, 3 TSLA |
| 12 | Side | byte; 1 BUY, 2 SELL |
| 13 | Reserved | 3 padding bytes |
| 16 | Limit price | signed 64-bit cents; positive and below 2^48 |
| 24 | Quantity | unsigned 64-bit; accepted range 1 through 2^32-1 |
| 32 | Producer timestamp | unsigned 64-bit monotonic ns, below 2^63 |

`protocol.TRADE` is 64 bytes: trade ID, buy ID, sell ID, symbol, four padding
bytes, price ticks, quantity, producer timestamp and native-return timestamp.
The exact `struct` formats are authoritative in `protocol.py`.

This format is separate from the original `src.market_data` 37-byte format.
Do not send an old-format record directly to this engine.

The producer owns a write slot until its context exits. The consumer owns a read
slot until its context exits. Never retain the view beyond the context, start
multiple producers/consumers on one ring, or read raw cursors without its lock.
Exceptions before a context commits restore its semaphore token. Process death
while holding a token is not recoverable; the supervisor fails the run.

Mapped payloads aren't sent through `multiprocessing.Queue`, JSON or Pickle.
Process startup does serialize configuration/handle metadata. Network WebSocket
frames are bytes and require a network-to-mmap copy; this isn't end-to-end network
zero-copy. Consumers read the mapped buffer directly, but the engine then loads
fields into its own C structs. Shared pages need not have equal virtual addresses
in each process.

## Run from the repository root

Install a compatible C++ compiler first. On Windows, install Microsoft C++ Build
Tools with the Desktop development with C++ workload, including MSVC and a Windows
SDK. VS Code alone does not include the compiler. On Linux, install a C++ compiler
and the development headers for the Python interpreter you use.

```text
python -m pip install -r requirements-dev.txt -r requirements-lowlatency.txt
python setup_lowlatency.py build_ext --inplace
python -m pytest tests_lowlatency -q
python -m pytest -q
```

On Windows, use the same Python interpreter to install, compile and run. If MSVC
isn't detected, reopen CMD after installing it or use the x64 Native Tools command
prompt for your Visual Studio installation. A Linux `.so` cannot be used on Windows;
the kit intentionally supplies source, not a prebuilt native extension.

Start a slow visible demonstration (press `q` to stop ingestion and drain):

```text
python -m lowlatency.pipeline --orders 100000 --rate 5000 --capacity 64 --terminal
```

Run the mock WebSocket client and source:

```text
python -m lowlatency.pipeline --orders 10000 --rate 100000 --source websocket --capacity 64
```

Run the isolated native benchmark and million-order IPC audit:

```text
python -m lowlatency.benchmark --count 100000
python -m lowlatency.audit --count 1000000 --compare-queue
python -m lowlatency.pipeline --orders 100000 --rate 100000 --capacity 64
```

Each command creates a new directory under `lowlatency_output/`, which has its own
Git ignore rule. Pipeline outputs include `report.json`, `matcher.json`, a SQLite
ledger, mmap files and raw latency samples. The sample file has two little-endian
u64 values per order: native-call ns and producer-stamp-to-native-return ns.
Changing `--output` requires keeping that destination out of Git yourself.

## Measurement definitions

- Native-call latency includes the Python/Cython wrapper and GIL transition.
- Pipeline latency starts at the producer's timestamp and stops immediately after
  native matching returns. Direct mode stamps after reserving an mmap slot, so it
  excludes the producer's earlier wait for space. WebSocket mode stamps before
  sending, so it also includes network/library buffering. Compare them separately.
- Publication of trade records and SQLite commit latency are excluded from that
  latency distribution. The writer can still backpressure later matching work.
- Pipeline throughput uses first producer timestamp to final native return;
  startup, final reporting and final ledger drain are excluded.
- Requested source rate is a target, not achieved throughput. Bounded buffers
  backpressure the producer instead of silently dropping orders.
- Median, p95, p99 and maximum are reported. A p99 below 50 us is NOT proof every
  trade is below 50 us. Shared runners and desktop systems have scheduling spikes.
- GC callbacks count collections in the whole Python matching worker. They aren't
  a guarantee of no pauses elsewhere. GC is not disabled globally.

The native benchmark is not the same workload as the original resting-insertion
benchmark. Neither can substitute for a network/IPC/ledger benchmark.

## Persistence and failure handling

Trades are drained to a separate SQLite ledger in batches, with WAL and FULL
synchronous commits. The parent reconciles emitted/committed counts before writing
a successful report. Worker failures and timeouts fail the run; new run directories
prevent overwriting prior ledgers. A graceful terminal `q` stops ingestion and drains
the buffers. Uncommitted trade batches may be lost on abrupt termination. There is
no durable ingress journal or restart replay of the native resting order book yet.

## Bounds and future work

Only limit orders are supported in this native path. Original website market-order,
cancel and risk controls are not automatically connected to it. Keep native runs
separate from the website; all data is simulated. Native storage has a fixed maximum
number of accepted IDs per run; exhausted capacity is an explicit error.

Future work: batched IPC/native calls for throughput; lower queueing latency;
bounded/preallocated price-level storage; crash recovery; cancellation/risk support;
and integration of native snapshots into the optional website. Do not claim HFT
production readiness, a lock-free bus, or guaranteed 50 us execution.

## References

- https://docs.python.org/3/library/mmap.html
- https://docs.python.org/3/library/multiprocessing.html
- https://cython.readthedocs.io/en/latest/src/userguide/nogil.html
- https://cython.readthedocs.io/en/latest/src/quickstart/install.html
- https://learn.microsoft.com/en-us/cpp/build/vscpp-step-0-installation
- https://websockets.readthedocs.io/en/stable/reference/asyncio/client.html
