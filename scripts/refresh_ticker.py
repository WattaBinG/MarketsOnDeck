#!/usr/bin/env python3
"""Refresh ticker-strip prices from free keyless quotes (GitHub Actions leg).

Replaces the retired local Claude routines "Ticker Refresh - Intraday" and
"Ticker Refresh - Market Close": until now they were the ONLY price source
for site/assets/ticker.json (build_ticker.py only reshapes and carries the
last local snapshot forward).

Rules (AUTOMATION.md): stale beats faked. A failed fetch keeps the previous
price and counts the symbol as stale; a price is only ever written from a
real quote. Symbols are never invented - the strip set stays as shaped by
build_ticker.py (pinned staples + Keith's positions + existing movers),
with a quote attempt for any pinned/held symbol missing from the strip.
"""
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
TICKER = ROOT / "site" / "assets" / "ticker.json"
POSITIONS = ROOT / "site" / "assets" / "positions.json"

PINNED = ["SPY", "QQQ", "DIA", "IWM", "USO"]
CRYPTO_PINNED = ["BTC", "ETH", "SOL"]  # priced by refresh_crypto.py, never here
EXCLUDED = ["USDG", "USDC", "DOGE", "METV26"]

# Plain client UA: Yahoo 429s browser-impersonating UAs from datacenter
# IPs (GitHub runners included); an honest non-browser UA passes.
YAHOO_UA = "Mozilla/5.0"


def fetch_yahoo_quote(symbol):
    """Best-effort keyless quote for one symbol via Yahoo Finance chart API.

    Returns (price, change, changePercent) or None on ANY failure.
    Never invents: a failed fetch means the caller keeps the old price.
    """
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": YAHOO_UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.load(resp)
        meta = data["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice")
        change_pct = meta.get("regularMarketChangePercent")
        if not isinstance(price, (int, float)) or not isinstance(change_pct, (int, float)):
            return None
        change = price * change_pct / 100
        return (round(price, 2), round(change, 2), round(change_pct, 2))
    except Exception:
        return None


def et_now():
    return datetime.now(timezone.utc).astimezone(ZoneInfo("America/New_York"))


def main():
    ticker = json.loads(TICKER.read_text(encoding="utf-8"))
    positions = json.loads(POSITIONS.read_text(encoding="utf-8"))
    held_syms = []
    for pos in positions.get("positions", []):
        sym = str(pos.get("symbol") or "").strip().upper()
        if sym and sym not in held_syms and sym not in EXCLUDED and sym not in CRYPTO_PINNED:
            held_syms.append(sym)

    by_symbol = {str(i.get("symbol", "")).upper(): i for i in ticker.get("items", [])}
    want = []
    for sym in PINNED + held_syms + list(by_symbol):
        if sym and sym not in want and sym not in CRYPTO_PINNED and sym not in EXCLUDED:
            want.append(sym)

    now_utc = datetime.now(timezone.utc)
    et = et_now()
    label = "Market Close" if et.hour >= 16 else f"Intraday {et.strftime('%-I:%M %p')} ET"

    updated, stale, no_price = [], [], []
    items = []
    for sym in want:
        prev = by_symbol.get(sym, {})
        quote = fetch_yahoo_quote(sym)
        if quote:
            price, change, change_pct = quote
            updated.append(sym)
        elif isinstance(prev.get("price"), (int, float)):
            price, change, change_pct = prev["price"], prev.get("change"), prev.get("changePercent")
            stale.append(sym)  # keep the old print - stale beats faked
        else:
            no_price.append(sym)  # never emit a blank ticker
            continue
        item = {"symbol": sym, "price": price, "change": change, "changePercent": change_pct}
        if prev.get("held") or sym in held_syms:
            item["held"] = True
        items.append(item)

    if not updated:
        print("SKIP: no quotes fetched; leaving ticker.json untouched")
        return

    ticker["pinned"] = PINNED
    ticker["items"] = items
    ticker["asOf"] = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    ticker["asOfLabel"] = label
    TICKER.write_text(json.dumps(ticker, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"OK: {len(updated)} priced, {len(stale)} stale-kept ({stale or 'none'}), "
          f"{len(no_price)} dropped no-price ({no_price or 'none'}); label={label}")
    print(f"COMMIT_MSG=Refresh ticker strip: {label}")


if __name__ == "__main__":
    main()
