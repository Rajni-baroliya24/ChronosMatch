"""Verify the counts reported by a completed ChronosMatch pipeline run."""

import argparse
import json
from pathlib import Path


def count(record, key):
    value = record[key]
    if type(value) is not int or value < 0:
        raise ValueError(f"{key} must be a non-negative integer")
    return value


def verify(report):
    if report["interrupted"] is not False:
        raise ValueError("the run was interrupted")

    orders = count(report, "orders_processed")
    trades = count(report, "trades_emitted")
    ledger = count(report, "ledger_trades")

    if orders != count(report, "requested_orders"):
        raise ValueError("processed orders do not match requested orders")
    if trades != ledger:
        raise ValueError(f"emitted {trades} trades but recorded {ledger}")

    for name, expected in (("orders_ring", orders), ("trades_ring", trades)):
        ring = report[name]
        if count(ring, "pending") != 0:
            raise ValueError(f"{name} did not drain")
        if count(ring, "written") != expected or count(ring, "read") != expected:
            raise ValueError(f"{name} counts do not match the reported total")

    return orders, trades


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Path to a pipeline report.json")
    args = parser.parse_args()

    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
        orders, trades = verify(report)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"FAIL: {exc}\n")

    print(f"PASS: {orders:,} orders processed, {trades:,} trades recorded, both rings drained.")


if __name__ == "__main__":
    main()