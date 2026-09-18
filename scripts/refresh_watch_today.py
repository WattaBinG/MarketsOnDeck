#!/usr/bin/env python3
"""Refresh site/assets/watch-today.json for the next US trading day.

Deterministic sources only, no AI:
  - NYSE 2026 holiday calendar (verified against nyse.com/markets/hours-calendars)
  - 2026 FOMC meeting calendar (federalreserve.gov/monetarypolicy/fomccalendars.htm)
  - Recurring weekly events (Baker Hughes rig count, CFTC Commitments of Traders)
  - BEA release calendar (official ICS feed, bea.gov/news/schedule/ics)

If a trading day has no known events, the file is left unchanged rather than
blanked (the existing as-of date on the page shows its age honestly).
"""
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "assets" / "watch-today.json"
ET = ZoneInfo("America/New_York")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# NYSE 2026 full-day closures (nyse.com/markets/hours-calendars, checked 2026-09-18)
HOLIDAYS_2026 = {
    date(2026, 1, 1), date(2026, 1, 19), date(2026, 2, 16), date(2026, 4, 3),
    date(2026, 5, 25), date(2026, 6, 19), date(2026, 7, 3), date(2026, 9, 7),
    date(2026, 11, 26), date(2026, 12, 25),
}
# 2026 FOMC decision days (2nd day of each meeting; federalreserve.gov calendar)
FOMC_2026 = {
    date(2026, 1, 28), date(2026, 3, 18), date(2026, 4, 29), date(2026, 6, 17),
    date(2026, 7, 29), date(2026, 9, 16), date(2026, 10, 28), date(2026, 12, 9),
}


def is_trading_day(d):
    return d.weekday() < 5 and d not in HOLIDAYS_2026


def next_trading_day(d):
    d = d + timedelta(days=1)
    while not is_trading_day(d):
        d += timedelta(days=1)
    return d


def third_friday(d):
    return d.weekday() == 4 and 15 <= d.day <= 21


def bea_events(target):
    """Official BEA ICS feed -> [(label, 'h:mm AM/PM ET')] for target date."""
    req = Request("https://www.bea.gov/news/schedule/ics/online-calendar-subscription.ics",
                  headers={"User-Agent": UA})
    try:
        with urlopen(req, timeout=20) as r:
            ics = r.read().decode("utf-8", "replace")
    except Exception as e:
        print(f"BEA feed failed: {e}", file=sys.stderr)
        return []
    ics = ics.replace("\r\n ", "").replace("\r\n\t", "")
    out = []
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", ics, re.S):
        m = re.search(r"DTSTART[^:]*:(\d{8})(?:T(\d{6})Z?)?", block)
        s = re.search(r"SUMMARY[^:]*:(.+)", block)
        if not m or not s:
            continue
        d = date(int(m.group(1)[:4]), int(m.group(1)[4:6]), int(m.group(1)[6:8]))
        if d != target:
            continue
        if m.group(2):
            dt = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
            t = dt.astimezone(ET)
        else:
            t = datetime(target.year, target.month, target.day, 8, 30, tzinfo=ET)  # BEA releases 8:30 AM ET
        label = re.sub(r"\\([,;])", r"\1", s.group(1)).strip()
        out.append((t.strftime("%-I:%M %p ET"), label, t))
    return out


def main():
    today = datetime.now(ET).date()
    target = next_trading_day(today)
    events = []
    if target in FOMC_2026:
        events.append(("2:00 PM ET", "FOMC Rate Decision", None))
    # FOMC minutes: three weeks after each decision day (matches the Fed's
    # published 2026 release dates: Jan 28->Feb 18, Mar 18->Apr 8,
    # Apr 29->May 20, Jun 17->Jul 8).
    if any(target == d + timedelta(days=21) for d in FOMC_2026):
        events.append(("2:00 PM ET", "FOMC Minutes", None))
    if target.weekday() == 2:  # Wednesday
        events.append(("10:30 AM ET", "EIA Weekly Petroleum Status Report", None))
    if target.weekday() == 3:  # Thursday
        events.append(("8:30 AM ET", "Initial Jobless Claims", None))
        events.append(("10:30 AM ET", "EIA Weekly Natural Gas Storage Report", None))
    if target.weekday() == 4:
        events.append(("1:00 PM ET", "Baker Hughes Rig Count", None))
        events.append(("3:30 PM ET", "CFTC Commitments of Traders", None))
        if target.month in (3, 6, 9, 12) and third_friday(target):
            events.append(("3:00 PM ET", "Quad Witching Expiration", None))
    events.extend(bea_events(target))
    if not events:
        print(f"no known events for {target}; leaving file unchanged")
        return
    def key(ev):
        m = re.match(r"(\d+):(\d+) (AM|PM)", ev[0])
        h = int(m.group(1)) % 12 + (12 if m.group(3) == "PM" else 0)
        return h * 60 + int(m.group(2))
    events.sort(key=key)
    out = {
        "date": target.isoformat(),
        "dateLabel": target.strftime("%A, %B ") + str(target.day),
        "events": [{"time": t, "event": e} for t, e, _ in events],
        "calendarUrl": "https://www.investing.com/economic-calendar/",
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"OK: {out['dateLabel']}: " + "; ".join(f"{t} {e}" for t, e, _ in events))
    print(f"COMMIT_MSG=Refresh What to Watch Today (next trading day): {out['dateLabel']}")


if __name__ == "__main__":
    main()
