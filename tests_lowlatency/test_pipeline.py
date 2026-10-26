import json
from pathlib import Path
import sqlite3
import pytest
from lowlatency.pipeline import run
from lowlatency.simulator import fields
from src.models import Order
from src.order_book import OrderBook
from lowlatency.protocol import SYMBOLS


@pytest.mark.parametrize('source', ['direct', 'websocket'])
def test_three_process_pipeline_reconciles_with_python_reference(native_book, tmp_path, source):
    report = run(count=205, rate=0, capacity=7, output=tmp_path, source=source)
    assert report['orders_processed'] == 205
    assert report['whale_sweeps'] == 41
    assert report['orders_ring'] == {'written': 205, 'read': 205, 'pending': 0}
    assert report['trades_ring']['pending'] == 0
    books = [OrderBook(symbol) for symbol in SYMBOLS]
    expected = []
    for oid in range(1, 206):
        _, symbol, side, price, quantity = fields(oid)
        for trade in books[symbol].submit(Order(oid, SYMBOLS[symbol], 'BUY' if side == 1 else 'SELL', price, quantity, oid)):
            expected.append((trade.buy_order_id, trade.sell_order_id, symbol, trade.price, trade.quantity))
    folder = Path(report['output_directory'])
    with sqlite3.connect(folder / 'ledger.sqlite3') as connection:
        persisted = connection.execute('SELECT buy_order_id,sell_order_id,symbol,price_ticks,quantity FROM trades ORDER BY trade_id').fetchall()
        assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert persisted == expected
    assert report['ledger_trades'] == len(expected)
    assert json.loads((folder / 'report.json').read_text()) == report
    assert (folder / 'latency_samples.u64').stat().st_size == 205 * 16


def test_output_runs_do_not_overwrite_existing_ledger(native_book, tmp_path):
    first = run(count=5, rate=0, capacity=1, output=tmp_path)
    path = Path(first['output_directory']) / 'ledger.sqlite3'
    before = path.read_bytes()
    second = run(count=5, rate=0, capacity=1, output=tmp_path)
    assert first['output_directory'] != second['output_directory']
    assert path.read_bytes() == before
