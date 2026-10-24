#!/usr/bin/env python3
"""Build dated canonical pages for MarketsOnDeck Brief + Tape entries.

The hubs (site/brief/index.html, site/market-tape/index.html) remain the lanes'
authoring surface: entries land there exactly as they always have. This script
is the packaging step that runs AFTER an entry commit:

  1. Extract every `<div class="card daily-entry" id="brief-YYYY-MM-DD">` /
     `id="tape-YYYY-MM-DD">` block from the hubs.
  2. For each entry without an active hold, generate its own dated page at
     /brief/<date>/ or /market-tape/<date>/ with a per-day title, meta,
     OG tags and a NewsArticle JSON-LD block (author = the MarketsOnDeck
     publication byline entity; never a personal name).
  3. Point the hubs' existing "Jump To" list items at the dated URLs for
     days that have dated pages (entry bodies are never modified).
  4. Regenerate site/news-sitemap.xml (entries published in the last 48h)
     and the dated-pages section of site/sitemap.xml with honest lastmod.
  5. Record every page in data/dated-pages.json (the manifest: publish and
     modification timestamps, headline, lead image, entry hash).

HOLD GATE (story-level, binding): data/publish-holds.json lists story keys.
  - status "active": the generator refuses to create a dated page for the
    key, and FAILS (exit 3) if a dated page for it exists on disk.
  - status "no-dated-page": republish guard - the story may live on its hub
    but must never get a dated page; generation is skipped.
A held story therefore cannot reach the dated-page path through this script,
on any lane, on any retry - the same discipline as the publish gate that
guards the brief/tape jobs themselves.

Publish timestamps: for a brand-new page the generator uses --published
KEY=ISO8601 if supplied (backfill uses the hub commit timestamps), otherwise
the current America/New_York time. If an entry's HTML later changes on the
hub, the page is regenerated and dateModified is bumped.

BACKFILL DISCIPLINE (CEO ruling, 2026-10-24): only entries dated within
--window-days (default 5) of today get new dated pages. Older entries stay
hub-only; a human can name a specific older entry with --page-key. There is
no mass-backfill mode, deliberately.

Stdlib only. Usage:
  python3 scripts/build_dated_pages.py [--root .] [--check]
      [--published brief-2026-10-19=2026-10-19T08:34:50-04:00]
      [--modified  brief-2026-10-19=2026-10-19T09:02:00-04:00]
Exit codes: 0 ok (or --check clean), 2 usage/io error, 3 HOLD VIOLATION.
"""
import argparse
import datetime as dt
import hashlib
import html
import json
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
SITE = "https://marketsondeck.net"
PUBLISHER = {
    "@type": "Organization",
    "name": "MarketsOnDeck",
    "url": SITE + "/",
    "logo": {
        "@type": "ImageObject",
        "url": SITE + "/assets/brand/logo-a-400.png",
    },
}
AUTHOR = {
    "@type": "Organization",
    "name": "MarketsOnDeck",
    "url": SITE + "/about.html",
}
KINDS = {
    "brief": {
        "hub": "site/brief/index.html",
        "hub_url": "/brief/",
        "label": "Morning Brief",
        "section": "Morning Brief",
        "title_prefix": "Stock Market Today: ",
    },
    "tape": {
        "hub": "site/market-tape/index.html",
        "hub_url": "/market-tape/",
        "label": "After Market Tape",
        "section": "After Market Tape",
        "title_prefix": None,  # built from date + story headline
    },
}


def now_et():
    return dt.datetime.now(ET)


def iso_z(d):
    """ISO 8601 with the ET offset, seconds precision."""
    return d.isoformat(timespec="seconds")


def parse_iso(s):
    return dt.datetime.fromisoformat(s)


def text_of(fragment):
    """HTML fragment -> plain text (tags stripped, entities decoded)."""
    t = re.sub(r"<[^>]+>", " ", fragment)
    t = html.unescape(t)
    return re.sub(r"\s+", " ", t).strip()


def esc(s):
    return html.escape(s, quote=True)


def find_entries(hub_html):
    """Yield (story_key, block_html, start, end) for each daily-entry div.

    Balanced-div scan from each `<div class="card daily-entry"` opening tag.
    """
    out = []
    for m in re.finditer(r'<div class="card daily-entry[^"]*" id="((?:brief|tape)-\d{4}-\d{2}-\d{2})"[^>]*>', hub_html):
        key = m.group(1)
        depth = 0
        pos = m.start()
        end = None
        for tag in re.finditer(r"<div\b[^>]*>|</div>", hub_html[m.start():]):
            if tag.group(0).startswith("</"):
                depth -= 1
                if depth == 0:
                    end = m.start() + tag.end()
                    break
            else:
                depth += 1
        if end is None:
            raise ValueError(f"unbalanced <div> scanning entry {key}")
        out.append((key, hub_html[m.start():end], m.start(), end))
    return out


def parse_entry(key, block):
    kind = key.split("-")[0]
    date = key[len(kind) + 1:]
    d = dt.date.fromisoformat(date)
    headline_m = re.search(r"<h3[^>]*>(.*?)</h3>", block, re.S)
    headline_raw = text_of(headline_m.group(1)) if headline_m else ""
    headline = headline_raw
    if kind == "tape":
        # "After Market Tape — <story>" -> keep the story as the headline.
        headline = re.sub(r"^After Market Tape\s*[—–-]\s*", "", headline_raw)
    eyebrow_m = re.search(r'card-eyebrow[^>]*>.*?<span>(.*?)</span>', block, re.S)
    date_label = text_of(eyebrow_m.group(1)) if eyebrow_m else d.strftime("%B %-d, %Y")
    note_m = re.search(r'<p style="margin-top:0; font-size:13px; font-style:italic[^"]*">(.*?)</p>', block, re.S)
    note = note_m.group(1) if note_m else None
    img_m = re.search(r'<img[^>]+src="([^"]+)"', block)
    image = SITE + img_m.group(1) if img_m else None
    # Meta description: the first paragraph after the headline that leads
    # with a <strong> (the scoreboard / lead line) - numbers first.
    desc = ""
    if headline_m:
        for p in re.finditer(r"<p[^>]*>(.*?)</p>", block[headline_m.end():], re.S):
            frag = p.group(1)
            if "<strong>" in frag:
                desc = text_of(frag)
                break
    if not desc:
        desc = headline
    desc = re.sub(r"\s+([,.;:)])", r"\1", desc)
    desc = re.sub(r"([(])\s+", r"\1", desc)
    if len(desc) > 155:
        desc = desc[:155].rsplit(" ", 1)[0].rstrip(",;:")
    # Body for the dated page: the entry block minus its <h3> (promoted to
    # the page H1) and minus the latest-entry marker class.
    body = block
    if headline_m:
        body = body.replace(headline_m.group(0), "", 1)
    body = body.replace(" daily-entry-latest", "", 1)
    return {
        "key": key, "kind": kind, "date": date, "date_label": date_label,
        "headline": headline, "headline_raw": headline_raw, "note": note,
        "image": image, "description": desc, "body": body,
        "sha": hashlib.sha256(block.encode()).hexdigest()[:16],
    }


def page_url(e):
    base = "/brief/" if e["kind"] == "brief" else "/market-tape/"
    return base + e["date"] + "/"


def page_title(e):
    if e["kind"] == "brief":
        return f"Stock Market Today: {e['headline']} | MarketsOnDeck"
    return f"Market Recap — {e['date_label']}: {e['headline']} | MarketsOnDeck"


def build_page(e, hub_html, published, modified, nav_links):
    """Assemble the dated page, reusing the hub's own chrome verbatim."""
    head_end = hub_html.index("</head>") + len("</head>")
    hub_head = hub_html[:head_end]
    body_start = hub_html.index("<main>")
    chrome_top = hub_html[head_end:body_start]  # <body> ... ticker strip
    tail = hub_html[hub_html.index("</main>") + len("</main>"):]
    disc_m = re.search(r'<p class="footer-disclosure".*?</p>', hub_html, re.S)
    disclosure = disc_m.group(0) if disc_m else ""

    url = SITE + page_url(e)
    title = page_title(e)
    head = hub_head
    head = re.sub(r"<title>.*?</title>", f"<title>{esc(title)}</title>", head, count=1, flags=re.S)
    head = re.sub(r'<meta name="description" content="[^"]*">',
                  f'<meta name="description" content="{esc(e["description"])}">', head, count=1)
    head = re.sub(r'<link rel="canonical" href="[^"]*">',
                  f'<link rel="canonical" href="{url}">', head, count=1)
    head = re.sub(r'<meta property="og:title" content="[^"]*">',
                  f'<meta property="og:title" content="{esc(title)}">', head, count=1)
    head = re.sub(r'<meta property="og:description" content="[^"]*">',
                  f'<meta property="og:description" content="{esc(e["description"])}">', head, count=1)
    head = re.sub(r'<meta property="og:url" content="[^"]*">',
                  f'<meta property="og:url" content="{url}">', head, count=1)
    head = re.sub(r'<meta property="og:type" content="[^"]*">',
                  '<meta property="og:type" content="article">', head, count=1)
    head = re.sub(r'<meta name="twitter:title" content="[^"]*">',
                  f'<meta name="twitter:title" content="{esc(title)}">', head, count=1)
    head = re.sub(r'<meta name="twitter:description" content="[^"]*">',
                  f'<meta name="twitter:description" content="{esc(e["description"])}">', head, count=1)
    img = e["image"] or (SITE + "/assets/brand/badge-1200.jpg")
    head = re.sub(r'<meta property="og:image" content="[^"]*">',
                  f'<meta property="og:image" content="{img}">', head, count=1)
    head = re.sub(r'<meta name="twitter:image" content="[^"]*">',
                  f'<meta name="twitter:image" content="{img}">', head, count=1)
    head = head.replace('<meta name="viewport"',
                        '<meta name="robots" content="max-image-preview:large">\n<meta name="viewport"', 1)

    article = {
        "@type": "NewsArticle",
        "headline": e["headline"],
        "description": e["description"],
        "datePublished": published,
        "dateModified": modified,
        "author": AUTHOR,
        "publisher": PUBLISHER,
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "isPartOf": {"@type": "WebSite", "name": "MarketsOnDeck", "url": SITE + "/"},
    }
    if e["image"]:
        article["image"] = [e["image"]]
    crumbs = {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/index.html"},
            {"@type": "ListItem", "position": 2, "name": KINDS[e["kind"]]["label"],
             "item": SITE + KINDS[e["kind"]]["hub_url"] + "index.html"},
            {"@type": "ListItem", "position": 3, "name": e["date_label"], "item": url},
        ],
    }
    ld = {"@context": "https://schema.org", "@graph": [article, crumbs]}
    ld_json = json.dumps(ld, ensure_ascii=False, separators=(",", ":"))
    head = re.sub(r'<script type="application/ld\+json">.*?</script>',
                  f'<script type="application/ld+json">{ld_json}</script>', head, count=1, flags=re.S)

    note_html = f'\n      <p class="hero-sub">{e["note"]}</p>' if e["note"] else ""
    pub_label = parse_iso(published).strftime("%B %-d, %Y, %-I:%M %p ET")
    nav_html = ""
    if nav_links:
        items = " &middot; ".join(
            f'<a href="{u}">{esc(t)}</a>' for t, u in nav_links)
        nav_html = (f'\n    <nav class="dated-nav" aria-label="More daily pages" '
                    f'style="margin:28px 0 8px; font-size:15px;">{items}</nav>')
    main = f"""<main>
  <div class="container section-tight">
    <div class="article-header">
      <div class="eyebrow">{esc(e["date_label"])} &middot; {KINDS[e["kind"]]["label"]}</div>
      <h1>{esc(e["headline"])}</h1>{note_html}
      <p class="text-muted" style="font-size:13px; margin-top:10px;">First published {pub_label} &middot; <a href="{KINDS[e["kind"]]["hub_url"]}index.html">All {KINDS[e["kind"]]["label"]} entries &rarr;</a></p>
      <div class="share-bar" data-title="{esc(e["headline"])} — MarketsOnDeck">
        <span class="share-label">Share</span>
        <a class="share-btn share-x" href="#" target="_blank" rel="noopener" aria-label="Share on X">X</a>
        <a class="share-btn share-fb" href="#" target="_blank" rel="noopener" aria-label="Share on Facebook">Facebook</a>
        <a class="share-btn share-li" href="#" target="_blank" rel="noopener" aria-label="Share on LinkedIn">LinkedIn</a>
        <button class="share-btn share-copy" type="button">Copy Link</button>
      </div>
    </div>
  </div>
  <div class="container">
    <div class="brief-layout daily-feed">
      <div class="brief-main article-body prose daily-entries">
{e["body"]}
      </div>
    </div>{nav_html}
    {disclosure}
  </div>
</main>"""
    return head + "\n" + chrome_top + main + tail


def load_json(path, default):
    if Path(path).exists():
        return json.loads(Path(path).read_text())
    return default


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--check", action="store_true",
                    help="report what would change; write nothing")
    ap.add_argument("--published", action="append", default=[],
                    metavar="KEY=ISO", help="seed publish time for a new page")
    ap.add_argument("--modified", action="append", default=[],
                    metavar="KEY=ISO", help="seed modified time for a new page")
    ap.add_argument("--page-key", action="append", default=[], metavar="KEY",
                    help="force a dated page for this entry even outside the "
                         "recency window (deliberate backfill, one key at a time)")
    ap.add_argument("--window-days", type=int, default=5,
                    help="entries dated within this many days of today (ET) "
                         "get dated pages; older entries stay hub-only. "
                         "Default 5 = the backfill cap; do not widen casually.")
    args = ap.parse_args(argv)
    root = Path(args.root)
    pub_seed = dict(kv.split("=", 1) for kv in args.published)
    mod_seed = dict(kv.split("=", 1) for kv in args.modified)

    holds = load_json(root / "data/publish-holds.json", {"holds": []})
    hold_map = {h["story_key"]: h for h in holds.get("holds", [])}
    manifest = load_json(root / "data/dated-pages.json", {"pages": {}})
    pages = manifest.setdefault("pages", {})

    problems, changes = [], []

    # Gather entries from both hubs.
    entries = {}
    hub_htmls = {}
    for kind, cfg in KINDS.items():
        hub_path = root / cfg["hub"]
        hub_html = hub_path.read_text()
        hub_htmls[kind] = hub_html
        for key, block, _s, _e in find_entries(hub_html):
            entries[key] = parse_entry(key, block)

    # HOLD GATE: a dated page must never exist for a held story, whatever
    # the hold status - and a held key must never sit in the manifest.
    for key, h in hold_map.items():
        kind = key.split("-")[0]
        date = key[len(kind) + 1:]
        base = "site/brief" if kind == "brief" else "site/market-tape"
        if (root / base / date / "index.html").exists():
            problems.append(
                f"HOLD VIOLATION: dated page exists for held story {key} "
                f"(status {h.get('status')})")
        if key in pages:
            problems.append(
                f"HOLD VIOLATION: held story {key} (status {h.get('status')}) "
                f"is present in data/dated-pages.json")
    if problems:
        for p in problems:
            print(p, file=sys.stderr)
        return 3

    # Decide nav neighbours among pages that exist or will exist this run.
    def will_exist(key):
        if key in hold_map:
            return False
        return key in entries

    ordered = sorted(entries.keys())
    stamp = iso_z(now_et())
    today_et = now_et().date()
    forced = set(args.page_key)
    for key in ordered:
        e = entries[key]
        if key in hold_map:
            changes.append(f"SKIP {key} (hold: {hold_map[key]['status']})")
            continue
        entry_date = dt.date.fromisoformat(e["date"])
        if (key not in pages and key not in forced
                and (today_et - entry_date).days > args.window_days):
            # Archive discipline (CEO ruling, 2026-10-24): no mass backfill.
            # Entries older than the recency window stay hub-only unless a
            # human names them one by one with --page-key.
            continue
        kind, date = e["kind"], e["date"]
        base = "site/brief" if kind == "brief" else "site/market-tape"
        page_path = root / base / date / "index.html"
        prev = pages.get(key)
        published = (prev or {}).get("published") or pub_seed.get(key) or stamp
        modified = (prev or {}).get("modified") or mod_seed.get(key) or published
        need = prev is None or not page_path.exists()
        if prev and prev.get("entry_sha") != e["sha"]:
            need = True
            modified = stamp
        if need:
            same_kind = [k for k in ordered if entries[k]["kind"] == kind and will_exist(k)]
            i = same_kind.index(key)
            nav = []
            if i > 0:
                pk = same_kind[i - 1]
                nav.append((f"← {entries[pk]['date_label']} {KINDS[kind]['label']}",
                            page_url(entries[pk])))
            sib_key = ("tape-" if kind == "brief" else "brief-") + date
            if sib_key in entries and will_exist(sib_key):
                nav.append((f"{entries[sib_key]['date_label']} {KINDS[entries[sib_key]['kind']]['label']} →",
                            page_url(entries[sib_key])))
            if i < len(same_kind) - 1:
                nk = same_kind[i + 1]
                nav.append((f"{entries[nk]['date_label']} {KINDS[kind]['label']} →",
                            page_url(entries[nk])))
            page_html = build_page(e, hub_htmls[kind], published, modified, nav)
            changes.append(f"WRITE {page_path.relative_to(root)} (published {published})")
            if not args.check:
                page_path.parent.mkdir(parents=True, exist_ok=True)
                page_path.write_text(page_html)
        pages[key] = {
            "kind": kind, "date": date, "url": page_url(e),
            "headline": e["headline"], "published": published,
            "modified": modified, "image": e["image"], "entry_sha": e["sha"],
        }

    # Hub Jump To links: point days with dated pages at the dated URL.
    for kind, cfg in KINDS.items():
        hub_path = root / cfg["hub"]
        hub_html = hub_htmls[kind]
        new_hub = hub_html
        for key, e in entries.items():
            if e["kind"] != kind or key in hold_map or key not in pages:
                continue
            new_hub = new_hub.replace(f'href="#{key}"', f'href="{page_url(e)}"')
        if new_hub != hub_html:
            changes.append(f"UPDATE {cfg['hub']} (Jump To links)")
            if not args.check:
                hub_path.write_text(new_hub)

    # News sitemap: pages published within the last 48 hours.
    cutoff = now_et() - dt.timedelta(hours=48)
    news_items = []
    for key in ordered:
        if key not in pages or key in hold_map:
            continue
        p = pages[key]
        if parse_iso(p["published"]) >= cutoff:
            news_items.append(p)
    news_xml = ['<?xml version="1.0" encoding="UTF-8"?>',
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
                'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">']
    for p in sorted(news_items, key=lambda x: x["published"], reverse=True):
        news_xml.append(
            "  <url><loc>{loc}</loc><news:news><news:publication>"
            "<news:name>MarketsOnDeck</news:name><news:language>en</news:language>"
            "</news:publication><news:publication_date>{pub}</news:publication_date>"
            "<news:title>{title}</news:title></news:news></url>".format(
                loc=SITE + p["url"], pub=p["published"], title=esc(p["headline"])))
    news_xml.append("</urlset>")
    news_path = root / "site/news-sitemap.xml"
    news_content = "\n".join(news_xml) + "\n"
    if not news_path.exists() or news_path.read_text() != news_content:
        changes.append("WRITE site/news-sitemap.xml")
        if not args.check:
            news_path.write_text(news_content)

    # Main sitemap: managed dated-pages block + honest hub lastmod.
    sm_path = root / "site/sitemap.xml"
    sm = sm_path.read_text()
    block_lines = []
    for key in ordered:
        if key not in pages or key in hold_map:
            continue
        p = pages[key]
        block_lines.append(
            f'  <url><loc>{SITE + p["url"]}</loc>'
            f'<lastmod>{p["modified"][:10]}</lastmod>'
            f'<changefreq>monthly</changefreq><priority>0.7</priority></url>')
    block = ("  <!-- dated-pages:start -->\n" + "\n".join(block_lines) +
             "\n  <!-- dated-pages:end -->\n")
    if "<!-- dated-pages:start -->" in sm:
        sm_new = re.sub(r"  <!-- dated-pages:start -->.*?<!-- dated-pages:end -->\n",
                        block, sm, flags=re.S)
    else:
        sm_new = sm.replace("</urlset>", block + "</urlset>")
    for kind, cfg in KINDS.items():
        dates = [e["date"] for e in entries.values() if e["kind"] == kind]
        if not dates:
            continue
        latest = max(dates)
        sm_new = re.sub(
            r'(<loc>' + re.escape(SITE + cfg["hub_url"]) + r'</loc><lastmod>)[^<]+(</lastmod>)',
            r"\g<1>" + latest + r"\g<2>", sm_new, count=1)
    if sm_new != sm:
        changes.append("UPDATE site/sitemap.xml (dated pages + hub lastmod)")
        if not args.check:
            sm_path.write_text(sm_new)

    if not args.check:
        mpath = root / "data/dated-pages.json"
        mpath.parent.mkdir(parents=True, exist_ok=True)
        mpath.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    for c in changes:
        print(c)
    print(f"dated pages: {len(pages)} | entries seen: {len(entries)} | "
          f"news items (48h): {len(news_items)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
