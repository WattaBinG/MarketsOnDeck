#!/usr/bin/env python3
"""Log today's Market Pulse reading.

One reading per day, computed from the same benchmark snapshots the ticker
strip shows (ticker.json + crypto.json) - no external feed, no licensed data.
CNN's Fear & Greed endpoint blocks datacenter reads and Stooq's keyless CSV is
dead, which is why this is self-sourced. Weighted daily moves across
SPY/QQQ/DIA/IWM/USO + BTC/ETH/SOL mapped to 0-100; components with no price
yet are dropped and the weights renormalized. Fewer than three priced
components leaves the history untouched (fail-closed: yesterday's reading
stays on the page). Within a day the entry updates as snapshots refresh; a
new day appends. History grows from launch - no keyless verifiable source
offers backfill for our own computed score.
"""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "site" / "assets" / "sentiment-history.json"
WEIGHTS = {"SPY": 0.25, "QQQ": 0.20, "DIA": 0.15, "IWM": 0.10, "USO": 0.05,
           "BTC": 0.10, "ETH": 0.10, "SOL": 0.05}
MIN_COMPONENTS = 3

ZONES = [(20, "Extreme Fear"), (40, "Fear"), (60, "Neutral"), (80, "Greed"), (101, "Extreme Greed")]


def zone(score):
    for cap, name in ZONES:
        if score < cap:
            return name


def main():
    ticker = json.loads((ROOT / "site/assets/ticker.json").read_text())
    crypto = json.loads((ROOT / "site/assets/crypto.json").read_text())
    by_sym = {i["symbol"]: i for i in ticker.get("items", [])}
    by_sym.update({i["symbol"]: i for i in crypto.get("items", [])})
    num = den = 0.0
    used = 0
    for sym, w in WEIGHTS.items():
        cp = by_sym.get(sym, {}).get("changePercent")
        if isinstance(cp, (int, float)):
            num += w * cp
            den += w
            used += 1
    if used < MIN_COMPONENTS or not den:
        print(f"sentiment: only {used} priced components, leaving history untouched")
        return
    score = max(0, min(100, round(50 + (num / den) * 20)))
    today = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    history = json.loads(HISTORY.read_text()) if HISTORY.exists() else []
    entry = {"date": today, "score": score, "label": zone(score)}
    if history and history[-1]["date"] == today:
        history[-1] = entry
        action = "updated"
    else:
        history.append(entry)
        action = "appended"
    history = history[-365:]  # a year of readings is plenty for the scrubber
    HISTORY.write_text(json.dumps(history, indent=2) + "\n")
    print(f"sentiment: {action} {today} score={score} ({zone(score)}), {len(history)} days logged")


if __name__ == "__main__":
    main()
