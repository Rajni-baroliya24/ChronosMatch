# ChronosMatch — Python Reference Trading Engine

An educational, deterministic limit-order matching engine with a binary
market-data parser and automated tests. **Not production HFT or end-to-end
zero-copy**; no live exchange connection, persistence, authentication,
network server, risk checks, or concurrency control.

## Team module ownership

- **Varsha:** `src/order_book.py` — price-time matching, partial fills, cancel, depth.
- **Akash:** `src/market_data.py` — fixed-width binary protocol and `memoryview` decoding.
- **Gauri:** `tests/` and `benchmarks/` — behavioral tests and performance measurement.
- **Team lead/integration:** `src/models.py`, `src/engine.py`, `main.py`, documentation.

## Windows / VS Code

From the repository root (folder containing `main.py`):

```powershell
python -m pip install -r requirements.txt
python -m pytest -v
python main.py
python -m benchmarks.benchmark
```

## Protocol

37-byte big-endian record: `uint64 id`, `8s symbol`, `uint8 side`,
`uint64 price_ticks`, `uint32 quantity`, `uint64 timestamp`.
Side 1 = BUY, 2 = SELL. Prices are **integer ticks**, not currency floats.
The parser uses `struct.unpack_from` with `memoryview` to avoid intermediate
record slicing, but creates Python `Order` objects and the engine maintains
Python order-book data structures. Thus this is not zero-copy end-to-end.

## Matching semantics

- Separate order book for each symbol.
- BUY crosses when limit >= best ask; SELL crosses when limit <= best bid.
- Trade price is the resting order's limit price.
- Best price first; FIFO within each price level, based on submission order.
- Partial fills remain in the book; cancellation removes remaining quantity.
- Order IDs are globally unique for the lifetime of the engine.
- This prototype assumes one thread and valid sequential submission.

## Limitations / next steps

- Verify mentor's exact ChronosMatch specification and expected API before integration.
- Add risk limits, audit logs, cancellation messages, persistence and recovery.
- Improve performance: current best-price lookup uses `min`/`max` over price levels
  and cancellation uses linear search in a deque.
- Add binary fuzz tests, memory allocation profiling, realistic mixed order-flow
  benchmarks, and concurrency/load testing.
- For true high-performance low-allocation processing consider a native engine
  with explicit ownership and buffer-lifetime guarantees.

## GitHub collaboration

Do not overwrite teammates' branches. Ask each owner to review/adapt their
module, open a PR into `develop`, and run `python -m pytest -v` before merging.
Keep existing repository modules and tests when integrating; reconcile any
`Order` model API differences rather than blindly replacing files.
