"""Official economic series shared by the watch-calendar scripts.

Keyless source: BLS Public Data API v2 without a registration key
(25 queries/day, verified live 2026-09-22). Event->series mapping is
deliberately small and conservative; unmapped events render plain.
All callers fail closed: a fetch or validation error means no number,
never a guessed one.
"""
import json, re
from urllib.request import Request, urlopen

BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
UA = "MarketsOnDeck calendar bot (+https://marketsondeck.wattabing.workers.dev)"

MAPPINGS = [
    (re.compile(r"employment situation", re.I), "jobs"),
    (re.compile(r"consumer price", re.I), "cpi"),
    (re.compile(r"producer price", re.I), "ppi"),
]
SERIES_FOR = {"jobs": ["CES0000000001", "LNS14000000"],
              "cpi": ["CUSR0000SA0"],
              "ppi": ["WPSFD4"]}


def kind_for(event_label):
    return next((k for rx, k in MAPPINGS if rx.search(event_label)), None)


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


def _mom(pts):
    if len(pts) < 2: raise RuntimeError("series too short")
    return (pts[0]["value"] / pts[1]["value"] - 1) * 100


def _period(pts):
    return (pts[0]["year"], pts[0]["month"])


def fmt_prev(kind, data):
    """The last official print - the 'Prev' column at calendar-build time."""
    if kind == "jobs":
        pay = data["CES0000000001"]
        if len(pay) < 2: raise RuntimeError("payrolls too short")
        delta = pay[0]["value"] - pay[1]["value"]
        if abs(delta) > 2000: raise RuntimeError(f"payroll delta {delta}K insane")
        return f"{delta:+.0f}K"
    if kind in ("cpi", "ppi"):
        mom = _mom(data[SERIES_FOR[kind][0]])
        if abs(mom) > 3: raise RuntimeError(f"{kind} m/m {mom}% insane")
        return f"{mom:+.1f}%"
    raise RuntimeError(f"unknown kind {kind}")


def fmt_actual(kind, data, today):
    """Today's just-released print - only when the API's latest period is the
    reference month this release covers (previous month for jobs/CPI/PPI),
    so a stale print can never post as today's."""
    ref = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
    if kind == "jobs":
        pay, unemp = data["CES0000000001"], data["LNS14000000"]
        if len(pay) < 2 or not unemp: raise RuntimeError("jobs series too short")
        if _period(pay) != ref: raise RuntimeError(f"payrolls latest {pay[0]['year']}-M{pay[0]['month']:02d} != expected {ref}")
        delta = pay[0]["value"] - pay[1]["value"]
        if abs(delta) > 2000: raise RuntimeError(f"payroll delta {delta}K insane")
        if _period(unemp) != ref: raise RuntimeError("unemployment not current")
        return f"payrolls {delta:+.0f}K, unemployment {unemp[0]['value']:.1f}%"
    if kind in ("cpi", "ppi"):
        sid = SERIES_FOR[kind][0]
        pts = data[sid]
        if _period(pts) != ref: raise RuntimeError(f"{sid} latest {pts[0]['year']}-M{pts[0]['month']:02d} != expected {ref}")
        mom = _mom(pts)
        if abs(mom) > 3: raise RuntimeError(f"{kind} m/m {mom}% insane")
        label = "CPI" if kind == "cpi" else "PPI"
        return f"{label} {mom:+.1f}% m/m"
    raise RuntimeError(f"unknown kind {kind}")
