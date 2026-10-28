#!/usr/bin/env python3
"""Tests for scripts/build_dated_pages.py (dated Brief/Tape pages + hold gate).

Synthetic mini-repo in a temp dir; no network. Run:
  python3 -m unittest tests.test_dated_pages -v
"""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "build_dated_pages.py"

HUB = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{hub_title} | MarketsOnDeck</title>
<meta name="description" content="generic hub description">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta property="og:image" content="https://marketsondeck.net/assets/brand/badge-1200.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://marketsondeck.net/assets/brand/badge-1200.jpg">
<link rel="canonical" href="https://marketsondeck.net{hub_url}">
<meta property="og:title" content="{hub_title} | MarketsOnDeck">
<meta property="og:description" content="generic">
<meta property="og:url" content="https://marketsondeck.net{hub_url}">
<meta property="og:type" content="website">
<meta name="twitter:title" content="{hub_title}">
<meta name="twitter:description" content="generic">
<script type="application/ld+json">{{"@context": "https://schema.org", "@type": "WebPage"}}</script>
</head>
<body>
<header class="site-header">nav</header>
<main>
<div class="brief-main article-body prose daily-entries" id="latest-entry">
{entries}
</div>
<section class="daily-archive" id="older-entries">
<h2>Older entries</h2>
<ul>
{jumpto}
</ul>
</section>
<p class="footer-disclosure">Education only, not investment advice.</p>
</main>
<footer class="site-footer">foot</footer>
</body>
</html>
"""

ENTRY = """<div class="card daily-entry" id="{key}">
<div class="card-eyebrow"><span>{date_label}</span><span class="badge">{label}</span></div>
<h3>{headline}</h3>
<p><strong>S&amp;P 500 +1.00% &middot; Nasdaq +2.00%</strong> — the day in one line.</p>
<img src="/assets/images/{key}-chart-1.png" alt="chart">
<p>Body text for {key}.</p>
</div>"""


def entry(key, label, headline=None):
    date = key.split("-", 1)[1]
    y, m, d = date.split("-")
    import datetime as _dt
    label_date = _dt.date(int(y), int(m), int(d)).strftime("%B %-d, %Y")
    return ENTRY.format(key=key, date_label=label_date, label=label,
                        headline=headline or f"Story for {key}")


def jumpto(keys, label):
    return "\n".join(f'<li><a href="#{k}">{k} — {label}</a></li>' for k in keys)


class DatedPagesTest(unittest.TestCase):
    def setUp(self):
        import datetime as dt
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "site/brief").mkdir(parents=True)
        (self.tmp / "site/market-tape").mkdir(parents=True)
        (self.tmp / "data").mkdir()
        (self.tmp / "scripts").mkdir()
        today = dt.datetime.now().date()
        self.d_today = today.isoformat()
        self.d_yday = (today - dt.timedelta(days=1)).isoformat()
        self.d_old = (today - dt.timedelta(days=60)).isoformat()
        briefs = [f"brief-{self.d_today}", f"brief-{self.d_yday}", f"brief-{self.d_old}"]
        tapes = [f"tape-{self.d_today}", f"tape-{self.d_yday}"]
        (self.tmp / "site/brief/index.html").write_text(HUB.format(
            hub_title="Morning Brief", hub_url="/brief/",
            entries="\n".join(entry(k, "Morning Brief") for k in briefs),
            jumpto=jumpto(briefs, "Morning Brief")))
        (self.tmp / "site/market-tape/index.html").write_text(HUB.format(
            hub_title="After Market Tape", hub_url="/market-tape/",
            entries="\n".join(entry(k, "After Market Tape",
                                    headline=f"After Market Tape — Story for {k}")
                              for k in tapes),
            jumpto=jumpto(tapes, "After Market Tape")))
        (self.tmp / "site/sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            '  <url><loc>https://marketsondeck.net/brief/</loc><lastmod>2020-01-01</lastmod></url>\n'
            '  <url><loc>https://marketsondeck.net/market-tape/</loc><lastmod>2020-01-01</lastmod></url>\n'
            '</urlset>\n')
        # tape yesterday is under an ACTIVE hold; nothing else is held.
        (self.tmp / "data/publish-holds.json").write_text(json.dumps({"holds": [
            {"story_key": f"tape-{self.d_yday}", "status": "active",
             "set": "2026-01-01", "note": "test hold"}]}))

    def run_gen(self, *extra):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.tmp), *extra],
            capture_output=True, text=True)

    def test_pages_created_and_held_skipped(self):
        r = self.run_gen()
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertTrue((self.tmp / f"site/brief/{self.d_today}/index.html").exists())
        self.assertTrue((self.tmp / f"site/market-tape/{self.d_today}/index.html").exists())
        # Active hold: no dated page, and not in the sitemap either.
        self.assertFalse((self.tmp / f"site/market-tape/{self.d_yday}/index.html").exists())
        sm = (self.tmp / "site/sitemap.xml").read_text()
        self.assertNotIn(f"/market-tape/{self.d_yday}/", sm)
        self.assertIn(f"/brief/{self.d_today}/", sm)

    def test_recency_window_blocks_mass_backfill(self):
        r = self.run_gen()
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertFalse((self.tmp / f"site/brief/{self.d_old}/index.html").exists())
        r2 = self.run_gen("--page-key", f"brief-{self.d_old}")
        self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
        self.assertTrue((self.tmp / f"site/brief/{self.d_old}/index.html").exists())

    def test_schema_and_byline(self):
        self.run_gen()
        page = (self.tmp / f"site/brief/{self.d_today}/index.html").read_text()
        ld = json.loads(re.search(r'application/ld\+json">(.*?)</script>', page, re.S).group(1))
        art = ld["@graph"][0]
        self.assertEqual(art["@type"], "NewsArticle")
        self.assertEqual(art["author"]["@type"], "Organization")
        self.assertEqual(art["author"]["name"], "MarketsOnDeck")
        self.assertIn("max-image-preview:large", page)
        self.assertIn(f"https://marketsondeck.net/brief/{self.d_today}/",
                      re.search(r'rel="canonical" href="([^"]+)"', page).group(1))
        self.assertNotIn("Watkins", page)

    def test_hold_violation_fails_loudly(self):
        self.run_gen()
        bogus = self.tmp / f"site/market-tape/{self.d_yday}/index.html"
        bogus.parent.mkdir(parents=True)
        bogus.write_text("<html>should never exist</html>")
        r = self.run_gen()
        self.assertEqual(r.returncode, 3)
        self.assertIn("HOLD VIOLATION", r.stderr)

    def test_idempotent(self):
        self.run_gen()
        r = self.run_gen()
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertNotIn("WRITE site/brief", r.stdout)
        self.assertNotIn("UPDATE site/brief", r.stdout)


if __name__ == "__main__":
    unittest.main()
