#!/usr/bin/env python3
"""Post actual prints next to passed events in the Watch Today box.

Reads the watch box in site/index.html, finds today's events whose ET time
has passed, and fills in the official result for the ones with a verified
keyless source. Everything else stays a bare strikethrough - fail closed,
never guess, never republish a stale print as today's.

Keyless source (2026-09-22, verified live): BLS Public Data API v2 without
a registration key (25 queries/day - we burn at most one, only when a
mappable event needs a result). EIA/BEA need keys; FOMC has no numeric
print; those events are intentionally unmapped until a verified free path
exists.

Honesty guards, all fail-closed:
- the release's reference month must equal the latest period the API
  returns (otherwise the API hasn't published today's print yet - skip)
- computed deltas must be sane (payrolls within +/-2,000K, CPI/PPI m/m
  within +/-3%) or the print is skipped
- any API/parse error leaves the box untouched and just logs
"""
import json, re, sys
from datetime import datetime, date
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "site" / "index.html"
WATCH_JSON = ROOT / "site" / "assets" / "watch-today.json"
ET = ZoneInfo("America/New_York")
UA = "MarketsOnDeck results bot (+https://marketsondeck.wattabing.workers.dev)"
BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

# event label regex -> (series needed, formatter name). Unmapped = no result.
MAPPINGS = [
    (re.compile(r"employment situation", re.I), "jobs"),
    (re.compile(r"consumer price", re.I), "cpi"),
    (re.compile(r"producer price", re.I), "ppi"),
]
SERIES_FOR = {"jobs": ["CES0000000001", "LNS14000000"],
              "cpi": ["CUSR0000SA0"],
              "ppi": ["WPSFD4"]}


def bls(series_ids):
    body = json.dumps({"seriesid": series_ids}).encode()
    req = Request(BLS_URL, data=body, headers={"User-Agent": UA, "Content-Type": "application/json"})
    with urlopen(req, timeout=25) as r:
        d = json.loads(r.read().decode())
    if d.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(f"BLS status {d.get('status')}: {d.get('message')}")
    out = {}
    for s in d["Results"]["series"]:
        pts = []
        for p in s["data"]:
            per = p["period"]
            if not per.startswith("M") or per == "M13": continue  # M13 = annual average
            try: pts.append({"year": int(p["year"]), "month": int(per[1:]), "value": float(p["value"])})
            except ValueError: continue  # BLS uses "-" for unavailable cells
        pts.sort(key=lambda p: (p["year"], p["month"]), reverse=True)
        out[s["seriesID"]] = pts
    return out


def expected_ref_month(today):
    return (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)


def fmt(kind, data, today):
    ref = expected_ref_month(today)
    if kind == "jobs":
        pay, unemp = data["CES0000000001"], data["LNS14000000"]
        if len(pay) < 2 or not unemp: raise RuntimeError("jobs series too short")
        if (pay[0]["year"], pay[0]["month"]) != ref: raise RuntimeError(f"payrolls latest {pay[0]['year']}-M{pay[0]['month']:02d} != expected {ref}")
        delta = pay[0]["value"] - pay[1]["value"]
        if abs(delta) > 2000: raise RuntimeError(f"payroll delta {delta}K insane")
        if (unemp[0]["year"], unemp[0]["month"]) != ref: raise RuntimeError("unemployment not current")
        return f"Actual: payrolls {delta:+.0f}K, unemployment {unemp[0]['value']:.1f}%"
    if kind in ("cpi", "ppi"):
        sid = SERIES_FOR[kind][0]
        pts = data[sid]
        if len(pts) < 2: raise RuntimeError(f"{sid} too short")
        if (pts[0]["year"], pts[0]["month"]) != ref: raise RuntimeError(f"{sid} latest {pts[0]['year']}-M{pts[0]['month']:02d} != expected {ref}")
        mom = (pts[0]["value"] / pts[1]["value"] - 1) * 100
        if abs(mom) > 3: raise RuntimeError(f"{kind} m/m {mom}% insane")
        label = "CPI" if kind == "cpi" else "PPI"
        return f"Actual: {label} {mom:+.1f}% m/m"
    raise RuntimeError(f"unknown kind {kind}")


def main():
    today = datetime.now(ET).date()
    html = INDEX.read_text(encoding="utf-8")
    m = re.search(r'(<!-- WATCH_TODAY_START.*?<!-- WATCH_TODAY_END -->)', html, re.S)
    if not m: print("no watch box; nothing to do"); return
    block = m.group(1)
    dm = re.search(r'data-watch-date="(\d{4}-\d{2}-\d{2})"', block)
    if not dm or dm.group(1) != today.isoformat():
        print(f"box date {dm.group(1) if dm else '?'} != today {today}; nothing to do"); return

    now_min = datetime.now(ET).hour * 60 + datetime.now(ET).minute
    lis = re.findall(r"<li>.*?</li>", block, re.S)
    work = []  # (li, time_str, event, kind)
    for li in lis:
        if "watch-result" in li: continue
        tm = re.search(r'watch-time">(\d{1,2}):(\d{2})\s*(AM|PM)', li)
        ev = re.search(r'watch-event">([^<]+)<', li)
        if not tm or not ev: continue
        h = int(tm.group(1)) % 12 + (12 if tm.group(3) == "PM" else 0)
        if h * 60 + int(tm.group(2)) > now_min: continue  # hasn't passed yet
        event = ev.group(1).strip()
        kind = next((k for rx, k in MAPPINGS if rx.search(event)), None)
        if kind: work.append((li, event, kind))
    if not work:
        print("no passed mappable events lacking results; nothing to do"); return

    needed = sorted({sid for _, _, kind in work for sid in SERIES_FOR[kind]})
    try:
        data = bls(needed)
    except Exception as e:
        print(f"FAILED(closed): BLS fetch: {e}"); return

    changed = False
    for li, event, kind in work:
        try:
            result = fmt(kind, data, today)
        except Exception as e:
            print(f"FAILED(closed): {event}: {e}"); continue
        new_li = li.replace("</li>", f'<span class="watch-result">{result}</span></li>')
        block = block.replace(li, new_li)
        changed = True
        print(f"OK: {event} -> {result}")
    if not changed: return

    html = html.replace(m.group(1), block)
    INDEX.write_text(html, encoding="utf-8")
    try:
        wj = json.loads(WATCH_JSON.read_text(encoding="utf-8"))
        for ev in wj.get("events", []):
            kind = next((k for rx, k in MAPPINGS if rx.search(ev.get("event", ""))), None)
            if kind and "actual" not in ev:
                try: ev["actual"] = fmt(kind, data, today)
                except Exception: pass
        WATCH_JSON.write_text(json.dumps(wj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except Exception as e:
        print(f"note: watch-today.json not updated ({e}); HTML already updated")
    print("RESULTS_UPDATED")


if __name__ == "__main__":
    main()
