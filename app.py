"""Run `python app.py`, then open http://127.0.0.1:5000."""
import csv
import io
import os
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException
from src.service import TradingService


def create_app(database=None, seed=True):
    web = Path(__file__).resolve().parent / "web"
    app = Flask(__name__, static_folder=str(web), static_url_path="/assets")
    app.config["MAX_CONTENT_LENGTH"] = 128 * 1024
    service = TradingService(database if database is not None else os.environ.get("CHRONOS_DB", str(Path(__file__).parent / "data" / "chronosmatch.sqlite3")), seed=seed)
    app.extensions["trading"] = service

    @app.before_request
    def same_origin_writes():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            origin = request.headers.get("Origin")
            if origin and origin != request.host_url.rstrip("/"):
                return jsonify(error="Use the application from its own origin"), 403
            if request.headers.get("Sec-Fetch-Site") == "cross-site":
                return jsonify(error="Cross-site changes are not allowed"), 403
            if not request.is_json:
                return jsonify(error="Send an application/json object"), 415

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    def body():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object")
        return data

    @app.errorhandler(ValueError)
    def bad_request(error):
        return jsonify(error=str(error)), 400

    @app.errorhandler(KeyError)
    def not_found(error):
        return jsonify(error=str(error).strip("'")), 404

    @app.errorhandler(HTTPException)
    def http_error(error):
        if request.path.startswith("/api/"):
            return jsonify(error=error.description), error.code
        return error

    @app.get("/")
    def index():
        return send_from_directory(web, "index.html")

    @app.get("/api/health")
    def health():
        return jsonify(status="ok", mode="python", storage="sqlite", wire_bytes=37)

    @app.get("/api/state")
    def state():
        return jsonify(service.snapshot(request.args.get("symbol", "AAPL")))

    @app.post("/api/orders")
    def submit():
        record = service.submit(body())
        return jsonify(order=record, state=service.snapshot(record["symbol"])), 201

    @app.post("/api/orders/<int:oid>/cancel")
    def cancel(oid):
        body()
        record = service.cancel(oid)
        return jsonify(state=service.snapshot(record["symbol"]))

    @app.post("/api/demo/tick")
    def demo():
        data = body()
        symbol = data.get("symbol", "AAPL")
        service.tick(symbol)
        return jsonify(state=service.snapshot(symbol))

    @app.post("/api/risk")
    def risk():
        return jsonify(risk=service.update_risk(body()))

    @app.post("/api/reset")
    def reset():
        body()
        service.reset()
        return jsonify(state=service.snapshot())

    @app.post("/api/benchmark")
    def benchmark():
        return jsonify(result=service.benchmark(body().get("count", 5000)))

    @app.get("/api/export")
    def export():
        kind = request.args.get("kind", "orders")
        if kind not in ("orders", "trades"):
            raise ValueError("Export kind must be orders or trades")
        snapshot = service.snapshot(request.args.get("symbol", "AAPL"))
        records = snapshot[kind]
        fields = (["id", "symbol", "side", "type", "price", "quantity", "filled", "remaining", "status", "source", "time"]
                  if kind == "orders" else ["id", "symbol", "side", "price", "quantity", "buy_order_id", "sell_order_id", "time"])
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
        return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f'attachment; filename="chronosmatch-{kind}.csv"'})

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=False)
