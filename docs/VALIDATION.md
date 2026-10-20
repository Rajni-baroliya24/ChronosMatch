# Validation report

Validated on 18 October 2026 with Python 3.12.14 and Node.js v24.19.0.

## Completed checks

- `python -m pytest -q`: **54 passed**. The suite includes the original 16 engine and binary-ingestion tests and new service, API, concurrency, risk, persistence and parity tests.
- A deterministic mixed workload compares Python and browser results across 250 attempted submissions/cancellations, two symbols, crossing limits, partial fills and market IOC behavior. Order states, trade allocations and final depth agree.
- `node tests/browser_engine.test.cjs`: passed. Covers FIFO, partial fills, cancellation, market IOC, risk limits, pause, reset, benchmark isolation, persistence and symbol isolation.
- `node --check` for both application scripts: passed.
- Static HTML validation: 98 unique element IDs; 74 direct JavaScript ID lookups resolved; all declared stylesheet and script paths exist.
- `python main.py`: completed the binary-ingestion example with two resting-price trades and an empty final book.
- `python -m benchmarks.benchmark`: completed the original 5,000-order resting-insertion workload.
- Flask test-client checks cover homepage/assets, JSON orders, cancellations, invalid requests, origin restrictions, demo/reset, risk, benchmark validation, symbol isolation and CSV export.

## Verification limits

Visual rendering and real-browser interaction could not be checked in this environment. Responsive CSS and theme controls are implemented, but no visual browser QA is claimed. Windows launch instructions and launcher are supplied; actual execution was tested on Linux, not on the user's Windows machine.

Benchmark values are local measurements of a specific workload and runtime. The application does not claim production HFT capability or end-to-end zero-copy execution. Hosted browser timing is separate from Python timing.
