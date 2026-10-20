# ChronosMatch Studio

A complete, local Python matching-engine project with a responsive web dashboard. This edition builds on the earlier ChronosMatch engine and dashboard archives.

**All orders, reference prices, liquidity and executions are simulated.** No API key, brokerage account, exchange connection or real money is involved.

## Start on Windows

Extract this ZIP into a **new folder** first. Keep your existing ChronosMatch folder until you have run and reviewed this edition.

Requirements: Python 3.10 or later, an up-to-date browser, and internet access for the initial package installation. Validation for this edition used Python 3.12.

Open Command Prompt inside the extracted project folder, where `app.py` is visible:

```bat
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python app.py
```

Then open **http://127.0.0.1:5000**. If `py` is unavailable, use `python` for the first command. You can also double-click `START_WINDOWS.bat` to perform these steps. Keep the server terminal open; press Ctrl+C to stop.

Your header should say **PYTHON ENGINE**. `python web_app.py` remains available as a compatible entry point. If port 5000 is already occupied by your old Flask app, stop it before starting this one.

## Start on macOS / Linux

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

Open http://127.0.0.1:5000. For a local WSGI server, run `python serve.py` from the same virtual environment. The Flask development-server notice is expected when using `app.py`.

## First five minutes

1. The overview starts with simulated buy and sell liquidity for AAPL. The other watchlist symbols have separate books.
2. Click **Run demo** at the top right. It repeatedly submits small simulated market orders and produces genuine matches inside the simulator. Click **Stop demo** to stop.
3. To make a manual match, choose **Buy / Long**, set **Market (IOC)**, enter 10 shares, and submit. It consumes the lowest available sell price. A Buy Limit at or above the best ask also crosses.
4. To rest an order, use a Buy Limit below the best ask or a Sell Limit above the best bid. Open orders can be cancelled from the blotter.
5. Explore Order blotter, Performance, Architecture and Risk controls. Try CSV export, dark mode, quantity/notional limits, pause and reset.

A market order with insufficient depth fills the available quantity and expires the remainder. A market order with no opposing liquidity is rejected. Limit orders can partially fill and keep a remainder in the book.

## Included functionality

- Price-time matching, multiple symbol books, resting-price execution, partial fills and cancellations.
- Integer price ticks inside the Python engine; two-decimal dollar prices in the dashboard.
- Limit/GTC and market/IOC orders.
- Visible demo controls, execution chart, depth, watchlist, trade tape and searchable/filterable blotter.
- Editable order risk limits and pause/resume controls.
- SQLite persistence with ordered event replay on restart.
- Measured matching durations and an isolated benchmark.
- CSV exports and responsive light/dark layouts.
- Binary ingestion example, automated tests, architecture and integration documentation.

## Files

```text
app.py                    Flask app factory and API
web_app.py                Compatible entry point
serve.py                  Waitress local server
src/models.py             Order / Trade dataclasses
src/order_book.py         Price-time FIFO matching
src/engine.py             Multi-symbol routing and binary ingestion
src/market_data.py        37-byte buffer-aware wire parser
src/service.py            Order lifecycle, risk, SQLite, metrics and demo
web/                      Complete web interface
main.py                   Command-line binary-ingestion demonstration
benchmarks/               Original isolated book-insertion benchmark
tests/                    Engine, API, service and recovery tests
architecture.md           Updated implementation architecture
docs/INTEGRATION.md        Safe integration into your existing project
docs/VALIDATION.md         Checks performed for this edition
```

## Tests and benchmarks

Inside the project folder and virtual environment:

```bat
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest -q
.venv\Scripts\python main.py
.venv\Scripts\python -m benchmarks.benchmark
```

Use the corresponding `.venv/bin/python` path on macOS/Linux. The original command-line benchmark measures resting insertions. The dashboard benchmark measures alternating same-price submissions and fills; their numbers describe different workloads.

Optional browser-simulator regression checks require Node.js:

```sh
node tests/browser_engine.test.cjs
```

## Storage and operating model

The Python workspace lives in `data/chronosmatch.sqlite3`. It is ignored by Git. To use a different database, set `CHRONOS_DB` before starting the server. Run one server process per database; Waitress's threads share the same service lock. There is one shared simulation workspace, without login or user accounts. The server binds to this computer's loopback address.

The hosted website is a **BROWSER DEMO**, with a separate JavaScript matcher and data stored in that browser. It does not run this Python server or share the SQLite database. Browser benchmark results are labeled accordingly. For the complete Python behavior, run this download locally.

## Architecture file: keep it

Your existing `architecture.md` is documentation, not executable code. Keep the file. After reviewing this implementation, replace the initial proposal with the updated `architecture.md` supplied here, or merge the relevant sections. Review `docs/INTEGRATION.md` before changing your original project.

## Engineering boundaries

This is an educational matching simulator, not a production HFT trading platform. The binary parser avoids payload-slice copies, while decoding and object creation still allocate. Order-book price-level scans and HTTP/SQLite overhead are not an exchange-grade low-latency architecture. See `architecture.md` for scope, complexity and next steps.

## Primary technical references

- [Flask testing](https://flask.palletsprojects.com/en/stable/testing/)
- [Flask deployment](https://flask.palletsprojects.com/en/stable/deploying/)
- [Python struct and buffer protocol](https://docs.python.org/3/library/struct.html)
