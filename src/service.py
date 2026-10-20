"""Single-workspace paper matching service, with ordered SQLite event replay."""
from __future__ import annotations

import json
import random
import sqlite3
from collections import deque
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from statistics import median
from threading import RLock
from time import perf_counter_ns

from .engine import ChronosMatchEngine
from .models import Order

SYMBOLS = {"AAPL": ("Apple Inc.", 18924), "MSFT": ("Microsoft", 42870),
           "NVDA": ("NVIDIA", 13245), "TSLA": ("Tesla", 24850)}
DEFAULT_RISK = {"max_quantity": 10000, "max_notional": 1000000, "paused": False}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def price_ticks(value):
    if isinstance(value, bool) or value is None:
        raise ValueError("Enter a positive price with at most two decimal places")
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Enter a valid price") from exc
    if not amount.is_finite() or amount <= 0 or amount > 1000000 or amount * 100 != (amount * 100).to_integral_value():
        raise ValueError("Price must be $0.01–$1,000,000, with at most two decimals")
    return int(amount * 100)


class TradingService:
    def __init__(self, database=":memory:", seed=True):
        self.lock = RLock()
        if database != ":memory:":
            Path(database).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(database), check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS benchmarks (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)")
        self._reload()
        if seed and not self.orders:
            self.seed()

    def _clear_memory(self):
        self.engine = ChronosMatchEngine()
        self.orders = {}
        self.trades = []
        self.latencies = deque(maxlen=2000)
        self.risk = dict(DEFAULT_RISK)
        self.next_id = 1

    def _reload(self):
        self._clear_memory()
        for kind, payload in self.db.execute("SELECT kind, payload FROM events ORDER BY seq"):
            self._apply(kind, json.loads(payload), measure=False)

    def _event(self, kind, payload):
        try:
            with self.db:
                self.db.execute("INSERT INTO events(kind,payload) VALUES (?,?)", (kind, json.dumps(payload)))
                return self._apply(kind, payload)
        except Exception:
            self.db.rollback()
            self._reload()
            raise

    def _apply(self, kind, payload, measure=True):
        if kind == "reset":
            self._clear_memory()
        elif kind == "risk":
            self.risk.update(payload)
        elif kind == "cancel":
            record = self.orders[payload["id"]]
            self.engine.book(record["symbol"]).cancel(record["id"])
            record["status"] = "CANCELLED"
            record["remaining"] = 0
        elif kind == "submit":
            record = dict(payload)
            oid = record["id"]
            self.next_id = max(self.next_id, oid + 1)
            order = Order(oid, record["symbol"], record["side"], record["price_ticks"], record["quantity"], oid)
            self.orders[oid] = record
            start = perf_counter_ns()
            trades = self.engine.submit(order)
            elapsed = perf_counter_ns() - start
            if measure:
                self.latencies.append(elapsed / 1000)
            for trade in trades:
                self.trades.append({"id": len(self.trades) + 1, "symbol": trade.symbol,
                                    "price": trade.price / 100, "quantity": trade.quantity,
                                    "buy_order_id": trade.buy_order_id, "sell_order_id": trade.sell_order_id,
                                    "side": record["side"], "time": record["time"]})
                for matched_id in (trade.buy_order_id, trade.sell_order_id):
                    matched = self.orders[matched_id]
                    matched["filled"] += trade.quantity
                    matched["remaining"] = matched["quantity"] - matched["filled"]
                    matched["status"] = "FILLED" if matched["remaining"] == 0 else "PARTIAL"
            if record["type"] == "MARKET" and record["remaining"]:
                self.engine.book(record["symbol"]).cancel(oid)
                record["status"] = "EXPIRED"
                record["remaining"] = 0
            return record

    def seed(self):
        with self.lock:
            for index, (symbol, (_, base)) in enumerate(SYMBOLS.items()):
                for level in range(1, 9):
                    for side in ("BUY", "SELL"):
                        ticks = base + (-1 if side == "BUY" else 1) * level * 4
                        qty = 140 + ((index + level) * 137) % 700
                        self._submit(symbol, side, "LIMIT", ticks, qty, "LIQUIDITY")

    def _submit(self, symbol, side, order_type, ticks, quantity, source):
        return self._event("submit", {"id": self.next_id, "symbol": symbol, "side": side,
                                     "type": order_type, "price_ticks": ticks, "price": ticks / 100,
                                     "quantity": quantity, "remaining": quantity, "filled": 0,
                                     "status": "OPEN", "source": source, "time": now()})

    def submit(self, data, source="MANUAL"):
        with self.lock:
            if self.risk["paused"]:
                raise ValueError("Engine is paused. Resume it in Risk controls.")
            symbol = data.get("symbol", "AAPL")
            side = data.get("side")
            order_type = data.get("type", "LIMIT")
            quantity = data.get("quantity")
            if not isinstance(symbol, str) or symbol not in SYMBOLS:
                raise ValueError("Choose a supported symbol")
            if side not in ("BUY", "SELL") or order_type not in ("LIMIT", "MARKET"):
                raise ValueError("Choose BUY or SELL, and LIMIT or MARKET")
            if not isinstance(quantity, int) or isinstance(quantity, bool) or not 1 <= quantity <= self.risk["max_quantity"]:
                raise ValueError(f"Quantity must be an integer from 1 to {self.risk['max_quantity']:,}")
            if order_type == "MARKET":
                depth = self.engine.book(symbol).depth()["asks" if side == "BUY" else "bids"]
                if not depth:
                    raise ValueError("No opposing liquidity. Add a limit order first.")
                ticks = depth[-1][0]
            else:
                ticks = price_ticks(data.get("price"))
            if ticks * quantity > self.risk["max_notional"] * 100:
                raise ValueError("Order exceeds the maximum order notional in Risk controls")
            return self._submit(symbol, side, order_type, ticks, quantity, source)

    def cancel(self, oid):
        with self.lock:
            record = self.orders.get(oid)
            if not record or record["status"] not in ("OPEN", "PARTIAL"):
                raise KeyError("Order is already closed or does not exist")
            self._event("cancel", {"id": oid})
            return record

    def tick(self, symbol):
        with self.lock:
            if not isinstance(symbol, str) or symbol not in SYMBOLS:
                raise ValueError("Choose a supported symbol")
            if self.risk["paused"]:
                raise ValueError("Engine is paused. Resume it in Risk controls.")
            side = random.choice(("BUY", "SELL"))
            book = self.engine.book(symbol)
            quote = book.best_ask() if side == "BUY" else book.best_bid()
            qty = random.randint(1, min(80, self.risk["max_quantity"]))
            if quote is None:
                base = SYMBOLS[symbol][1]
                self._submit(symbol, "SELL" if side == "BUY" else "BUY", "LIMIT", base, 200, "LIQUIDITY")
            return self.submit({"symbol": symbol, "side": side, "type": "MARKET", "quantity": qty}, source="DEMO")

    def update_risk(self, data):
        updates = {}
        for key, limit in (("max_quantity", 1000000), ("max_notional", 100000000)):
            if key in data:
                value = data[key]
                if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= limit:
                    raise ValueError(f"{key} must be an integer from 1 to {limit:,}")
                updates[key] = value
        if "paused" in data:
            if not isinstance(data["paused"], bool):
                raise ValueError("paused must be true or false")
            updates["paused"] = data["paused"]
        with self.lock:
            self._event("risk", updates)
            return dict(self.risk)

    def reset(self):
        with self.lock:
            self._event("reset", {})
            self.db.execute("DELETE FROM benchmarks")
            self.db.commit()
            self.seed()

    def snapshot(self, symbol="AAPL"):
        with self.lock:
            if not isinstance(symbol, str) or symbol not in SYMBOLS:
                raise ValueError("Choose a supported symbol")
            book = self.engine.book(symbol)
            depth = book.depth()
            trades = [t for t in self.trades if t["symbol"] == symbol]
            records = [o for o in self.orders.values() if o["symbol"] == symbol]
            active = [o for o in records if o["status"] in ("OPEN", "PARTIAL")]
            matched_shares = sum(t["quantity"] for t in trades)
            volume = sum(t["price"] * t["quantity"] for t in trades)
            samples = sorted(self.latencies)
            def percentile(q):
                return round(samples[int(q * (len(samples) - 1))], 2) if samples else None
            watch = []
            for ticker, (name, reference) in SYMBOLS.items():
                recent = next((t for t in reversed(self.trades) if t["symbol"] == ticker), None)
                last = recent["price"] if recent else reference / 100
                watch.append({"symbol": ticker, "name": name, "price": last,
                              "change": round((last / (reference / 100) - 1) * 100, 2)})
            return {"symbol": symbol, "name": SYMBOLS[symbol][0], "mode": "python", "risk": dict(self.risk),
                    "watchlist": watch, "reference": SYMBOLS[symbol][1] / 100,
                    "bids": [{"price": p / 100, "quantity": q} for p, q in depth["bids"]],
                    "asks": [{"price": p / 100, "quantity": q} for p, q in depth["asks"]],
                    "best_bid": book.best_bid() / 100 if book.best_bid() else None,
                    "best_ask": book.best_ask() / 100 if book.best_ask() else None,
                    "last_price": trades[-1]["price"] if trades else SYMBOLS[symbol][1] / 100,
                    "orders": list(reversed(records)), "trades": list(reversed(trades[-500:])),
                    "history": trades[-200:], "active_orders": len(active), "total_orders": len(records),
                    "total_trades": len(trades), "matched_shares": matched_shares, "volume": round(volume, 2),
                    "vwap": round(volume / matched_shares, 2) if matched_shares else None,
                    "latency": {"median": round(median(samples), 2) if samples else None, "p95": percentile(.95),
                                "p99": percentile(.99), "samples": len(samples)},
                    "benchmarks": [json.loads(row[0]) for row in self.db.execute("SELECT payload FROM benchmarks ORDER BY id DESC LIMIT 8")]}

    def benchmark(self, count=5000):
        if isinstance(count, bool) or not isinstance(count, int) or not 100 <= count <= 20000:
            raise ValueError("Benchmark count must be an integer from 100 to 20,000")
        isolated = ChronosMatchEngine()
        durations = []
        start = perf_counter_ns()
        trades = 0
        for i in range(count):
            order = Order(i + 1, "AAPL", "SELL" if i % 2 == 0 else "BUY", 10000, 1, i)
            before = perf_counter_ns()
            trades += len(isolated.submit(order))
            durations.append((perf_counter_ns() - before) / 1000)
        elapsed = (perf_counter_ns() - start) / 1e9
        samples = sorted(durations)
        result = {"count": count, "throughput": round(count / elapsed), "median": round(median(samples), 2),
                  "p95": round(samples[int(.95 * (count - 1))], 2), "p99": round(samples[int(.99 * (count - 1))], 2),
                  "trades": trades, "elapsed_ms": round(elapsed * 1000, 2), "mode": "python", "time": now(),
                  "scenario": "Alternating same-price limit orders; isolated in-memory engine; excludes HTTP and SQLite."}
        with self.lock, self.db:
            self.db.execute("INSERT INTO benchmarks(payload) VALUES (?)", (json.dumps(result),))
        return result
