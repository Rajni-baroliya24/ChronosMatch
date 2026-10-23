"""Cancellation, execution history and FIFO must survive repeated restarts."""

from contextlib import contextmanager

import pytest

from src.service import TradingService


PERSISTED_FIELDS = (
    "orders", "trades", "history", "bids", "asks", "total_orders",
    "total_trades", "active_orders", "matched_shares", "volume", "vwap",
)


@contextmanager
def workspace(path):
    service = TradingService(path, seed=False)
    try:
        yield service
    finally:
        service.db.close()


def limit_order(service, side, quantity):
    return service.submit({
        "symbol": "AAPL", "side": side, "type": "LIMIT",
        "price": "100.00", "quantity": quantity,
    })


@pytest.mark.parametrize("resting_side", ["BUY", "SELL"])
@pytest.mark.parametrize(
    "cancel_index",
    [
        pytest.param(0, id="partially-filled-head"),
        pytest.param(1, id="unfilled-middle"),
    ],
)
def test_cancellation_and_fifo_survive_repeated_restarts(
    tmp_path, resting_side, cancel_index
):
    path = tmp_path / "cancel-replay.sqlite3"
    opposite = "SELL" if resting_side == "BUY" else "BUY"
    own_depth = "bids" if resting_side == "BUY" else "asks"
    resting_id_key = "buy_order_id" if resting_side == "BUY" else "sell_order_id"

    with workspace(path) as first:
        # Three equal-price orders must retain their arrival priority.
        resting = [limit_order(first, resting_side, 5) for _ in range(3)]
        limit_order(first, opposite, 2)
        assert resting[0]["filled"] == 2

        cancelled_id = resting[cancel_index]["id"]
        first.cancel(cancelled_id)
        before = first.snapshot("AAPL")
        next_id = first.next_id
        assert before["total_trades"] == 1
        assert before["matched_shares"] == 2
        assert before[own_depth] == [{
            "price": 100.0, "quantity": 10 if cancel_index == 0 else 8,
        }]

    # Closing and reopening a real SQLite file exercises persisted event replay.
    with workspace(path) as second:
        replayed = second.snapshot("AAPL")
        for key in PERSISTED_FIELDS:
            assert replayed[key] == before[key], key
        assert second.next_id == next_id
        cancelled = second.orders[cancelled_id]
        assert cancelled["status"] == "CANCELLED"
        assert cancelled["remaining"] == 0
        assert cancelled["filled"] == (2 if cancel_index == 0 else 0)

        first_survivor = resting[1]["id"] if cancel_index == 0 else resting[0]["id"]
        first_quantity = 5 if cancel_index == 0 else 3
        incoming = limit_order(second, opposite, first_quantity + 1)
        assert incoming["id"] == next_id
        assert incoming["status"] == "FILLED"

        # Earlier fills stay recorded; new fills skip the cancelled remainder.
        assert second.trades[0] == before["trades"][0]
        assert [(t[resting_id_key], t["quantity"]) for t in second.trades[1:]] == [
            (first_survivor, first_quantity), (resting[2]["id"], 1),
        ]
        after = second.snapshot("AAPL")
        assert after["total_trades"] == 3
        assert after["matched_shares"] == 2 + first_quantity + 1
        assert after["volume"] == 100 * after["matched_shares"]
        assert after["vwap"] == 100.0
        assert after["active_orders"] == 1
        assert after[own_depth] == [{"price": 100.0, "quantity": 4}]
        assert second.orders[cancelled_id]["status"] == "CANCELLED"

    # A second replay must preserve both the cancellation and the later trades.
    with workspace(path) as third:
        final = third.snapshot("AAPL")
        for key in PERSISTED_FIELDS:
            assert final[key] == after[key], key
        assert third.next_id == incoming["id"] + 1
