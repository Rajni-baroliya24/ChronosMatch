
from flask import Flask, jsonify, render_template, request
from threading import Lock

from src.engine import ChronosMatchEngine
from src.models import Order

app = Flask(__name__)
engine = ChronosMatchEngine()
engine_lock = Lock()


@app.get("/")
def home():
    return render_template("index.html")


@app.post("/api/orders")
def submit_order():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="A JSON object is required"), 400

    try:
        order = Order(
            order_id=int(data["order_id"]),
            symbol=str(data["symbol"]).strip().upper(),
            side=str(data["side"]).upper(),
            price=int(data["price"]),
            quantity=int(data["quantity"]),
            timestamp=int(data["timestamp"]),
        )

        with engine_lock:
            trades = engine.submit(order)

        return jsonify(
            message="Order submitted successfully",
            trades=[vars_trade(trade) for trade in trades],
        ), 201

    except (ValueError, TypeError, KeyError) as exc:
        return jsonify(error=str(exc)), 400


def vars_trade(trade):
    return {
        "buy_order_id": trade.buy_order_id,
        "sell_order_id": trade.sell_order_id,
        "symbol": trade.symbol,
        "price": trade.price,
        "quantity": trade.quantity,
    }


@app.get("/api/trades")
def get_trades():
    with engine_lock:
        trades = engine.trade_history.get_all_trades()
        return jsonify([vars_trade(trade) for trade in trades])


@app.get("/api/stats")
def get_stats():
    with engine_lock:
        history = engine.trade_history
        return jsonify(
            total_trades=history.get_total_trades(),
            total_volume=history.get_total_volume(),
            total_traded_value=history.get_total_traded_value(),
        )


@app.get("/api/book/<symbol>")
def get_book(symbol):
    with engine_lock:
        book = engine.book(symbol.upper())
        return jsonify(book.depth())

@app.post("/api/reset")
def reset_dashboard():
    global engine

    with engine_lock:
        engine = ChronosMatchEngine()

    return jsonify(message="Dashboard reset successfully")


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
