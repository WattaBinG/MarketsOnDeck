#!/usr/bin/env python3
"""Render the Earnings Today block into site/index.html.

Reads site/assets/earnings.json (seeded each morning by scripts/fetch_earnings.py
from the Nasdaq public earnings-calendar API — ticker, company, BMO/AMC slot,
EPS estimate, source quote link, and per-entry provenance) and renders the
earnings box between the EARNINGS_TODAY_START / EARNINGS_TODAY_END markers
in site/index.html.

After earnings print during the day, the routine fills in actualEps values and
re-runs this script; badges (Big Beat / Beat / In-line / Miss / Big Miss) are
computed from the surprise vs the estimate. Fail-closed: no badge is shown
unless BOTH an actual and an estimate are present.

Usage:
    python3 scripts/refresh_earnings.py                      # render from earnings.json
    python3 scripts/refresh_earnings.py --actual NKE=0.50     # fill an actual, then render
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "site" / "assets" / "earnings.json"
INDEX_PATH = ROOT / "site" / "index.html"

MARK_START = "<!-- EARNINGS_TODAY_START"
MARK_END = "<!-- EARNINGS_TODAY_END -->"

# Badge thresholds: surprise = (actual - estimate) / |estimate|.
# Boundary values belong to the non-"Big" band: exactly +10% is a Beat,
# exactly -10% is a Miss.
BIG_BEAT_SURPRISE = 0.10   # strictly greater than +10% over estimate
BEAT_SURPRISE = 0.02        # +2% to +10% over estimate
INLINE_BAND = 0.02          # within ±2% of estimate
BIG_MISS_SURPRISE = -0.10   # strictly worse than -10% under estimate
# anything else with both values present: Miss (-2% to -10%)

# Tolerance so float noise (e.g. 0.10000000000000009) can't flip a band
# when the true value sits exactly on a boundary.
_BOUNDARY_TOL = 1e-9


def badge_for(actual: float | None, estimate: float | None) -> str | None:
    """Return the surprise badge, or None when no badge can be computed."""
    if actual is None or estimate is None or estimate == 0:
        return None
    surprise = (actual - estimate) / abs(estimate)
    if surprise > BIG_BEAT_SURPRISE + _BOUNDARY_TOL:
        return "Big Beat"
    if surprise >= BEAT_SURPRISE - _BOUNDARY_TOL:
        return "Beat"
    if surprise >= -INLINE_BAND - _BOUNDARY_TOL:
        return "In-line"
    if surprise >= BIG_MISS_SURPRISE - _BOUNDARY_TOL:
        return "Miss"
    return "Big Miss"


_BADGE_CLASS = {
    "Big Beat": "earn-badge-big-beat",
    "Beat": "earn-badge-beat",
    "In-line": "earn-badge-inline",
    "Miss": "earn-badge-miss",
    "Big Miss": "earn-badge-big-miss",
}

# Reusable plain-English legend for the market jargon in this block.
LEGEND_HTML = (
    '<div class="legend">'
    "*BMO = Before Market Open &middot; AMC = After Market Close &middot; "
    "EPS = earnings per share"
    "<br>"
    "*Beat/Miss vs the EPS estimate: Big Beat &gt;+10% &middot; "
    "Beat +2&ndash;10% &middot; In-line &plusmn;2% &middot; "
    "Miss &minus;2&ndash;10% &middot; Big Miss &lt;&minus;10%"
    "</div>"
)


def _eps(actual: float | None, estimate: float | None) -> str:
    def fmt(v: float | None) -> str:
        return f"${v:.2f}" if v is not None else "&mdash;"
    return f"Est: {fmt(estimate)} &middot; Act: {fmt(actual)}"


def _row(r: dict) -> str:
    ticker = html.escape(r["ticker"])
    company = html.escape(r["company"])
    # slot is None when the source does not supply timing — never guessed.
    slot = html.escape(r["slot"]) if r.get("slot") else "&mdash;"
    link = html.escape(r["link"], quote=True)
    badge = badge_for(r.get("actualEps"), r.get("epsEst"))
    badge_html = (
        f'<span class="earn-badge {_BADGE_CLASS[badge]}">{badge}</span>'
        if badge else ""
    )
    return (
        f'    <li><span class="earn-slot">{slot}</span>'
        f'<span class="earn-id"><a class="earn-ticker" href="{link}" '
        f'target="_blank" rel="noopener">{ticker}</a>'
        f'<span class="earn-name">{company}</span></span>'
        f'<span class="earn-eps">{_eps(r.get("actualEps"), r.get("epsEst"))}</span>'
        f"{badge_html}</li>"
    )


def _week_row(r: dict) -> str:
    return (
        f'    <li><span class="earn-week-day">{html.escape(r["dayLabel"])}</span>'
        f'<a class="earn-ticker" href="{html.escape(r["link"], quote=True)}" '
        f'target="_blank" rel="noopener">{html.escape(r["ticker"])}</a>'
        f'<span class="earn-slot">{html.escape(r["slot"]) if r.get("slot") else "&mdash;"}</span></li>'
    )


def render_earnings_block(data: dict, today: str | None = None) -> str:
    """Render the full EARNINGS_TODAY marker block from the data file."""
    today = today or datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    if data["date"] != today:
        date = html.escape(data["date"])
        return (MARK_START + " -->\n" + f'<div class="earn-box data-stale" data-earn-date="{date}">' +
                '<div class="earn-box-header">Earnings</div>' +
                f'<div class="earn-box-date">No current earnings feed. Last schedule: {date}</div></div>\n' + MARK_END)
    lines = [
        "<!-- EARNINGS_TODAY_START — rendered by scripts/refresh_earnings.py "
        "from site/assets/earnings.json; keep the markers for clean find/replace -->",
        f'<div class="earn-box" data-earn-date="{html.escape(data["date"])}">',
        '  <div class="earn-box-header">Earnings Today</div>',
        f'  <div class="earn-box-date">{html.escape(data["dateLabel"])}</div>',
        '  <ul class="earn-list">',
    ]
    for r in data["today"]:
        lines.append(_row(r))
    lines.append("  </ul>")
    if data.get("weekAhead"):
        lines.append('  <div class="earn-week">')
        lines.append('    <div class="earn-week-header">Coming up</div>')
        lines.append('    <ul class="earn-week-list">')
        for r in data["weekAhead"]:
            lines.append(_week_row(r))
        lines.append("    </ul>")
        lines.append("  </div>")
    lines.append(LEGEND_HTML)
    lines.append("</div>")
    lines.append(MARK_END)
    return "\n".join(lines)


def render_index(index_path: Path, data: dict) -> bool:
    """Replace the EARNINGS_TODAY block in index.html. Returns True on success."""
    text = index_path.read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(MARK_START) + r".*?" + re.escape(MARK_END),
        re.DOTALL,
    )
    matches = pattern.findall(text)
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly 1 EARNINGS_TODAY block in {index_path}, "
            f"found {len(matches)} — refusing to touch the file."
        )
    block = render_earnings_block(data)
    text = pattern.sub(lambda _m: block, text, count=1)
    index_path.write_text(text, encoding="utf-8")
    return True


def set_actual(data: dict, ticker: str, actual: float) -> None:
    ticker = ticker.upper()
    for r in data["today"] + data.get("weekAhead", []):
        if r["ticker"].upper() == ticker:
            r["actualEps"] = actual
            data["updatedAt"] = datetime.now(timezone.utc).isoformat()
            return
    raise KeyError(f"Ticker {ticker} not found in earnings.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render the Earnings Today block.")
    parser.add_argument(
        "--actual",
        action="append",
        default=[],
        metavar="TICKER=EPS",
        help="Fill in a reported actual EPS before rendering (repeatable).",
    )
    args = parser.parse_args(argv)

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    for item in args.actual:
        if "=" not in item:
            raise SystemExit(f"--actual expects TICKER=EPS, got: {item!r}")
        ticker, raw = item.split("=", 1)
        set_actual(data, ticker.strip(), float(raw.strip()))
        DATA_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    render_index(INDEX_PATH, data)
    print(f"Earnings block rendered from {DATA_PATH.name} ({data['date']}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
