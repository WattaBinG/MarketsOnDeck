#!/usr/bin/env python3
"""Rank tracked AI tools by Apple's public US Top Free Apps chart.

Reads data/ai-tools.json (Keith's config: name, optional siteUrl, App Store
id, referralUrl slot), fetches Apple's keyless marketing-tools chart feed,
and publishes the charted tools in chart order to site/assets/ai-tools.json.
That is the whole ranking story: if an app falls off the chart it falls off
the strip, and a new entrant appears once it charts and has a config line -
the churn is the chart's churn, no editorializing.

Link precedence per tool: referralUrl (Keith's, when he drops one in) >
siteUrl > the app's App Store page from the chart feed itself. No URL is
ever invented.

Fail-closed: any fetch/parse error, or a chart with zero tracked tools,
leaves the last published strip in place.
"""
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "data" / "ai-tools.json"
OUT = ROOT / "site" / "assets" / "ai-tools.json"
CHART_URL = "https://rss.applemarketingtools.com/api/v2/us/apps/top-free/100/apps.json"
UA = "MarketsOnDeck AI strip bot (+https://marketsondeck.wattabing.workers.dev)"
MAX_ITEMS = 8


def main():
    tools = json.loads(CONFIG.read_text(encoding="utf-8"))["tools"]
    by_id = {int(t["appStoreId"]): t for t in tools if t.get("appStoreId")}
    req = Request(CHART_URL, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=25) as r:
            feed = json.loads(r.read().decode("utf-8", "replace"))
        entries = feed["feed"]["results"]
    except Exception as e:
        print(f"FAILED(closed): chart fetch: {e}; keeping last published strip")
        return
    items = []
    for pos, entry in enumerate(entries, 1):
        tool = by_id.get(int(entry.get("id", 0)))
        if not tool:
            continue
        url = tool.get("referralUrl") or tool.get("siteUrl") or entry.get("url")
        if not url:
            continue
        items.append({"rank": pos, "name": tool["name"], "url": url})
        if len(items) >= MAX_ITEMS:
            break
    if not items:
        print("FAILED(closed): no tracked tools on the chart; keeping last published strip")
        return
    now = datetime.now(timezone.utc)
    out = {
        "asOf": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "asOfLabel": now.astimezone(ZoneInfo("America/New_York")).strftime("%-I:%M %p ET"),
        "source": "Apple App Store - US Top Free Apps chart",
        "sourceUrl": "https://www.apple.com/app-store/charts/",
        "items": items,
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"OK: {len(items)} charted tools, top: {items[0]['name']} (#{items[0]['rank']})")


if __name__ == "__main__":
    main()
