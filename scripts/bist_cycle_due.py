"""Dış çağrı veya cron için son başarılı V2 çevriminin saatini kontrol eder."""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

IST = ZoneInfo("Europe/Istanbul")


def decision(now, cfg, snapshot):
    now = now.astimezone(IST)
    day = now.date().isoformat()
    calendar = snapshot.get("monitoring", {}).get("calendar", {})
    window = cfg["observation_window"]
    close_key = "half_day_close" if day in calendar.get("half_days", []) else "close"
    opening = datetime.fromisoformat(f"{day}T{window['open']}").replace(tzinfo=IST)
    closing = datetime.fromisoformat(f"{day}T{window[close_key]}").replace(tzinfo=IST)
    if now.weekday() >= 5 or day in calendar.get("full_days", []) or not opening <= now < closing:
        return False, "gözlem penceresi kapalı"

    interval = timedelta(minutes=cfg["cycle_interval_minutes"])
    slot = opening + ((now - opening) // interval) * interval
    try:
        at = datetime.fromisoformat(snapshot["generated_at"])
        health = snapshot["health"]
        complete = (snapshot["market"] == "bist" and at.tzinfo is not None
                    and slot <= at <= now and health["errors"] == []
                    and health["expected_quotes"] > 0
                    and health["quote_coverage"] == health["expected_quotes"]
                    and snapshot["monitoring"]["phase"] in ("entry", "protection", "valuation"))
    except (KeyError, ValueError, TypeError):
        complete = False
    return (False, "bu saatin çevrimi kayıtlı") if complete else (True, "saatlik çevrim gerekli")


if __name__ == "__main__":
    cfg = json.loads(Path("advisor/config.json").read_text())
    try:
        snapshot = json.loads(Path(sys.argv[1]).read_text())
    except (OSError, ValueError):
        snapshot = {}
    due, reason = decision(datetime.now(IST), cfg, snapshot if isinstance(snapshot, dict) else {})
    print(reason, file=sys.stderr)
    print("true" if due else "false")
