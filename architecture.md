# ChronosMatch System Architecture

## Project overview

ChronosMatch Studio is a Python-based educational trading-engine simulator with an interactive web dashboard. It extends the earlier ChronosMatch reference engine. All prices, liquidity and executions are simulated. This edition does not connect to exchanges or brokerage accounts.

The original high-frequency, zero-copy description is a **design objective**, not a verified production capability. The binary parser avoids copying payload slices; Python objects, JSON serialization, SQLite writes and HTTP responses still allocate memory.

## Architecture objectives

- Minimize unnecessary copying in the binary ingestion path.
- Match orders deterministically using integer price ticks and price-time priority.
- Separate the matching engine, service, persistence, API and interface.
- Validate new orders against configurable quantity and notional limits.
- Restore the workspace after restart by replaying ordered events.
- Support integration, meaningful tests and reproducible performance measurements.
- Keep system interfaces and practical limits explicit.

## Implemented system components

| Component | Implementation | Responsibility |
| --- | --- | --- |
| Market data ingestion | `src/market_data.py` | Encode and parse fixed-width binary messages using `memoryview` and `struct.unpack_from`. |
| Shared models | `src/models.py` | Immutable, slotted Order and Trade dataclasses; positive integer prices and quantities. |
| Order book | `src/order_book.py` | Per-symbol price levels and FIFO queues; partial fills, resting-price execution and cancellation. |
| Matching engine | `src/engine.py` | Route orders to separate symbol books, enforce globally unique IDs, and prevalidate binary batches. |
| Simulation driver | `TradingService.tick` | Submit small simulated market orders against seeded liquidity. This is a demonstration strategy. |
| Risk management | `TradingService.submit` / `update_risk` | Check supported symbols, types, sides, quantity, price precision, per-order notional and pause state. |
| Execution interface | `app.py` | Same-origin JSON API for orders, cancellations, demo ticks, state, risk, export and benchmarks. |
| Persistence | `TradingService` + SQLite | Append ordered events; reconstruct active orders and trades on restart. Save benchmark results separately. |
| Monitoring | `TradingService.snapshot` / `benchmark` | Order and execution counts, traded value, VWAP, depth, matching latency and isolated benchmark results. |
| Web dashboard | `web/index.html`, `style.css`, `app.js` | Responsive workspace, chart, order entry, order book, trade tape, blotter, CSV export and controls. |
| Hosted browser demonstration | `web/demo-engine.js` | Separate JavaScript implementation for the hosted demo; uses local storage instead of the Python API. |

## Data flow

1. The web client validates ordinary form constraints and sends a JSON order to Flask.
2. The service checks the pause state, symbol, side, order type, price, quantity and notional limit.
3. Under a process-local lock, SQLite records the event and the service applies it to the engine.
4. The engine routes the order to its symbol's order book.
5. The book fills the best opposing price first, then orders at that price in submission order.
6. Each match updates both orders and appends an execution with the resting order's price.
7. A limit-order remainder rests. A market-order remainder is cancelled immediately.
8. The API returns a snapshot. The dashboard refreshes its depth, history, chart and counters.

The browser edition follows the same matching rules in JavaScript. It does not invoke Python or synchronize with the local SQLite workspace.

## Matching contracts

- Supported dashboard symbols: AAPL, MSFT, NVDA and TSLA. These are sample instruments with fixed initial reference prices, not current market quotes.
- Core engine prices are integer cents (`price_ticks`); `$100.01` becomes `10001` ticks.
- Limit orders remain good till cancelled. Market orders are immediate-or-cancel (IOC).
- Matching uses the resting order's price. Timestamps are metadata; submission sequence determines FIFO order.
- IDs are unique across all symbols within an engine session. The service assigns them.
- Partial orders show filled quantity and remaining resting quantity separately.
- Cancelled and expired orders have zero *active* remaining quantity. Their unfilled quantity is `quantity - filled`.
- A market order has no limit price; the service uses the worst current opposing price for its conservative pre-trade notional check.
- No available opposing liquidity means the market order is rejected.
- Seeded orders are marked `LIQUIDITY`; demo orders are marked `DEMO`; user submissions are marked `MANUAL`.
- This is a matching laboratory. All sides share one book; account ownership, self-trade prevention, balances and settlement are not modeled.

## Risk rules

Defaults: maximum 10,000 shares and $1,000,000 notional per order. Both are editable. Pausing blocks new manual and demo orders while allowing cancellations. Limit changes apply to future orders. System liquidity seeding supplies the simulation and bypasses these order-entry limits.

These controls validate each order. They do not implement position exposure, cumulative account limits, exchange circuit breakers, credit checks or portfolio risk.

## Persistence and concurrency

SQLite stores ordered `submit`, `cancel`, `risk` and `reset` events. Startup replays them without treating replay time as fresh latency measurements. A reset event starts a clean logical session and restores default limits and liquidity; earlier events remain in the database's event log. Benchmark history is cleared on reset.

One `TradingService` instance owns the in-memory books. A reentrant lock serializes its mutations and snapshots, including access from Waitress threads. Run **one server process per database**. Multiple independent WSGI processes would have separate in-memory books and are not supported. This edition is a single shared local workspace, without user authentication.

## JSON API

| Method | Endpoint | Contract |
| --- | --- | --- |
| GET | `/api/health` | Python mode, server health, SQLite storage and wire message size. |
| GET | `/api/state?symbol=AAPL` | Book depth, orders, recent executions, counters, limits and benchmark history. |
| POST | `/api/orders` | `{ "symbol": "AAPL", "side": "BUY", "type": "LIMIT", "price": "189.28", "quantity": 10 }` |
| POST | `/api/orders/<id>/cancel` | Cancel a resting remainder; JSON body `{}`. |
| POST | `/api/demo/tick` | One simulation step: `{ "symbol": "AAPL" }`. |
| POST | `/api/risk` | Any supported fields: `max_quantity`, `max_notional`, `paused`. |
| POST | `/api/benchmark` | `{ "count": 5000 }`; accepted range 100–20,000. |
| POST | `/api/reset` | Reset the workspace; JSON body `{}`. |
| GET | `/api/export?symbol=AAPL&kind=orders` | CSV for orders; use `kind=trades` for the last 500 executions in the snapshot. |

Requests that mutate state must use `application/json`. Invalid fields return JSON 400 responses; unavailable cancellations return 404. Cross-origin mutation requests are rejected. The local service binds to `127.0.0.1` by default.

## Binary ingestion format

Network byte order, struct format `!Q8sBQIQ`, **37 bytes per order**:

| Field | Bytes | Encoding |
| --- | --- | --- |
| Order ID | 8 | Unsigned 64-bit integer |
| Symbol | 8 | ASCII, NUL-padded |
| Side | 1 | 1 = BUY, 2 = SELL |
| Price ticks | 8 | Unsigned 64-bit integer |
| Quantity | 4 | Unsigned 32-bit integer |
| Timestamp | 8 | Unsigned 64-bit integer |

A stream must contain complete messages. Malformed streams and duplicate IDs are checked before the engine applies any order in a binary ingestion batch. Binary ingestion is exposed through the Python engine, not a public HTTP upload endpoint.

## Performance methodology

The dashboard benchmark creates an isolated in-memory engine, then alternates same-price SELL and BUY orders. It reports wall-clock throughput and the median, P95 and P99 of measured submission time. It excludes HTTP, SQLite, chart rendering and real network traffic. Throughput includes loop and order-construction overhead. Browser and Python results are labeled separately and should not be treated as equivalent measurements.

The overview reports recent matching durations across symbols in the current process or browser session, including liquidity creation. Python restart resets these samples. Benchmarks depend on the machine, runtime, workload and background activity; they are not an HFT latency guarantee.

Price selection currently scans price-level keys (`min` / `max`), and cancellation removes from a FIFO queue. Heap or tree indexes, bounded queues, exchange connectivity, durable recovery under external writers and end-to-end memory measurements are future engineering work.

## Development workflow

- `main`: reviewed, stable project.
- `develop`: integration and testing.
- `feature/*`: individual changes.
- Review engine and service contract changes together. Run the complete Python tests before merging to `develop`.
- Suggested review ownership: matching and books; ingestion and buffers; testing and benchmarks; architecture and integration.
- See `docs/INTEGRATION.md` before merging this package into an existing checkout.

## Status

Implemented educational Python application with a hosted browser demonstration. Original reference-engine behavior is retained, binary-batch duplicate checking is strengthened, and API/persistence/dashboard functionality is added. The included validation report records the checks run on this edition.
