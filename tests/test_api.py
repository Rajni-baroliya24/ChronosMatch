import csv
import io
import pytest
from app import create_app


@pytest.fixture
def app():
    app = create_app(":memory:", seed=False)
    app.config["TESTING"] = True
    yield app
    app.extensions["trading"].db.close()


@pytest.fixture
def client(app):
    return app.test_client()


def test_website_assets_and_health(client):
    assert client.get("/").status_code == 200
    assert b"Run demo" in client.get("/").data
    assert client.get("/assets/style.css").status_code == 200
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/api/health").json["mode"] == "python"


def test_api_full_order_lifecycle(client):
    sell = client.post("/api/orders", json=dict(symbol="AAPL", side="SELL", price="100.01", quantity=10))
    assert sell.status_code == 201
    buy = client.post("/api/orders", json=dict(symbol="AAPL", side="BUY", type="MARKET", quantity=6))
    assert buy.status_code == 201
    assert buy.json["order"]["filled"] == 6
    assert buy.json["state"]["volume"] == 600.06
    cancelled = client.post("/api/orders/1/cancel", json={})
    assert cancelled.status_code == 200 and cancelled.json["state"]["active_orders"] == 0
    assert client.post("/api/orders/1/cancel", json={}).status_code == 404


@pytest.mark.parametrize("payload", [[], None, 3, {"symbol": []}, {"quantity": True}, {"price": "NaN"}])
def test_invalid_requests_return_json_400(client, payload):
    response = client.post("/api/orders", data=__import__("json").dumps(payload), content_type="application/json")
    assert response.status_code == 400
    assert "error" in response.json


def test_cross_origin_mutations_are_rejected(client):
    assert client.post("/api/reset", json={}, headers={"Origin": "https://unrelated.example"}).status_code == 403
    assert client.post("/api/reset", data="{}").status_code == 415
    assert client.post("/api/reset", json={}, headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403


def test_symbol_isolation_and_export(client):
    client.post("/api/orders", json=dict(symbol="AAPL", side="BUY", price="99.01", quantity=3))
    assert client.get("/api/state?symbol=MSFT").json["orders"] == []
    response = client.get("/api/export?kind=orders&symbol=AAPL")
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert rows[0]["price"] == "99.01" and rows[0]["quantity"] == "3"
    assert client.get("/api/export?kind=invalid").status_code == 400
    assert client.get("/api/state?symbol=UNKNOWN").status_code == 400


def test_risk_update_and_benchmark_validation(client):
    assert client.post("/api/risk", json={"paused": "yes"}).status_code == 400
    assert client.post("/api/risk", json={"max_notional": -1}).status_code == 400
    assert client.post("/api/benchmark", json={"count": True}).status_code == 400
    response = client.post("/api/benchmark", json={"count": 100})
    assert response.status_code == 200 and response.json["result"]["trades"] == 50


def test_demo_seeding_and_reset(client):
    assert client.post("/api/demo/tick", json={"symbol": "AAPL"}).json["state"]["total_trades"] >= 1
    reset = client.post("/api/reset", json={})
    assert reset.status_code == 200
    assert reset.json["state"]["total_orders"] == 16
    assert reset.json["state"]["total_trades"] == 0


def test_unexpected_api_paths_have_json_errors(client):
    response = client.get("/api/missing")
    assert response.status_code == 404 and response.json["error"]
