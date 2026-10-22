# ChronosMatch performance results

Recorded: 2026-10-22T17:36:52+05:30

## Environment and source

- Operating system: Windows-11-10.0.26300-SP0
- Python: CPython 3.13.6
- Processor: Intel64 Family 6 Model 154 Stepping 4, GenuineIntel
- Source branch: `feature/chronosmatch-integration`
- Source commit: `a5786f404147716fb8a001ca73cb1c792a5a341c`
- Working tree before measurement: clean

## Method

- Command: `python -m benchmarks.benchmark`
- Runs: 5; each run uses a new Python process.
- Orders per run: 5,000
- Scenario reported by the benchmark: same-price resting BUY insertions; no matching or network I/O.
- Throughput is the benchmark's wall-clock rate; submission timings are its per-order samples.
- Values below retain the rounding used by the benchmark's printed output.

## Measured results

| Run | Orders | Throughput (orders/s) | Median submit (us) | P95 submit (us) | P99 submit (us) |
| --- | --- | --- | --- | --- | --- |
| 1 | 5,000 | 288,078 | 0.70 | 1.40 | 3.20 |
| 2 | 5,000 | 234,624 | 0.70 | 1.60 | 4.40 |
| 3 | 5,000 | 303,582 | 0.60 | 1.10 | 2.20 |
| 4 | 5,000 | 331,268 | 0.60 | 1.20 | 2.50 |
| 5 | 5,000 | 162,853 | 1.30 | 2.10 | 6.00 |

## Observations

- Median reported throughput across runs: 288,078 orders/s.
- Throughput range: 162,853 to 331,268 orders/s.
- Percentile values describe each run individually.
- These measurements establish a local baseline for the stated workload.
- The workload directly exercises OrderBook; the API, persistence and binary-ingestion paths have separate performance characteristics.
- The benchmark result does not establish production HFT latency or end-to-end zero-copy behavior.
