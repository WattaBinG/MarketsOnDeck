#!/usr/bin/env python3
"""Build and update Market Pulse history from keyless benchmark prices.

Daily uses the current strip snapshots. Longer views are derived from adjusted
closes returned by Yahoo Finance's keyless chart endpoint for the same eight
benchmarks. Only derived scores are published, never raw prices. The first run
backfills one year; later runs refresh the file once per market day. Any source
failure leaves the last dated history intact.
"""
import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "site" / "assets" / "sentiment-history.json"
WEIGHTS = {"SPY": .25, "QQQ": .20, "DIA": .15, "IWM": .10, "USO": .05,
           "BTC": .10, "ETH": .10, "SOL": .05}
YAHOO = {**{s: s for s in ("SPY", "QQQ", "DIA", "IWM", "USO")},
         "BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD"}
LOOKBACKS = {"1D": 1, "1W": 5, "1M": 21, "3M": 63, "6M": 126, "1Y": 252}
MIN_COMPONENTS = 3
ZONES = [(20, "Extreme Fear"), (40, "Fear"), (60, "Neutral"), (80, "Greed"), (101, "Extreme Greed")]


def zone(score):
    return next(name for cap, name in ZONES if score < cap)


def score_return(weighted_pct, sessions):
    # Normalize trend strength by sqrt(time), so long horizons do not simply
    # pin the dial at an extreme. Daily retains the original 20 points/% map.
    return max(0, min(100, round(50 + weighted_pct * 20 / math.sqrt(sessions))))


def fetch_prices(symbol):
    url = "https://query1.finance.yahoo.com/v8/finance/chart/{}?{}".format(
        urllib.parse.quote(YAHOO[symbol]), urllib.parse.urlencode({"range": "2y", "interval": "1d", "events": "history"}))
    req = urllib.request.Request(url, headers={"User-Agent": "MarketsOnDeck/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as response:
        payload = json.load(response)
    result = payload.get("chart", {}).get("result") or []
    if not result:
        raise ValueError(f"no chart result for {symbol}")
    row = result[0]
    closes = ((row.get("indicators", {}).get("adjclose") or [{}])[0].get("adjclose") or
              (row.get("indicators", {}).get("quote") or [{}])[0].get("close") or [])
    out = {}
    for stamp, close in zip(row.get("timestamp") or [], closes):
        if isinstance(close, (int, float)) and close > 0:
            day = datetime.fromtimestamp(stamp, ZoneInfo("America/New_York")).date().isoformat()
            out[day] = float(close)
    if len(out) < 260:
        raise ValueError(f"too little history for {symbol}: {len(out)} sessions")
    return out


def at_or_before(series, date):
    dates = [d for d in series if d <= date]
    return max(dates) if dates else None


def horizon_score(series_by_symbol, date, sessions):
    weighted = den = 0.0
    used = 0
    for sym, weight in WEIGHTS.items():
        series = series_by_symbol.get(sym, {})
        end = at_or_before(series, date)
        if not end:
            continue
        ordered = [d for d in series if d <= end]
        ordered.sort()
        if len(ordered) <= sessions:
            continue
        start = ordered[-(sessions + 1)]
        move = (series[end] / series[start] - 1) * 100
        weighted += weight * move
        den += weight
        used += 1
    if used < MIN_COMPONENTS or not den:
        return None
    value = score_return(weighted / den, sessions)
    return {"score": value, "label": zone(value)}


def current_daily():
    ticker = json.loads((ROOT / "site/assets/ticker.json").read_text())
    crypto = json.loads((ROOT / "site/assets/crypto.json").read_text())
    by_sym = {i["symbol"]: i for i in ticker.get("items", [])}
    by_sym.update({i["symbol"]: i for i in crypto.get("items", [])})
    num = den = 0.0
    used = 0
    for sym, weight in WEIGHTS.items():
        move = by_sym.get(sym, {}).get("changePercent")
        if isinstance(move, (int, float)):
            num += weight * move
            den += weight
            used += 1
    if used < MIN_COMPONENTS or not den:
        return None
    value = score_return(num / den, 1)
    return {"score": value, "label": zone(value)}


def main():
    today = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    old = json.loads(HISTORY.read_text()) if HISTORY.exists() else []
    # Do not hit the history source repeatedly during the hourly wire run.
    if old and old[-1].get("date") == today and old[-1].get("scores", {}).get("1Y"):
        daily = current_daily()
        if daily:
            old[-1]["scores"]["1D"] = daily
            old[-1].update(daily)  # backwards-compatible fields for older clients
            HISTORY.write_text(json.dumps(old[-365:], indent=2) + "\n")
            print(f"sentiment: updated {today} daily score={daily['score']}, history source not re-fetched")
        return

    try:
        series = {sym: fetch_prices(sym) for sym in WEIGHTS}
    except Exception as exc:
        print(f"sentiment: history fetch failed ({exc}), leaving history untouched")
        return

    common_dates = sorted({d for values in series.values() for d in values})
    cutoff = (datetime.now(ZoneInfo("America/New_York")).date() - timedelta(days=364)).isoformat()
    history = []
    for date in (d for d in common_dates if cutoff <= d <= today):
        scores = {}
        for key, sessions in LOOKBACKS.items():
            value = horizon_score(series, date, sessions)
            if value:
                scores[key] = value
        if "1D" in scores:
            history.append({"date": date, **scores["1D"], "scores": scores})

    daily = current_daily()
    if daily:
        if history and history[-1]["date"] == today:
            history[-1]["scores"]["1D"] = daily
            history[-1].update(daily)
        else:
            previous = history[-1]["scores"].copy() if history else {}
            previous["1D"] = daily
            history.append({"date": today, **daily, "scores": previous})
    if not history:
        print("sentiment: no complete derived readings, leaving history untouched")
        return
    HISTORY.write_text(json.dumps(history[-365:], indent=2) + "\n")
    print(f"sentiment: backfilled {len(history[-365:])} dated readings through {history[-1]['date']}")


if __name__ == "__main__":
    main()
