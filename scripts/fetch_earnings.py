#!/usr/bin/env python3
"""Fetch the upcoming earnings calendar, validate, atomically write
site/assets/earnings.json, and re-render the Earnings Today block.

Source: Nasdaq public earnings-calendar API
    https://api.nasdaq.com/api/calendar/earnings?date=YYYY-MM-DD
Each entry carries provenance (source name, source URL, fetched timestamp).
No invented data: any field the source does not supply is omitted (slot may
render as an em dash; entries missing symbol/company/date are dropped).

Fail-closed semantics:
  - If the fetch fails (network, HTTP error, bad JSON) the existing
    earnings.json is NOT touched and the run exits non-zero.
  - If validation finds zero usable entries, the existing file is NOT
    touched and the run exits non-zero.
  - The new payload is written to a temp file, re-validated from disk,
    then atomically renamed over the live file.

Usage:
    python3 scripts/fetch_earnings.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refresh_earnings import render_index  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "site" / "assets" / "earnings.json"
INDEX_PATH = ROOT / "site" / "index.html"

SOURCE_NAME = "Nasdaq earnings calendar (public API)"
API_URL = "https://api.nasdaq.com/api/calendar/earnings?date={date}"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

WINDOW_DAYS = 14          # forward window, inclusive of today
TODAY_MAX = 12            # cap on the "today" list, ranked by market cap
WEEKAHEAD_PER_DAY = 3     # cap per day in the "week ahead" list, by market cap

_SLOT_MAP = {
    "time-pre-market": "BMO",
    "time-after-hours": "AMC",
}


def fetch_day(day: date) -> list[dict]:
    """Return raw calendar rows for one date. Raises on any failure."""
    url = API_URL.format(date=day.isoformat())
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"fetch failed for {day.isoformat()}: {exc}") from exc
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"unexpected API shape for {day.isoformat()}")
    rows = data.get("rows") or []
    if not isinstance(rows, list):
        raise RuntimeError(f"unexpected rows shape for {day.isoformat()}")
    return rows


def _parse_money(raw: str | None) -> float | None:
    if not raw:
        return None
    neg = raw.strip().startswith("-")
    m = re.search(r"[\d,]+(?:\.\d+)?", raw)
    if not m:
        return None
    try:
        value = float(m.group(0).replace(",", ""))
    except ValueError:
        return None
    return -value if neg else value


def _parse_cap(raw: str | None) -> float:
    v = _parse_money(raw)
    return v if v is not None else 0.0


def _quote_link(ticker: str) -> str:
    # Deterministic link to the source's own quote page — never an IR URL we
    # have not verified. Provenance, not invention.
    return f"https://www.nasdaq.com/market-activity/stocks/{ticker.lower()}"


def parse_entry(row: dict, day_iso: str, fetched_at: str) -> dict | None:
    """Convert one API row to a schema entry, or None when it can't be sourced."""
    symbol = (row.get("symbol") or "").strip().upper()
    company = (row.get("company") or row.get("name") or "").strip()
    if not symbol or not company:
        return None
    eps = _parse_money(row.get("epsForecast"))
    slot = _SLOT_MAP.get((row.get("time") or "").strip().lower())
    entry = {
        "ticker": symbol,
        "company": company,
        "epsEst": eps,
        "actualEps": None,
        "slot": slot,  # None -> renders as an em dash; never guessed
        "link": _quote_link(symbol),
        "date": day_iso,
        "source": SOURCE_NAME,
        "sourceUrl": API_URL.format(date=day_iso),
        "fetchedAt": fetched_at,
    }
    return entry


def _rank(entries: list[dict], limit: int) -> list[dict]:
    ranked = sorted(entries, key=lambda e: e.pop("_cap"), reverse=True)
    return ranked[:limit]


def build_payload(today: date, rows_by_day: dict[str, list[dict]]) -> dict:
    fetched_at = datetime.now(timezone.utc).isoformat()
    today_iso = today.isoformat()
    today_entries: list[dict] = []
    week: list[dict] = []
    for day_iso, rows in sorted(rows_by_day.items()):
        parsed = []
        for row in rows:
            entry = parse_entry(row, day_iso, fetched_at)
            if entry is None:
                continue
            entry["_cap"] = _parse_cap(row.get("marketCap"))
            parsed.append(entry)
        if day_iso == today_iso:
            today_entries.extend(_rank(parsed, TODAY_MAX))
        else:
            for e in _rank(parsed, WEEKAHEAD_PER_DAY):
                d = date.fromisoformat(day_iso)
                e["dayLabel"] = d.strftime("%a, %b %-d")
                week.append(e)
    # strip internal ranking key
    for e in today_entries + week:
        e.pop("_cap", None)
    payload = {
        "date": today_iso,
        "dateLabel": today.strftime("%A, %B %-d"),
        "note": None,
        "thresholds": {
            "beat": 0.02,
            "bigBeat": 0.1,
            "bigMiss": -0.1,
            "miss": -0.02,
            "note": ("Surprise vs EPS estimate. >+10% = Big Beat, +2% to +10% = Beat, "
                     "within ±2% = In-line, -2% to -10% = Miss, worse than -10% = Big Miss."),
        },
        "today": today_entries,
        "weekAhead": week,
        "updatedAt": fetched_at,
        "provenance": {
            "source": SOURCE_NAME,
            "apiPattern": API_URL.format(date="YYYY-MM-DD"),
            "windowDays": WINDOW_DAYS,
            "note": ("Entries carry per-row source/sourceUrl/fetchedAt. "
                     "Fields the source does not supply (slot, estimate) are omitted, "
                     "never invented."),
        },
    }
    return payload


def validate(payload: dict, today: date) -> list[str]:
    """Return a list of validation errors (empty = valid)."""
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["payload is not an object"]
    if payload.get("date") != today.isoformat():
        errors.append(f"date {payload.get('date')!r} != run date {today.isoformat()}")
    lo, hi = today, today + timedelta(days=WINDOW_DAYS)
    usable = 0
    for key in ("today", "weekAhead"):
        items = payload.get(key) or []
        if not isinstance(items, list):
            errors.append(f"{key} is not a list")
            continue
        for i, e in enumerate(items):
            loc = f"{key}[{i}]"
            if not isinstance(e, dict):
                errors.append(f"{loc} is not an object")
                continue
            if not e.get("ticker"):
                errors.append(f"{loc} missing ticker")
                continue
            if not e.get("company"):
                errors.append(f"{loc} missing company")
                continue
            if not e.get("source"):
                errors.append(f"{loc} missing provenance source")
                continue
            try:
                d = date.fromisoformat(e.get("date", ""))
            except (ValueError, TypeError):
                errors.append(f"{loc} bad date {e.get('date')!r}")
                continue
            if not (lo <= d <= hi):
                errors.append(f"{loc} date {d.isoformat()} outside window")
                continue
            usable += 1
    if usable == 0:
        errors.append("zero usable entries — refusing to publish an empty feed")
    return errors


def atomic_write(path: Path, payload: dict) -> None:
    """Write via temp file + re-validate from disk, then atomic rename."""
    text = json.dumps(payload, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        # re-validate exactly what will go live
        reread = json.loads(Path(tmp).read_text(encoding="utf-8"))
        if reread != payload:
            raise RuntimeError("round-trip mismatch on temp file")
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    today = datetime.now(ZoneInfo("America/New_York")).date()
    errors: list[str] = []
    rows_by_day: dict[str, list[dict]] = {}
    for offset in range(WINDOW_DAYS + 1):
        day = today + timedelta(days=offset)
        try:
            rows_by_day[day.isoformat()] = fetch_day(day)
        except RuntimeError as exc:
            # Fail closed on any single-day fetch failure: a partial calendar
            # is still a broken calendar.
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
    payload = build_payload(today, rows_by_day)
    errors = validate(payload, today)
    if errors:
        for e in errors:
            print(f"ERROR: validation: {e}", file=sys.stderr)
        print("ERROR: refusing to overwrite site/assets/earnings.json", file=sys.stderr)
        return 2
    atomic_write(DATA_PATH, payload)
    render_index(INDEX_PATH, payload)
    n_today = len(payload["today"])
    n_week = len(payload["weekAhead"])
    print(f"COMMIT_MSG=Earnings feed - {today.isoformat()}")
    print(f"Earnings feed written: {n_today} today, {n_week} coming up "
          f"({DATA_PATH.name} @ {today.isoformat()}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
