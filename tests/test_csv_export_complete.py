"""Complete CSV exports must remain independent of dashboard display limits."""
import csv
import io
import pytest
from app import create_app


@pytest.fixture
def workspace():
    app = create_app(":memory:", seed=False)
    app.config["TESTING"] = True
    yield app.test_client(), app.extensions["trading"]
    app.extensions["trading"].db.close()


def order(service, side, quantity=1, symbol="AAPL", price="100.00"):
    return service.submit(dict(symbol=symbol, side=side, type="LIMIT", price=price, quantity=quantity))


@pytest.mark.parametrize("count", [500, 501, 1001])
def test_csv_contains_all_trades_beyond_display_limit(workspace, count):
    client, service = workspace
    order(service, "SELL", symbol="MSFT")
    order(service, "BUY", symbol="MSFT")
    for _ in range(count):
        order(service, "SELL")
    order(service, "BUY", quantity=count)

    state = client.get("/api/state?symbol=AAPL").get_json()
    assert state["total_trades"] == count
    assert len(state["trades"]) == min(count, 500)
    response = client.get("/api/export?kind=trades&symbol=AAPL")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "attachment" in response.headers["Content-Disposition"]
    rows = list(csv.DictReader(io.StringIO(response.get_data(as_text=True))))
    assert len(rows) == count
    assert [int(row["id"]) for row in rows] == list(range(count + 1, 1, -1))
    assert {row["symbol"] for row in rows} == {"AAPL"}
    assert sum(int(row["quantity"]) for row in rows) == count
    assert sum(float(row["price"]) * int(row["quantity"]) for row in rows) == count * 100
    assert service.snapshot("AAPL")["total_trades"] == count


def test_order_export_is_a_copy_and_remains_symbol_scoped(workspace):
    client, service = workspace
    first = order(service, "BUY", quantity=3, price="99.00")
    order(service, "BUY", symbol="MSFT", price="99.00")
    copied = service.export_records("orders", "AAPL")
    service.cancel(first["id"])
    assert copied[0]["status"] == "OPEN"
    assert copied[0]["remaining"] == 3
    assert copied[0] is not first
    rows = list(csv.DictReader(io.StringIO(client.get("/api/export?kind=orders&symbol=AAPL").text)))
    assert len(rows) == 1
    assert rows[0]["symbol"] == "AAPL"
    assert rows[0]["status"] == "CANCELLED"


@pytest.mark.parametrize("query", ["kind=invalid", "kind=trades&symbol=UNKNOWN", "kind=orders&symbol="])
def test_invalid_export_parameters_return_json_errors(workspace, query):
    client, _ = workspace
    response = client.get("/api/export?" + query)
    assert response.status_code == 400
    assert response.is_json and response.get_json()["error"]


@pytest.mark.parametrize("kind", ["orders", "trades"])
def test_empty_export_still_has_headers(workspace, kind):
    client, _ = workspace
    response = client.get("/api/export?kind=" + kind)
    assert response.status_code == 200
    reader = csv.DictReader(io.StringIO(response.text))
    assert reader.fieldnames and "symbol" in reader.fieldnames
    assert list(reader) == []
