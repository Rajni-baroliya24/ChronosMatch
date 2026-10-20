from concurrent.futures import ThreadPoolExecutor
import pytest
from src.service import TradingService


@pytest.fixture
def service():
    instance = TradingService(seed=False)
    yield instance
    instance.db.close()


def order(service, side, price="100.00", quantity=10, **kwargs):
    return service.submit(dict(symbol="AAPL", side=side, type="LIMIT", price=price, quantity=quantity, **kwargs))


def test_partial_fill_and_cancel_keep_execution_history(service):
    sell = order(service, "SELL", quantity=10)
    buy = order(service, "BUY", price="101.00", quantity=6)
    assert buy["status"] == "FILLED"
    assert sell["status"] == "PARTIAL" and sell["remaining"] == 4
    service.cancel(sell["id"])
    snapshot = service.snapshot()
    assert snapshot["total_trades"] == 1
    assert snapshot["trades"][0]["price"] == 100
    assert snapshot["trades"][0]["quantity"] == 6
    assert snapshot["asks"] == []
    assert sell["filled"] == 6 and sell["status"] == "CANCELLED"


def test_market_order_does_not_rest_unfilled_remainder(service):
    order(service, "SELL", quantity=3)
    record = service.submit(dict(symbol="AAPL", side="BUY", type="MARKET", quantity=10))
    assert record["status"] == "EXPIRED"
    assert record["filled"] == 3 and record["remaining"] == 0
    assert service.snapshot()["bids"] == []
    assert service.snapshot()["asks"] == []


def test_market_sweeps_levels_at_resting_prices(service):
    order(service, "SELL", "101.01", 3)
    order(service, "SELL", "100.01", 2)
    result = service.submit(dict(symbol="AAPL", side="BUY", type="MARKET", quantity=4))
    assert result["filled"] == 4
    assert [(t["price"], t["quantity"]) for t in service.trades] == [(100.01, 2), (101.01, 2)]


def test_risk_rejection_preserves_id_and_book(service):
    service.update_risk(dict(max_quantity=5, max_notional=100))
    with pytest.raises(ValueError):
        order(service, "BUY", quantity=6)
    with pytest.raises(ValueError):
        order(service, "BUY", quantity=2)
    assert service.next_id == 1 and not service.orders


def test_pause_blocks_manual_and_demo_but_allows_cancel(service):
    record = order(service, "BUY", quantity=1)
    service.update_risk(dict(paused=True))
    with pytest.raises(ValueError):
        order(service, "SELL", quantity=1)
    with pytest.raises(ValueError):
        service.tick("AAPL")
    service.cancel(record["id"])


@pytest.mark.parametrize("payload", [
    dict(price="0"), dict(price="1.001"), dict(price="NaN"), dict(price="Infinity"),
    dict(price=True), dict(quantity=True), dict(quantity=1.5), dict(symbol={}),
    dict(symbol="UNKNOWN"), dict(side="HOLD"), dict(type="STOP"), dict(price="1000001"),
])
def test_invalid_payload_has_no_side_effects(service, payload):
    data = dict(symbol="AAPL", side="BUY", type="LIMIT", price="100", quantity=1)
    data.update(payload)
    with pytest.raises(ValueError):
        service.submit(data)
    assert service.next_id == 1 and not service.orders


def test_restart_replays_cancellation_in_correct_sequence(tmp_path):
    path = tmp_path / "replay.db"
    first = TradingService(path, seed=False)
    cancelled = order(first, "SELL", "99.99", 8)
    first.cancel(cancelled["id"])
    resting = order(first, "SELL", "100.01", 8)
    order(first, "BUY", "100.02", 5)
    first.update_risk(dict(max_quantity=500))
    before = first.snapshot()
    first.db.close()
    second = TradingService(path, seed=False)
    after = second.snapshot()
    for key in ("orders", "trades", "bids", "asks", "risk", "vwap"):
        assert after[key] == before[key]
    assert second.orders[resting["id"]]["remaining"] == 3
    assert second.trades[0]["sell_order_id"] == resting["id"]
    second.db.close()


def test_reset_remains_reset_after_restart(tmp_path):
    path = tmp_path / "reset.db"
    first = TradingService(path, seed=False)
    order(first, "BUY")
    first.update_risk(dict(paused=True))
    first.reset()
    assert len(first.orders) == 64 and not first.trades
    first.db.close()
    second = TradingService(path)
    assert len(second.orders) == 64 and not second.trades
    assert not second.risk["paused"]
    assert second.next_id == 65
    second.db.close()


def test_concurrent_submissions_get_unique_ids(service):
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: order(service, "BUY", quantity=1), range(40)))
    assert len({r["id"] for r in results}) == 40
    assert service.snapshot()["bids"] == [dict(price=100, quantity=40)]


def test_benchmark_isolated_from_workspace(service):
    order(service, "BUY")
    before = service.snapshot()
    result = service.benchmark(1000)
    assert result["trades"] == 500 and result["throughput"] > 0
    assert result["median"] <= result["p95"] <= result["p99"]
    assert service.snapshot()["orders"] == before["orders"]
    assert service.snapshot()["benchmarks"][0] == result


def test_demo_supports_one_share_risk_limit(service):
    service.update_risk(dict(max_quantity=1))
    result = service.tick("AAPL")
    assert result["quantity"] == 1 and result["filled"] == 1
