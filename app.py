
"""ChronosMatch local Flask trading dashboard."""

from threading import Lock

from flask import Flask, jsonify, render_template, request

from src.engine import ChronosMatchEngine
from src.models import Order


app = Flask(__name__)

# In-memory trading engine for local development.
engine = ChronosMatchEngine()
engine_lock = Lock()


def serialize_trade(trade):
    """Convert a trade object into JSON-compatible data."""
    return {
        "buy_order_id": trade.buy_order_id,
        "sell_order_id": trade.sell_order_id,
        "symbol": trade.symbol,
        "price": trade.price,
        "quantity": trade.quantity,
    }


@app.get("/")
def home():
    """Serve the ChronosMatch dashboard."""
    return render_template("index.html")


@app.post("/api/orders")
def submit_order():
    """Validate and submit a BUY or SELL order."""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(
            error="Please provide a valid JSON order."
        ), 400

    required_fields = (
        "order_id",
        "symbol",
        "side",
        "price",
        "quantity",
        "timestamp",
    )

    for field in required_fields:
        if field not in data:
            return jsonify(
                error=f"Missing required field: {field}"
            ), 400

    try:
        order_id = int(data["order_id"])
        symbol = str(data["symbol"]).strip().upper()
        side = str(data["side"]).strip().upper()
        price = int(data["price"])
        quantity = int(data["quantity"])
        timestamp = int(data["timestamp"])

        if order_id <= 0:
            raise ValueError("Order ID must be positive.")

        if not symbol:
            raise ValueError("Symbol cannot be empty.")

        if side not in ("BUY", "SELL"):
            raise ValueError("Side must be BUY or SELL.")

        if price <= 0:
            raise ValueError("Price must be greater than zero.")

        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        if timestamp < 0:
            raise ValueError("Timestamp cannot be negative.")

        order = Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            price=price,
            quantity=quantity,
            timestamp=timestamp,
        )

        with engine_lock:
            trades = engine.submit(order)

        return jsonify(
            message="Order submitted successfully",
            order_id=order.order_id,
            symbol=order.symbol,
            trades=[
                serialize_trade(trade)
                for trade in trades
            ],
        ), 201

    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        return jsonify(error=str(exc)), 400


@app.get("/api/trades")
def get_trades():
    """Return all executed trades."""
    with engine_lock:
        trades = engine.trade_history.get_all_trades()

        return jsonify([
            serialize_trade(trade)
            for trade in trades
        ])


@app.get("/api/stats")
def get_stats():
    """Return current trading statistics."""
    with engine_lock:
        history = engine.trade_history

        return jsonify(
            total_trades=history.get_total_trades(),
            total_volume=history.get_total_volume(),
            total_traded_value=(
                history.get_total_traded_value()
            ),
        )


@app.get("/api/book/<symbol>")
def get_book(symbol):
    """Return the current order book for a symbol."""
    symbol = symbol.strip().upper()

    if not symbol:
        return jsonify(error="Symbol is required."), 400

    with engine_lock:
        book = engine.book(symbol)
        return jsonify(book.depth())


@app.post("/api/reset")
def reset_dashboard():
    """Clear the current in-memory trading session."""
    global engine

    with engine_lock:
        engine = ChronosMatchEngine()

    return jsonify(
        message="Dashboard reset successfully"
    ), 200


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )
