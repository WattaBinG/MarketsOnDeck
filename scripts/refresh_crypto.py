#!/usr/bin/env python3
"""Refresh site/assets/crypto.json from Coinbase Exchange's public market-data
API. No key, no AI. price = latest trade, change/changePercent = versus the
rolling 24-hour open that Coinbase's /stats endpoint reports (same basis the
file already uses). Source attribution travels in the file ("source") and is
documented in AUTOMATION.md.

Runs on GitHub Actions every 15 minutes. On API failure it exits non-zero and
writes nothing, so the site keeps the last good snapshot (whose as-of shows
its age).
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "assets" / "crypto.json"
SYMBOLS = ["BTC", "ETH", "SOL"]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def stats(sym):
    url = f"https://api.exchange.coinbase.com/products/{sym}-USD/stats"
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def main():
    items = []
    for sym in SYMBOLS:
        s = stats(sym)
        last, open_ = float(s["last"]), float(s["open"])
        change = last - open_
        items.append({
            "symbol": sym,
            "price": round(last, 2),
            "change": round(change, 2),
            "changePercent": round(100 * change / open_, 2) if open_ else 0.0,
        })
    out = {
        "asOf": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "Coinbase Exchange (public market data)",
        "items": items,
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print("OK: " + ", ".join(f"{i['symbol']} {i['price']}" for i in items))
    print("COMMIT_MSG=Refresh crypto ticker")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"crypto refresh failed: {e}", file=sys.stderr)
        sys.exit(1)
