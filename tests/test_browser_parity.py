"""Optional differential check: browser matcher versus the actual Python service."""
import json
from pathlib import Path
import random
import shutil
import subprocess
import pytest
from src.service import TradingService


def test_browser_and_python_matcher_agree_on_mixed_workload():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is optional; needed only for browser/Python parity check")
    service = TradingService(seed=False)
    rng = random.Random(42)
    operations = []
    for _ in range(250):
        active = [o for o in service.orders.values() if o["status"] in ("OPEN", "PARTIAL")]
        if active and rng.random() < .15:
            oid = rng.choice(active)["id"]
            service.cancel(oid)
            operations.append(dict(kind="cancel", id=oid))
        else:
            data = dict(symbol=rng.choice(["AAPL", "MSFT"]), side=rng.choice(["BUY", "SELL"]),
                        type="MARKET" if rng.random() < .2 else "LIMIT",
                        price=f"{100 + rng.randrange(-10, 11) / 100:.2f}", quantity=rng.randrange(1, 30))
            try:
                service.submit(data)
            except ValueError:
                continue
            operations.append(dict(kind="submit", data=data))
    def normalize(snapshot):
        return dict(orders=[{k: o[k] for k in ("id", "symbol", "side", "type", "price", "quantity", "filled", "remaining", "status")} for o in snapshot["orders"]],
                    trades=[{k: t[k] for k in ("id", "symbol", "side", "price", "quantity", "buy_order_id", "sell_order_id")} for t in snapshot["trades"]],
                    bids=snapshot["bids"], asks=snapshot["asks"])
    expected = {s: normalize(service.snapshot(s)) for s in ("AAPL", "MSFT")}
    script = r'''
const fs=require('node:fs');
const {DemoEngine}=require(process.argv[1]);
const engine=new DemoEngine(null,{seed:false});
for(const op of JSON.parse(fs.readFileSync(0,'utf8'))){if(op.kind==='cancel')engine.cancel(op.id);else engine.submit(op.data)}
const keys=(obj, fields)=>Object.fromEntries(fields.map(k=>[k,obj[k]]));
const normalize=s=>({orders:s.orders.map(o=>keys(o,['id','symbol','side','type','price','quantity','filled','remaining','status'])),trades:s.trades.map(t=>keys(t,['id','symbol','side','price','quantity','buy_order_id','sell_order_id'])),bids:s.bids,asks:s.asks});
process.stdout.write(JSON.stringify(Object.fromEntries(['AAPL','MSFT'].map(s=>[s,normalize(engine.snapshot(s))]))));
'''
    result = subprocess.run([node, "-e", script, str(Path(__file__).resolve().parents[1] / "web" / "demo-engine.js")], input=json.dumps(operations), text=True, capture_output=True, check=True)
    service.db.close()
    assert json.loads(result.stdout) == expected
