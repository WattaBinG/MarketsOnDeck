# MarketsOnDeck Autonomous Updates

How the site keeps itself fresh with **no Claude Desktop, no Windows PC, no
Claude credits, and no paid data feeds**. Everything here is deterministic:
scripts fetch public data and rewrite data files. Nothing invents prices,
headlines, or commentary.

| What | Workflow | Cadence | Source |
|---|---|---|---|
| Crypto ticker (`assets/crypto.json`) | `refresh-crypto.yml` | every 15 min | Coinbase Exchange public market-data API |
| The Wire (`assets/wire.json`, `wire-archive.json`, homepage blocks) | `refresh-wire.yml` | hourly | publishers' own public RSS feeds |
| What to Watch Today (`assets/watch-today.json`) | `refresh-watch-today.yml` | Sun-Thu evenings | BEA official calendar (ICS), Fed + NYSE published calendars, fixed weekly releases |

Cloudflare deploys `main` automatically, so each workflow commit is live
within a minute or two. Each workflow also has a **Run workflow** button in
GitHub → Actions for a manual kick.

## Sources and why they are OK to publish

- **The Wire** aggregates the *headlines and links* from public RSS feeds
  (CNBC, MarketWatch, Yahoo Finance, Benzinga, Investing.com, NBC News,
  France 24, Federal Reserve). It shows the publisher's own headline, names
  the source, and links out — the same Fark/Drudge-style aggregation the site
  has always done. No article text is copied or republished.
- **Crypto prices** come from Coinbase Exchange's public market-data API
  (no key). The file carries `source: "Coinbase Exchange (public market
  data)"`. Change/percent are versus the rolling 24-hour open reported by
  Coinbase — the same basis the file already used.
- **The calendar** uses official published schedules only: BEA's ICS feed,
  the Fed's 2026 FOMC calendar, NYSE's 2026 holiday list, and fixed weekly
  releases (jobless claims, EIA reports, Baker Hughes, CFTC COT, quad
  witching). Days with no known events leave the previous file in place
  rather than blanking it.

## Honesty and failure behavior

- Every data file carries its own `asOf` timestamp, and the site displays it,
  so stale data always shows its age instead of posing as live.
- If a source fails, the workflow exits red and **commits nothing** — the
  last good snapshot stays up. GitHub emails the repo owner on workflow
  failure, so a dead feed is visible instead of silent.
- First Wire run after merge archives a one-time backlog of recent headlines
  into `wire-archive.json` (capped at 200). After that it trickles.

## What this deliberately does NOT automate

- **US stock/ETF intraday prices.** No free feed is licensed for public
  website display: Twelve Data, Alpaca, Robinhood, Webull, Massive, and
  Alpha Vantage free tiers are all personal/internal-use only (verified
  2026-09-18; Twelve Data public display starts at ~$149/mo). The honest
  zero-cost fallback is what ships: the ticker shows its last verified
  snapshot with a visible as-of label and basis tooltip, never a "live"
  claim. If a licensed feed is ever added, PR #19 (Webull OpenAPI worker)
  is the parked starting point.
- **The Record / positions / trades.** Those come from Keith's actual
  brokerage accounts; automating them would need brokerage API access and is
  out of scope here.
- **Morning Brief and Market Tape.** These are authored analysis, not data.
  No free autonomous writer exists, and a template would produce invented
  commentary — which this project bans. They stay PR-reviewed and human/AI
  authored; when Claude credits exist again, the existing claude.ai routine
  (`trig_017Ph8RYYJqrhMYgHUDCG53W`) can resume opening draft PRs.

## Retiring the local routines

Once this is merged, the Claude Desktop scheduled routines for **crypto**,
**The Wire**, and **What to Watch Today** can be turned off — their GitHub
Actions replacements cover the same files. Keep or remove the others
(Morning Brief drafts, Record refreshes) as Keith prefers; nothing here
conflicts with them.
