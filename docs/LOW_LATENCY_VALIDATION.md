# Low-latency validation: 25 October 2026

These are measurements on the assistant's Linux test machine, Python 3.12.14,
Cython 3.3.0, websockets 17.3 and GCC. They are NOT measurements of Rajni's Windows
laptop or GitHub runners. Source is supplied so every experiment can be repeated.
No Windows-native compilation was performed locally; the new CI workflow builds
on Windows and Ubuntu with Python 3.13 after installation/push.

## Correctness

- 31 new low-latency tests plus the 54-test Studio reference suite: 85 passed.
- The user's additional/custom tests must be run in the actual repository.
- Native matcher compared with the Python order book across three deterministic
  random workloads of 1,000 orders each, including all four symbols.
- FIFO, partial fills, best-price execution, duplicate IDs, bounds and multi-level
  sweep counting are checked. Three fills at one price are not called three levels.
- Capacity-one/tiny rings and wraparound are tested using spawned processes.
- Direct and WebSocket three-process runs are compared with reference trades and
  reconciled against the SQLite ledger, including database integrity checks.
- Curses rendered in a Linux pseudo-terminal; q drained the run and exited cleanly.
- Payload audit checked every field, including deterministic timestamp data, for
  1,000,000 records in exact order. Both ring cursors reconciled and checksum was
  500,000,500,000.

## Recorded timings

| Experiment | Orders | Throughput orders/s | Native-call p99 us | Producer-stamp-to-native-return p99 us |
| --- | ---: | ---: | ---: | ---: |
| mmap IPC only | 1,000,000 | 218,902.81 | n/a | n/a |
| Queue/Pickle IPC baseline | 1,000,000 | 102,337.63 | n/a | n/a |
| Isolated native benchmark | 100,000 | 607,711.50 | 1.878 | n/a |
| Direct ingestion + matcher + writer | 100,000 | 57,370.70 | 3.706 | 2484.908 |
| Local mock WebSocket pipeline | 10,000 | 33,266.45 | 6.385 | 24078.604 |

The final IPC audit was 2.139 times the Queue
baseline's throughput in that run. This is not a universal speedup claim. An earlier
prototype audit was slower than Queue; removing a shared cursor-lock bottleneck and
repeated header validation improved this implementation. Tests and some experiments
ran on shared compute with other work; the environment wasn't CPU-isolated. Repeat
several times on the target machine before drawing performance conclusions.

The direct run requested 100,000 orders/s and actually achieved
57,370.70. It persisted all 80,000
emitted trades and observed 20,000 three-or-more-level sweeps.
The native benchmark's maximum call latency was 2981.105 us,
so p99 below 50 us does NOT mean all calls satisfied 50 us.
The matching worker observed 0 GC collections
in the direct run, with GC enabled. This is an observation, not a permanent guarantee.

## Requirement status after adding the module

| Requirement | Status |
| --- | --- |
| Cython matching algorithm with native structs/pointers | Implemented and tested |
| mmap binary IPC between separate processes | Implemented and million-order audited |
| Asyncio mock WebSocket client/source | Implemented and integration-tested |
| Terminal bid/ask, latency graph and whale highlight | Implemented; Linux pseudo-terminal checked |
| Native and pipeline timestamp distributions | Implemented with explicit measurement boundaries |
| Background SQLite ledger | Implemented, counted and compared with reference trades |
| No Python objects in normal native matching loops | Implemented; wrappers and native allocations remain |
| Sustained complete pipeline at 100,000 orders/s | Not established; inspect measured results above |
| Every trade below 50 us | Not established; measured maxima exceeded the target |
| Complete sub-millisecond latency | Not established; queueing/network tails remain |
| Crash recovery of native resting orders | Not implemented; abrupt loss is documented |
| Windows build and terminal verification | Pending actual Windows/CI execution |

## Reproduce

From the project root after installing dependencies and compiling:

```text
python -m pytest tests_lowlatency -q
python -m pytest -q
python -m lowlatency.audit --count 1000000 --compare-queue
python -m lowlatency.benchmark --count 100000
python -m lowlatency.pipeline --orders 100000 --rate 100000 --capacity 64
python -m lowlatency.pipeline --orders 10000 --rate 100000 --capacity 64 --source websocket
```

The raw reports in `docs/lowlatency_evidence/` preserve environment, sample counts,
measurement scopes and limitations. Native benchmark throughput includes packing
and sampling but excludes IPC/network/storage. Pipeline latency excludes publication
of trade records and SQLite durability. The full pipeline must not be described as
having met all project performance requirements yet.
