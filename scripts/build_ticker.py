#!/usr/bin/env python3
"""Reshape the stock/ETF ticker strip from data the repo already owns.

Layers (AUTOMATION.md): pinned staples first, then Keith's portfolio
(derived here from site/assets/positions.json - symbols are his own data,
not licensed market data), then the rotating movers picked by his local
routine. Dedupes across layers and caps the strip at 15. Prices are never
invented: they carry over from the last local-refresh snapshot, and symbols
without a price get null (the site renders "--" and the as-of label keeps
the snapshot honest). BTC/ETH/SOL stay out of this file on purpose - they
pin from crypto.json's own 15-minute refresh.

Runs inside the hourly wire workflow as the mechanical backstop; a sloppy
local pick cannot break the shape. Keyless, no network, deterministic.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TICKER = ROOT / "site" / "assets" / "ticker.json"
POSITIONS = ROOT / "site" / "assets" / "positions.json"

PINNED = ["SPY", "QQQ", "DIA", "IWM", "USO"]  # oil rides USO; BTC/ETH/SOL pin via crypto.json
CRYPTO_PINNED = ["BTC", "ETH", "SOL"]        # never duplicated into this strip
EXCLUDED = ["USDG"]                      # dollar-pegged stablecoin - price never moves, strip noise (Keith, 2026-09-22)
MAX_ITEMS = 15


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
    for sym, is_held in ordered:
        prev = by_symbol.get(sym, {})
        item = {
            "symbol": sym,
            "price": prev.get("price"),
            "change": prev.get("change"),
            "changePercent": prev.get("changePercent"),
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
          f"asOf {ticker.get('asOfLabel', '?')} preserved")


if __name__ == "__main__":
    main()
