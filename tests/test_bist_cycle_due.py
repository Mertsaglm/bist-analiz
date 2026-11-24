from datetime import datetime
import json
from pathlib import Path

from scripts.bist_cycle_due import decision

CFG = json.loads((Path(__file__).resolve().parents[1] / "advisor/config.json").read_text())


def check(at, snapshot):
    return decision(datetime.fromisoformat(at + "+03:00"), CFG, snapshot)[0]


def test_duplicate_calls_missing_data_and_next_slot():
    snapshot = {"market": "bist", "generated_at": "2026-11-19T07:17:00+00:00",
                "health": {"expected_quotes": 33, "quote_coverage": 33, "errors": []},
                "monitoring": {"phase": "entry"}}
    assert not check("2026-11-19T10:45", snapshot)
    assert check("2026-11-19T11:15", snapshot)
    snapshot["health"]["quote_coverage"] = 0
    assert check("2026-11-19T10:45", snapshot)
    assert check("2026-11-19T10:15", {})


def test_market_windows_and_holidays():
    assert not check("2026-11-19T10:00", {})
    assert not check("2026-11-19T20:00", {})
    assert not check("2026-11-21T11:00", {})
    assert not check("2026-10-29T11:00", {"monitoring": {"calendar": {"full_days": ["2026-10-29"]}}})


def test_delayed_close_or_stale_analysis_cannot_replace_a_trading_cycle():
    snapshot = {"market": "bist", "generated_at": "2026-11-24T07:17:00+00:00",
                "health": {"expected_quotes": 33, "quote_coverage": 33, "errors": []},
                "monitoring": {"phase": "valuation", "closing_refresh": True}}
    assert check("2026-11-24T10:45", snapshot)
    snapshot["monitoring"] = {"phase": "entry"}
    snapshot["health"]["analysis_issues"] = {"AKBNK": "Beklenen kapanış eksik"}
    assert check("2026-11-24T10:45", snapshot)
    snapshot["health"]["analysis_issues"] = {}
    assert not check("2026-11-24T10:45", snapshot)
