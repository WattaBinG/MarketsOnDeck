#!/usr/bin/env python3
"""Reshape the stock/ETF ticker strip from data the repo already owns.

Layers (AUTOMATION.md): pinned staples first, then Keith's portfolio
(derived here from site/assets/positions.json - symbols are his own data,
not licensed market data), then the rotating movers picked by his local
routine. Dedupes across layers and caps the strip at 15. Prices are never
invented: they carry over from the last local-refresh snapshot; symbols
that arrive without a price get one keyless Yahoo Finance quote attempt,
and anything still priceless is DROPPED (the site must never render a
blank "--" ticker). BTC/ETH/SOL stay out of this file on purpose - they
pin from crypto.json's own 15-minute refresh.

Runs inside the hourly wire workflow as the mechanical backstop; a sloppy
local pick cannot break the shape. The Yahoo fallback is best-effort only:
any fetch failure degrades to dropping the symbol, never to a guess.
"""
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TICKER = ROOT / "site" / "assets" / "ticker.json"
POSITIONS = ROOT / "site" / "assets" / "positions.json"

PINNED = ["SPY", "QQQ", "DIA", "IWM", "USO"]  # oil rides USO; BTC/ETH/SOL pin via crypto.json
CRYPTO_PINNED = ["BTC", "ETH", "SOL"]        # never duplicated into this strip
# Never on the tape, ever: stablecoins/dust (USDG, USDC, DOGE) and Micro Ether futures.
# USDG was excluded 2026-10-01; DOGE/USDC added 2026-10-02 (dust balances, blank quotes).
EXCLUDED = ["USDG", "USDC", "DOGE", "METV26"]
MAX_ITEMS = 15

YAHOO_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def fetch_yahoo_quote(symbol):
    """Best-effort keyless quote for one symbol via Yahoo Finance chart API.

    Returns (price, change, changePercent) or None on ANY failure.
    Never invents: a failed fetch means the caller drops the symbol.
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


def main():
    ticker = json.loads(TICKER.read_text(encoding="utf-8"))
    positions = json.loads(POSITIONS.read_text(encoding="utf-8"))
    held = []
    for pos in positions.get("positions", []):
        sym = str(pos.get("symbol") or "").strip().upper()
        if sym and sym not in held and sym not in EXCLUDED:
            held.append(sym)

    by_symbol = {str(i.get("symbol", "")).upper(): i for i in ticker.get("items", [])}

    ordered = []
    for sym in PINNED:                       # layer 1: staples
        ordered.append((sym, False))
    for sym in held:                         # layer 2: his book
        if sym not in PINNED and sym not in CRYPTO_PINNED:
            ordered.append((sym, True))
    for sym in by_symbol:                    # layer 3: local routine's movers
        if sym not in PINNED and sym not in CRYPTO_PINNED and sym not in held and sym not in EXCLUDED:
            ordered.append((sym, False))
    ordered = ordered[:MAX_ITEMS]            # movers trim last

    items = []
    dropped = []
    filled = []
    for sym, is_held in ordered:
        prev = by_symbol.get(sym, {})
        price = prev.get("price")
        change = prev.get("change")
        change_pct = prev.get("changePercent")
        if not isinstance(price, (int, float)):
            quote = fetch_yahoo_quote(sym)
            if quote:
                price, change, change_pct = quote
                filled.append(sym)
        if not isinstance(price, (int, float)):
            dropped.append(sym)              # never emit a blank ticker
            continue
        item = {
            "symbol": sym,
            "price": price,
            "change": change,
            "changePercent": change_pct,
        }
        if is_held:
            item["held"] = True
        items.append(item)

    ticker["pinned"] = PINNED
    ticker["items"] = items
    TICKER.write_text(json.dumps(ticker, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    movers = [s for s, h in ordered if not h and s not in PINNED]
    print(f"OK: {len(items)} items ({len(PINNED)} pinned, "
          f"{sum(1 for _, h in ordered if h)} held, {len(movers)} movers); "
          f"asOf {ticker.get('asOfLabel', '?')} preserved; "
          f"yahoo-filled: {filled or 'none'}; dropped (no price): {dropped or 'none'}")


if __name__ == "__main__":
    main()
