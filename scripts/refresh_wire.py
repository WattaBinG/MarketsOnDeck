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

LEAD STORY (sticky lead): every run scores each story cluster with a fixed,
explainable formula (see AUTOMATION.md): source weight x recency decay,
boosted for cross-source corroboration and market relevance. The incumbent
lead keeps its slot until a challenger story outscores it by more than
~1.4x (STICKY_FACTOR) or its newest item ages past MAX_LEAD_AGE_HOURS — so
the top of the page only changes when the day's story actually changes.
The full score table and the lead decision are printed to the workflow log.
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
MIN_FEED_SUCCESS_RATIO = 0.60  # preserve the last good snapshot during broad provider outages
ARCHIVE_CAP = 200

# Sticky-lead tuning (see AUTOMATION.md for the rationale):
STICKY_FACTOR = 0.70      # incumbent keeps the lead while its cluster scores >= 70% of the challenger's
MAX_LEAD_AGE_HOURS = 30   # a lead whose newest item is older than this cannot hold the slot
CLUSTER_JACCARD = 0.34    # token overlap needed to call two headlines the same story
UNKNOWN_AGE_HOURS = 12    # feeds that omit a publish time score as if this old, never as brand-new

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

# Source weights for lead scoring: official primary sources and the two
# highest-volume market wires count a little more. Everything else is 1.0.
SOURCE_W = {"Federal Reserve": 2.0, "CNBC": 1.5, "MarketWatch": 1.5}

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
BLOCK = re.compile(r"(motley fool|fool\.com|options flow|/news/company-news/|^\d+ (incredible|top|smart) |reasons? to buy)", re.I)

MONEY = re.compile(r"\b(stock|share|market|invest|trade|trading|earn|profit|revenue|ipo|"
                   r"fed|rate|inflation|oil|gold|bitcoin|crypto|bank|economy|gdp|"
                   r"tariff|sanction|china|russia|iran|israel|opec|treasur|bond|"
                   r"wall street|nasdaq|s&p|dow)\b", re.I)

STOP = set(("the a an and or of to in on for with at by from as is are was were be been it its "
            "this that these those over after amid into your you how what why will would could "
            "should says say said new vs not no more most than about out up down his her their "
            "our us we i here are is to of in for on with at by").split())


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


def tokens(title):
    """Significant tokens used for same-story matching."""
    return {t for t in norm(title).split() if t not in STOP and len(t) > 2}


def jaccard(a, b):
    u = a | b
    return len(a & b) / len(u) if u else 0.0


def fetch(url):
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=20) as r:
        return r.read()


def recency_factor(ts_epoch, now_epoch):
    age_h = max(0.0, (now_epoch - ts_epoch) / 3600.0)
    return max(0.25, 1.0 - age_h / MAX_AGE_HOURS)


def cluster_score(cluster, now_epoch):
    """Deterministic, explainable: sum(source weight x recency), boosted
    for cross-source corroboration and market relevance."""
    # Items without a real publish time score at UNKNOWN_AGE_HOURS old so
    # evergreen filler cannot win the lead on a fabricated "just now".
    base = sum(SOURCE_W.get(it["source"], 1.0) *
               recency_factor(it["_ts"] if it["_known_ts"] else now_epoch - UNKNOWN_AGE_HOURS * 3600,
                              now_epoch)
               for it in cluster["items"])
    n_sources = len({it["source"] for it in cluster["items"]})
    heads = " ".join(it["headline"] for it in cluster["items"])
    corroboration = 1.0 + 0.35 * (n_sources - 1)
    relevance = 1.25 if (MACRO.search(heads) or BROAD.search(heads) or MOVE.search(heads)) else 1.0
    return base * corroboration * relevance, base, n_sources, relevance


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
            known_ts = ts is not None
            if ts is None:
                ts = datetime.now(timezone.utc)
            items.append({
                "headline": title,
                "url": link,
                "source": source,
                "category": classify(title, bias),
                "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "_ts": ts.timestamp(),
                "_known_ts": known_ts,
            })
    minimum_ok = max(1, int(len(FEEDS) * MIN_FEED_SUCCESS_RATIO + 0.999))
    if ok_feeds < minimum_ok:
        print(f"only {ok_feeds}/{len(FEEDS)} feeds succeeded (need {minimum_ok}); leaving last good wire in place", file=sys.stderr)
        sys.exit(1)

    items.sort(key=lambda x: x["_ts"], reverse=True)
    now = datetime.now(timezone.utc)
    now_epoch = now.timestamp()
    cutoff = now_epoch - MAX_AGE_HOURS * 3600

    fresh = [it for it in items if it["_ts"] >= cutoff]
    fetched_aged = [it for it in items if it["_ts"] < cutoff]
    keep, aged = fresh[:MAX_ITEMS + 4], fetched_aged + fresh[MAX_ITEMS + 4:]

    # Cluster same-story headlines (deterministic greedy pass, recency order).
    clusters = []
    for it in keep:
        tok = tokens(it["headline"])
        best, best_j = None, 0.0
        for c in clusters:
            j = jaccard(c["tokens"], tok)
            if j > best_j:
                best, best_j = c, j
        if best is not None and best_j >= CLUSTER_JACCARD:
            best["items"].append(it)
            best["tokens"] |= tok
        else:
            clusters.append({"tokens": set(tok), "items": [it]})

    scored = []
    for c in clusters:
        score, base, n_src, rel = cluster_score(c, now_epoch)
        c["score"] = score
        scored.append((score, base, n_src, rel, c))
    scored.sort(key=lambda s: (-s[0], -max(it["_ts"] for it in s[4]["items"])))

    print("story scores (score | base x corroboration x relevance | sources | headline):")
    for score, base, n_src, rel, c in scored[:8]:
        rep = max(c["items"], key=lambda i: i["_ts"])
        print(f"  {score:5.2f} | {base:5.2f} x {1 + .35*(n_src-1):.2f} x {rel:.2f} | "
              f"{n_src} src | {rep['headline'][:80]}")

    # Incumbent lead from the current wire.json.
    incumbent = None
    try:
        prior = json.loads((ASSETS / "wire.json").read_text())
        incumbent = prior.get("topStory") or None
    except Exception:
        incumbent = None

    challenger = scored[0][4] if scored else None
    lead_cluster, held = challenger, False
    if incumbent and challenger:
        inc_cluster = None
        for c in clusters:
            if any(it["url"] == incumbent.get("url") for it in c["items"]):
                inc_cluster = c
                break
        if inc_cluster is None:  # URL gone from feeds; match by headline tokens
            inc_tok = tokens(incumbent.get("headline", ""))
            for c in clusters:
                if jaccard(c["tokens"], inc_tok) >= CLUSTER_JACCARD:
                    inc_cluster = c
                    break
        if inc_cluster is None:
            # Persist a young incumbent even after it falls below a feed's short
            # window. Score its saved item with the same deterministic decay so
            # it still must clear the documented 70% challenger threshold.
            try:
                inc_ts = datetime.fromisoformat(incumbent["timestamp"].replace("Z", "+00:00")).timestamp()
            except Exception:
                inc_ts = 0
            if inc_ts and now_epoch - inc_ts <= MAX_LEAD_AGE_HOURS * 3600:
                saved = dict(incumbent)
                saved["_ts"] = inc_ts
                saved["_known_ts"] = True
                inc_cluster = {"tokens": tokens(saved.get("headline", "")), "items": [saved]}
                inc_cluster["score"], _, _, _ = cluster_score(inc_cluster, now_epoch)
        if inc_cluster is challenger:
            # The incumbent's story is still the top-scoring story: lead held.
            held = True
        elif inc_cluster is not None:
            newest = max(it["_ts"] for it in inc_cluster["items"])
            young = (now_epoch - newest) <= MAX_LEAD_AGE_HOURS * 3600
            strong = inc_cluster["score"] >= challenger["score"] * STICKY_FACTOR
            print(f"incumbent: score {inc_cluster['score']:.2f} vs challenger {challenger['score']:.2f} "
                  f"(need >= {challenger['score'] * STICKY_FACTOR:.2f}), young={young}")
            if young and strong:
                lead_cluster, held = inc_cluster, True

    # Lead item: keep the exact incumbent item when held (headline continuity);
    # otherwise the freshest item from the highest-weighted source in the cluster.
    top = None
    lead_since = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    if lead_cluster:
        if held and incumbent and any(it["url"] == incumbent.get("url") for it in lead_cluster["items"]):
            top = next(it for it in lead_cluster["items"] if it["url"] == incumbent.get("url"))
            lead_since = incumbent.get("leadSince") or incumbent.get("timestamp") or lead_since
        else:
            top = max(lead_cluster["items"],
                      key=lambda i: (SOURCE_W.get(i["source"], 1.0), i["_ts"]))

    # List: freshest first, excluding the lead item and duplicate versions of
    # the lead story from other sources.
    lead_dupes = {id(it) for it in lead_cluster["items"]} if lead_cluster else set()
    rest = [it for it in keep if id(it) not in lead_dupes][:MAX_ITEMS]
    listed = {id(it) for it in rest} | lead_dupes
    overflow = [it for it in keep if id(it) not in listed]

    # Archive: aged-out and overflow items, prepended, deduped by URL, capped.
    try:
        archive = json.loads((ASSETS / "wire-archive.json").read_text())
    except Exception:
        archive = {"items": []}
    have = {a.get("url") for a in archive.get("items", [])}
    new_arch = []
    current_urls = {it["url"] for it in items}
    prior_visible = []
    if incumbent:
        prior_visible.append(incumbent)
    prior_visible.extend(prior.get("items", []) if isinstance(prior, dict) else [])
    for old in prior_visible:
        if old.get("url") and old.get("url") not in current_urls and old.get("url") not in have:
            try:
                old_ts = datetime.fromisoformat(old.get("timestamp", "").replace("Z", "+00:00")).timestamp()
            except Exception:
                old_ts = now_epoch
            if old_ts < cutoff:
                have.add(old["url"])
                new_arch.append({k: old.get(k, "") for k in ("headline", "url", "source", "category", "timestamp")})
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
            "timestamp": top["timestamp"],
            "leadSince": lead_since,
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
    decision = "lead held" if held else ("new lead" if top else "no lead")
    print(f"OK: {ok_feeds}/{len(FEEDS)} feeds, {len(rest)} items, top={top['category'] if top else '-'} ({decision})")
    print(f"COMMIT_MSG=Refresh The Wire: {label} ({decision})")


if __name__ == "__main__":
    main()
