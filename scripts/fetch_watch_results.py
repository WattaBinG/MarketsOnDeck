#!/usr/bin/env python3
"""Post actual prints into the Watch Today calendar (TradingView-style).

Today's events carry a numbers line - "Act: - | Cons: - | Prev: X" - from
the calendar build (refresh_watch_today.py). Once an event's ET time
passes and the official source has published, this fills in the Act.
Consensus stays blank: surveys are licensed data with no keyless source.
Fail-closed everywhere: no number is ever guessed, and a stale print can
never post as today's (the release's reference month must equal the API's
latest period).

Keyless source (2026-09-22, verified live): BLS Public Data API v2 without
a registration key (25 queries/day - at most one per run, only when a
mappable event needs its actual). DOL weekly claims PDF and EIA WPSR JSON are public without keys and
are guarded by release date and reporting week. BEA GDP/PCE and EIA gas are covered through official releases with strict
publication/reference dates. Unmapped events stay struck through without actuals.
"""
import html, json, re, sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import econ_series as es
import econ_official as official
import econ_bea as bea

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "site" / "index.html"
WATCH_JSON = ROOT / "site" / "assets" / "watch-today.json"
ET = ZoneInfo("America/New_York")


def main():
    today = datetime.now(ET).date()
    doc_html = INDEX.read_text(encoding="utf-8")
    m = re.search(r'(<!-- WATCH_TODAY_START.*?<!-- WATCH_TODAY_END -->)', doc_html, re.S)
    if not m: print("no watch box; nothing to do"); return
    block = m.group(1)
    dm = re.search(r'data-watch-date="(\d{4}-\d{2}-\d{2})"', block)
    if not dm or dm.group(1) != today.isoformat():
        print(f"box date {dm.group(1) if dm else '?'} != today {today}; nothing to do"); return

    now_min = datetime.now(ET).hour * 60 + datetime.now(ET).minute
    lis = re.findall(r"<li>.*?</li>", block, re.S)
    work = []  # (li, event, kind)
    for li in lis:
        if "watch-actual" in li: continue  # already has an actual
        tm = re.search(r'watch-time">(\d{1,2}):(\d{2})\s*(AM|PM)', li)
        ev = re.search(r'watch-event">([^<]+)<', li)
        if not tm or not ev: continue
        h = int(tm.group(1)) % 12 + (12 if tm.group(3) == "PM" else 0)
        if h * 60 + int(tm.group(2)) > now_min: continue  # hasn't passed yet
        kind = es.kind_for(ev.group(1).strip()) or official.kind_for(ev.group(1).strip()) or bea.kind_for(ev.group(1).strip())
        if kind: work.append((li, ev.group(1).strip(), kind))
    if not work:
        print("no passed mappable events awaiting actuals; nothing to do"); return

    needed = sorted({sid for _, _, kind in work if kind in es.SERIES_FOR for sid in es.SERIES_FOR[kind]})
    data = {}
    if needed:
        try:
            data = es.bls(needed)
        except Exception as e:
            print(f"FAILED(closed): BLS fetch: {e}")

    changed = False
    actuals = {}
    for li, event, kind in work:
        try:
            actual = (es.fmt_actual(kind, data, today) if kind in es.SERIES_FOR
                      else bea.value(kind, event, today) if kind in ("gdp", "pce")
                      else official.value(kind, today, actual=True))
        except Exception as e:
            print(f"FAILED(closed): {event}: {e}"); continue
        safe_actual = html.escape(actual)
        updated = li.replace('</span></span><span class="watch-event">',
                             f'</span><span class="watch-actual">Act: {safe_actual}</span></span><span class="watch-event">', 1)
        if updated == li:
            print(f"FAILED(closed): {event}: unexpected watch markup"); continue
        block = block.replace(li, updated)
        actuals[event] = actual
        changed = True
        print(f"OK: {event} -> Act: {actual}")
    if not changed: return

    INDEX.write_text(doc_html.replace(m.group(1), block), encoding="utf-8")
    try:
        wj = json.loads(WATCH_JSON.read_text(encoding="utf-8"))
        for ev in wj.get("events", []):
            if ev.get("event") in actuals:
                ev["actual"] = actuals[ev["event"]]
        WATCH_JSON.write_text(json.dumps(wj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except Exception as e:
        print(f"note: watch-today.json not updated ({e}); HTML already updated")
    print("RESULTS_UPDATED")


if __name__ == "__main__":
    main()
