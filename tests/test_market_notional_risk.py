"""Risk checks must price actual available market fills before changing state."""
import json
from pathlib import Path
import shutil
import subprocess
import pytest
from app import create_app
from src.service import TradingService


CASES = [
    pytest.param("BUY", 1, 1, True, 1, id="buy-best-price-only"),
    pytest.param("BUY", 2, 100, False, 0, id="buy-sweep-exceeds-limit"),
    pytest.param("BUY", 2, 101, True, 101, id="buy-at-limit"),
    pytest.param("BUY", 5, 101, True, 101, id="buy-ioc-prices-only-available-fills"),
    pytest.param("SELL", 1, 99, False, 0, id="sell-best-bid-exceeds-limit"),
    pytest.param("SELL", 1, 100, True, 100, id="sell-at-limit"),
    pytest.param("SELL", 2, 100, False, 0, id="sell-sweep-exceeds-limit"),
    pytest.param("SELL", 2, 101, True, 101, id="sell-sweep-at-limit"),
    pytest.param("SELL", 5, 101, True, 101, id="sell-ioc-prices-only-available-fills"),
]


def liquidity(service, incoming_side):
    resting_side = "SELL" if incoming_side == "BUY" else "BUY"
    for price in ("100.00", "1.00"):
        service.submit(dict(symbol="AAPL", side=resting_side, type="LIMIT", price=price, quantity=1))


@pytest.mark.parametrize("side,quantity,limit,allowed,value", CASES)
def test_market_notional_api_checks_executable_depth_before_submission(side, quantity, limit, allowed, value):
    app = create_app(":memory:", seed=False)
    app.config["TESTING"] = True
    service = app.extensions["trading"]
    try:
        liquidity(service, side)
        service.update_risk({"max_notional": limit})
        before = service.snapshot("AAPL")
        next_id = service.next_id
        events = service.db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        response = app.test_client().post("/api/orders", json=dict(symbol="AAPL", side=side, type="MARKET", quantity=quantity))
        if not allowed:
            assert response.status_code == 400
            assert "notional" in response.get_json()["error"]
            assert service.snapshot("AAPL") == before
            assert service.next_id == next_id
            assert service.db.execute("SELECT COUNT(*) FROM events").fetchone()[0] == events
        else:
            assert response.status_code == 201
            data = response.get_json()
            assert data["order"]["filled"] == min(quantity, 2)
            assert data["order"]["remaining"] == 0
            assert data["order"]["status"] == ("FILLED" if quantity <= 2 else "EXPIRED")
            assert data["state"]["volume"] == value
            assert data["state"]["volume"] <= limit
    finally:
        service.db.close()


@pytest.mark.parametrize("side", ["BUY", "SELL"])
def test_limit_orders_still_use_limit_price_times_requested_quantity(side):
    service = TradingService(seed=False)
    try:
        service.update_risk({"max_notional": 100})
        with pytest.raises(ValueError, match="notional"):
            service.submit(dict(symbol="AAPL", side=side, type="LIMIT", price="100.00", quantity=2))
        assert service.next_id == 1 and not service.orders and not service.trades
    finally:
        service.db.close()


def test_rejected_market_sell_does_not_reappear_after_restart(tmp_path):
    path = tmp_path / "risk.sqlite3"
    service = TradingService(path, seed=False)
    try:
        liquidity(service, "SELL")
        service.update_risk({"max_notional": 99})
        with pytest.raises(ValueError, match="notional"):
            service.submit(dict(symbol="AAPL", side="SELL", type="MARKET", quantity=1))
    finally:
        service.db.close()
    restarted = TradingService(path, seed=False)
    try:
        assert restarted.next_id == 3
        assert len(restarted.orders) == 2
        assert restarted.trades == []
        assert restarted.risk["max_notional"] == 99
        assert restarted.engine.book("AAPL").depth()["bids"] == [(10000, 1), (100, 1)]
    finally:
        restarted.db.close()


def test_browser_engine_enforces_the_same_market_risk_cases():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is needed for browser risk parity")
    cases = [list(case.values) for case in CASES]
    script = r'''
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {DemoEngine}=require(process.argv[1]);
const cases=JSON.parse(fs.readFileSync(0,'utf8'));
for(const [side,quantity,limit,allowed,value] of cases){
  const engine=new DemoEngine(null,{seed:false});
  for(const price of ['100.00','1.00'])
    engine.submit({symbol:'AAPL',side:side==='BUY'?'SELL':'BUY',type:'LIMIT',price,quantity:1});
  engine.updateRisk({max_notional:limit});
  const before=JSON.stringify({orders:engine.orders,trades:engine.trades,nextId:engine.nextId});
  const submit=()=>engine.submit({symbol:'AAPL',side,type:'MARKET',quantity});
  if(allowed){
    const order=submit();
    assert.equal(order.filled,Math.min(quantity,2));
    assert.equal(order.remaining,0);
    assert.equal(order.status,quantity<=2?'FILLED':'EXPIRED');
    assert.equal(engine.snapshot('AAPL').volume,value);
    assert.ok(value<=limit);
  }else{
    assert.throws(submit,/notional/);
    assert.equal(JSON.stringify({orders:engine.orders,trades:engine.trades,nextId:engine.nextId}),before);
  }
}
console.log('All 9 browser market-risk scenarios passed');
'''
    result = subprocess.run([node, "-e", script, str(Path(__file__).resolve().parents[1] / "web/demo-engine.js")],
                            input=json.dumps(cases), text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
