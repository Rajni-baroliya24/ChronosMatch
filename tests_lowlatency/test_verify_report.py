import json
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    ("changes", "exit_code", "expected_message"),
    [
        ({}, 0, "PASS:"),
        ({"interrupted": True}, 1, "the run was interrupted"),
        ({"ledger_trades": 2}, 1, "emitted 3 trades but recorded 2"),
        (
            {"trades_ring": {"written": 3, "read": 2, "pending": 1}},
            1,
            "trades_ring did not drain",
        ),
    ],
    ids=["complete-run", "interrupted-run", "missing-ledger-trade", "pending-trade"],
)
def test_report_checker_cli(tmp_path, changes, exit_code, expected_message):
    report = {
        "interrupted": False,
        "requested_orders": 5,
        "orders_processed": 5,
        "trades_emitted": 3,
        "ledger_trades": 3,
        "orders_ring": {"written": 5, "read": 5, "pending": 0},
        "trades_ring": {"written": 3, "read": 3, "pending": 0},
    }
    report.update(changes)
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "lowlatency.verify_report", str(report_path)],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == exit_code, result.stderr
    if exit_code == 0:
        assert expected_message in result.stdout
    else:
        assert expected_message in result.stderr
        assert "PASS:" not in result.stdout