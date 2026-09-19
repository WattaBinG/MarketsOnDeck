# MarketsOnDeck Autonomous Updates

How the site keeps itself fresh with **no Claude Desktop, no Windows PC, no
Claude credits, and no paid data feeds**. Everything here is deterministic:
scripts fetch public data and rewrite data files. Nothing invents prices,
headlines, or commentary.

| What | Workflow | Cadence | Source |
|---|---|---|---|
| Crypto ticker (`assets/crypto.json`) | `refresh-crypto.yml` | every 15 min | Coinbase Exchange public market-data API |
| The Wire (`assets/wire.json`, `wire-archive.json`, homepage blocks) | `refresh-wire.yml` | hourly, with a sticky lead story | publishers' own public RSS feeds |
| What to Watch Today (`assets/watch-today.json`) | `refresh-watch-today.yml` | Sun-Thu evenings | BEA and BLS official calendars, Census economic-indicators calendar, Fed + NYSE published calendars, fixed weekly releases |

Each refresh workflow serializes its commit/push with the other publishers and then runs Wrangler to deploy that exact committed snapshot. Deployment requires the repository secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`; if either commit, push, or deploy fails, the workflow stays red and the previous production snapshot remains live. Each workflow also has a **Run workflow** button in
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

## The Wire's lead story (sticky lead)

Keith's rule: refresh the wire as often as possible, but do not churn the top
slot — if the lead is still the day's dominant story, it stays. The script
does this deterministically, no AI-written headlines or summaries:

1. Every run clusters same-story headlines across feeds (normalized-token
   overlap, fixed threshold) so a story covered by three publishers is one
   story, not three items.
2. Each cluster scores as: sum over its items of (source weight x recency
   decay), multiplied by a corroboration bonus (more distinct sources
   covering it = more important) and a market-relevance bonus (macro /
   broad-market / mover keywords). Source weights: Federal Reserve 2.0,
   CNBC and MarketWatch 1.5, everything else 1.0. Items whose feed omits a
   publish time score as if 12 hours old, so evergreen filler cannot win on
   fabricated freshness.
3. Sticky rule: the incumbent lead keeps its slot while its story's score
   is at least 70% of the best challenger's and its newest item is under 30
   hours old. A clearly bigger new story (more than ~1.4x the incumbent's
   score) takes the slot immediately.
4. Everything is auditable: the full score table and the lead decision
   ("lead held" / "new lead") are printed in the workflow run log, the
   commit message carries the decision, and `wire.json`'s `topStory` has a
   `leadSince` timestamp. Other versions of the lead story are kept off the
   list so the same story never appears twice on the homepage.

## Ticker composition (three layers)

The ticker is deliberately *not* a fixed market strip. `ticker.json` and
`crypto.json` express it in three layers, per Keith (2026-09-18):

1. **Permanent benchmarks** — always present: BTC, ETH, SOL (the
   `crypto.json` strip, automated every 15 min) and SPY, QQQ, DIA
   (the `pinned` list in `ticker.json`, rendered in the pinned bar).
2. **Keith's portfolio** — `ticker.json` items flagged `"held": true`.
   These are supplied at authoring time by Keith's own routine using his
   brokerage connection (Robinhood via MCP, or Webull level-2). The cloud
   automation in this repo never touches brokerage credentials, never reads
   holdings, and never runs the MCP connectors; portfolio symbols only
   appear because Keith's authoring routine put them there, and only the
   symbol is flagged — never sizes or account data.
3. **Rotating daily set** — the remaining symbols, chosen at authoring
   time from the day's high-volume names, major movers, market-important
   stories, and what the audience is watching. This layer is expected to
   churn daily; layers 1 and 2 are stable.

Data-rights rule for the ticker: Robinhood, Alpaca, Yahoo Finance, and the
other free sources verified on 2026-09-18 are licensed for personal/internal
use only, so they may inform authoring but nothing here republishes their
data on a schedule. Until a display-licensed feed exists, `ticker.json`
keeps its last verified snapshot with a visible as-of label and basis
tooltip (the honesty layer from PR #20). PR #19 (Webull OpenAPI worker) is
the parked starting point if a licensed feed is ever added.

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
