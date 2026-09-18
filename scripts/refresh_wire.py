#!/usr/bin/env python3
"""Refresh The Wire (site/assets/wire.json, wire-archive.json, and the
WIRE_TOP / WIRE_LIST blocks in site/index.html) from public RSS feeds.

Deterministic: no AI, no invented prose. Headlines are the publishers' own
titles; every item keeps its source name and outbound link. Only the
publishers' headlines and links are aggregated (the same Fark/Drudge-style
link aggregation the site already does); no article text is copied.

Runs on GitHub Actions hourly. Safe to run any time: if every feed fails,
exits non-zero and writes nothing, so the site keeps the last good snapshot
(whose own as-of label shows its age).
"""
import json
import re
import sys
import html
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import feedparser

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
ASSETS = SITE / "assets"
INDEX = SITE / "index.html"

MAX_ITEMS = 17          # list length on the homepage (matches current layout)
MAX_AGE_HOURS = 36      # older items fall off the list into the archive
ARCHIVE_CAP = 200

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# (url, source label, feed bias, relevance filter?)
# feed bias: default category when keyword rules don't match.
# relevance filter True = general feed, keep only finance/geopolitics items.
FEEDS = [
    ("https://www.cnbc.com/id/100003114/device/rss/rss.html", "CNBC", "Markets", False),
    ("https://www.cnbc.com/id/100727362/device/rss/rss.html", "CNBC", "Geopolitics", False),
    ("https://feeds.marketwatch.com/marketwatch/topstories/", "MarketWatch", "Markets", False),
    ("https://feeds.marketwatch.com/marketwatch/marketpulse/", "MarketWatch", "Markets", False),
    ("https://finance.yahoo.com/news/rssindex", "Yahoo Finance", "Markets", False),
    ("https://www.benzinga.com/feed", "Benzinga", "Markets", False),
    ("https://www.investing.com/rss/news.rss", "Investing.com", "Markets", False),
    ("https://feeds.nbcnews.com/nbcnews/public/business", "NBC News", "Markets", False),
    ("https://www.france24.com/en/rss", "France 24", "Geopolitics", True),
    ("https://www.federalreserve.gov/feeds/press_all.xml", "Federal Reserve", "Macro", False),
]

MACRO = re.compile(r"\b(fed|fomc|federal reserve|powell|interest rate|rate cut|rate hike|"
                   r"inflation|cpi|ppi|treasur|yield|bond|central bank|jobs report|payrolls|"
                   r"unemployment|gdp|recession|ecb|boj|bank of england)\b", re.I)
GEO = re.compile(r"\b(trump|white house|congress|senate|tariff|sanction|war|ceasefire|nato|"
                 r"russia|ukraine|china|taiwan|israel|iran|gaza|middle east|opec|venezuela|"
                 r"election|geopolitic|missile|military)\b", re.I)
MOVE = re.compile(r"\b(soar|surge|jump|plunge|tumble|sink|rall|slide|slump|drop|gain|"
                  r"beat|miss|earn|upgrade|downgrade|ipo|deal|acqui|merger|buyback|"
                  r"stock rises|stock falls|shares)\b", re.I)
BROAD = re.compile(r"\b(s&p|nasdaq|dow jones|wall street|stock market|stocks|futures)\b", re.I)
# Syndicated promo and bot-written filler we never want on the wire.
BLOCK = re.compile(r"(motley fool|fool\.com|options flow shows|/news/company-news/|^\d+ (incredible|top|smart) |reasons? to buy)", re.I)

MONEY = re.compile(r"\b(stock|share|market|invest|trade|trading|earn|profit|revenue|ipo|"
                   r"fed|rate|inflation|oil|gold|bitcoin|crypto|bank|economy|gdp|"
                   r"tariff|sanction|china|russia|iran|israel|opec|treasur|bond|"
                   r"wall street|nasdaq|s&p|dow)\b", re.I)


def classify(title, bias):
    if MACRO.search(title):
        return "Macro"
    if GEO.search(title):
        return "Geopolitics"
    if MOVE.search(title) and not BROAD.search(title):
        return "Movers"
    return bias


def norm(title):
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def fetch(url):
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=20) as r:
        return r.read()


def main():
    seen = set()
    items = []
    ok_feeds = 0
    for url, source, bias, filtered in FEEDS:
        try:
            data = fetch(url)
            feed = feedparser.parse(data)
        except Exception as e:
            print(f"feed failed: {source} ({e})", file=sys.stderr)
            continue
        if not feed.entries:
            print(f"feed empty: {source}", file=sys.stderr)
            continue
        ok_feeds += 1
        for e in feed.entries[:15]:
            title = html.unescape(getattr(e, "title", "")).strip()
            link = getattr(e, "link", "").strip()
            if not title or not link:
                continue
            if filtered and not MONEY.search(title):
                continue
            if BLOCK.search(title) or BLOCK.search(link):
                continue
            key = norm(title)
            if key in seen:
                continue
            seen.add(key)
            ts = None
            for attr in ("published_parsed", "updated_parsed"):
                t = getattr(e, attr, None)
                if t:
                    ts = datetime(*t[:6], tzinfo=timezone.utc)
                    break
            if ts is None:
                ts = datetime.now(timezone.utc)
            items.append({
                "headline": title,
                "url": link,
                "source": source,
                "category": classify(title, bias),
                "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "_ts": ts.timestamp(),
            })
    if ok_feeds == 0:
        print("all feeds failed; leaving last good wire in place", file=sys.stderr)
        sys.exit(1)

    items.sort(key=lambda x: x["_ts"], reverse=True)
    now = datetime.now(timezone.utc)
    cutoff = now.timestamp() - MAX_AGE_HOURS * 3600

    fresh = [it for it in items if it["_ts"] >= cutoff]
    keep, aged = fresh[:MAX_ITEMS + 1], fresh[MAX_ITEMS + 1:]

    # Top story: prefer a company mover, then a markets/macro headline with
    # broad market relevance; never lead with a non-financial politics item
    # unless it is the only thing on the wire.
    def top_score(it):
        if it["category"] == "Movers":
            return 0
        if it["category"] in ("Markets", "Macro") and (BROAD.search(it["headline"]) or MACRO.search(it["headline"]) or MOVE.search(it["headline"])):
            return 1
        if MONEY.search(it["headline"]):
            return 2
        return 3
    top = min(keep, key=top_score) if keep else None
    rest = [it for it in keep if it is not top]
    rest = rest[:MAX_ITEMS]
    overflow = keep[len(rest) + (1 if top else 0):]

    # Archive: aged-out and overflow items, prepended, deduped by URL, capped.
    try:
        archive = json.loads((ASSETS / "wire-archive.json").read_text())
    except Exception:
        archive = {"items": []}
    have = {a.get("url") for a in archive.get("items", [])}
    new_arch = []
    for it in aged + overflow:
        if it["url"] not in have:
            have.add(it["url"])
            new_arch.append({k: it[k] for k in ("headline", "url", "source", "category", "timestamp")})
    archive["items"] = (new_arch + archive.get("items", []))[:ARCHIVE_CAP]

    et = now.astimezone(ZoneInfo("America/New_York"))
    label = et.strftime("%-I:%M %p ET").replace("AM", "AM").replace("PM", "PM")
    wire = {"asOf": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "asOfLabel": label}
    if top:
        wire["topStory"] = {
            "headline": top["headline"],
            "url": top["url"],
            "source": top["source"],
            "category": top["category"],
            "image": f"/assets/images/wire-{top['category'].lower()}.jpg",
        }
    wire["items"] = [{k: it[k] for k in ("headline", "url", "source", "category", "timestamp")}
                     for it in rest]

    # Rewrite the marked blocks in index.html (exact structure, so this stays
    # a clean find/replace against the same markers the old routine used).
    doc = INDEX.read_text()
    if top:
        top_html = (
            '<!-- WIRE_TOP_START — updated hourly by the Wire Refresh routine; keep this exact structure so the automated edit stays a clean find/replace -->\n'
            f'    <a class="wire-top" href="{html.escape(top["url"], quote=True)}" target="_blank" rel="noopener">\n'
            f'      <img class="wire-top-image" src="/assets/images/wire-{top["category"].lower()}.jpg" alt="">\n'
            f'      <span class="wire-top-label">Top Story</span>\n'
            f'      <span class="wire-top-headline">{html.escape(top["headline"])}</span>\n'
            f'      <span class="wire-top-source">{html.escape(top["source"])}</span>\n'
            f'    </a>\n'
            '    <!-- WIRE_TOP_END -->')
        doc = re.sub(r"<!-- WIRE_TOP_START.*?WIRE_TOP_END -->", lambda m: top_html, doc, flags=re.S)
    lis = "\n".join(
        f'      <li><span class="wire-tag">{it["category"]}</span> '
        f'<a href="{html.escape(it["url"], quote=True)}" target="_blank" rel="noopener">'
        f'{html.escape(it["headline"])}</a> <span class="wire-source">{html.escape(it["source"])}</span></li>'
        for it in rest)
    list_html = (
        '<!-- WIRE_LIST_START — updated hourly by the Wire Refresh routine; keep this exact structure so the automated edit stays a clean find/replace -->\n'
        '    <ul class="wire-list">\n'
        f'{lis}\n'
        '    </ul>\n'
        '    <!-- WIRE_LIST_END -->')
    doc = re.sub(r"<!-- WIRE_LIST_START.*?WIRE_LIST_END -->", lambda m: list_html, doc, flags=re.S)

    (ASSETS / "wire.json").write_text(json.dumps(wire, indent=2, ensure_ascii=False) + "\n")
    (ASSETS / "wire-archive.json").write_text(json.dumps(archive, indent=2, ensure_ascii=False) + "\n")
    INDEX.write_text(doc)
    print(f"OK: {ok_feeds}/{len(FEEDS)} feeds, {len(rest)} items, top={top['category'] if top else '-'}")
    print(f"COMMIT_MSG=Refresh The Wire: {label}")


if __name__ == "__main__":
    main()
