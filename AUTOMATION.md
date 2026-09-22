# MarketsOnDeck Autonomous Updates

How the site keeps itself fresh with **no Claude Desktop, no Windows PC, no
Claude credits, and no paid data feeds**. Everything here is deterministic:
scripts fetch public data and rewrite data files. Nothing invents prices,
headlines, or commentary.

| What | Workflow | Cadence | Source |
|---|---|---|---|
| Crypto ticker (`assets/crypto.json`) | `refresh-crypto.yml` | every 15 min | Coinbase Exchange public market-data API |
| The Wire (`assets/wire.json`, `wire-archive.json`, homepage blocks) | `refresh-wire.yml` | hourly, with a sticky lead story | publishers' own public RSS feeds, the public Walter Bloomberg Telegram mirror (labeled unofficial), and Keith's own Discord news channel (via his bot) |
| What to Watch Today (`assets/watch-today.json`) | `refresh-watch-today.yml` | 7 PM ET Sun-Thu (rolls to the next trading day) | BEA and BLS official calendars, Census economic-indicators calendar, Fed + NYSE published calendars, fixed weekly releases |

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
   covering it = more important), a market-relevance bonus (macro /
   broad-market / mover keywords), and a magnitude bonus (record / crisis /
   emergency / extreme-move language — Keith's Drudge rule: the biggest,
   most attention-grabbing current story leads, not the freshest). Source
   weights: Federal Reserve, EIA and SEC 2.0 (official/regulatory primary
   sources), CNBC and MarketWatch 1.5, everything else 1.0. Items whose feed
   omits a publish time score as if 12 hours old, so evergreen filler cannot
   win on fabricated freshness.
3. Sticky rule: the incumbent lead keeps its slot while its story's score
   is at least 70% of the best challenger's and its newest item is under 30
   hours old. A clearly bigger new story (more than ~1.4x the incumbent's
   score) takes the slot immediately.
4. Everything is auditable: the full score table and the lead decision
   ("lead held" / "new lead") are printed in the workflow run log, the
   commit message carries the decision, and `wire.json`'s `topStory` has a
   `leadSince` timestamp. Other versions of the lead story are kept off the
   list so the same story never appears twice on the homepage.
5. Walter Bloomberg items can join any story cluster, but a story carried
   ONLY by the unofficial mirror can never occupy the lead slot — it can
   appear in the list, clearly labeled, until a publisher confirms it.

## The Wire's non-RSS sources (added 2026-09-21)

- **Walter Bloomberg (unofficial mirror).** The public Telegram preview at
  t.me/s/WalterBloomberg is parsed hourly. Every item keeps its exact post
  timestamp, links to the Telegram post, and is labeled "Walter Bloomberg
  (unofficial mirror)". The last message ID is cached in
  `data/wire-state.json` as a high-water mark. Any HTML or rate-limit
  breakage skips the source (fail open); it never counts toward the feed
  success ratio, so the Wire never depends on it.
- **Keith's Discord news channel.** His server aggregates headlines and
  links from several sources; the whole channel is a wire source. His
  existing "MarketsOnDeck Reader" bot reads it hourly over the REST API
  (`after=` the cached last message ID, pagination capped at 300 messages,
  429 `retry_after` honored). Only messages with both text and an outbound
  link become items. Token comes from repo secret `DISCORD_BOT_TOKEN`,
  channel from repo variable `DISCORD_NEWS_CHANNEL_ID`; when either is
  missing the step prints a skip notice and the Wire is unaffected.
- Both non-RSS sources get up to 4 guaranteed list slots so high-volume RSS
  cannot crowd fresh mirror/Discord items off the page between hourly runs.

## AI section (2026-09-22)

Two pieces, both keyless and fail-closed:

1. **AI wire category.** `scripts/refresh_wire.py` classifies AI-industry
   headlines (OpenAI/ChatGPT, Anthropic/Claude, Gemini, Grok, DeepSeek,
   Perplexity, LLM/generative-AI terms) into an "AI" category and pulls two
   dedicated desks, TechCrunch AI and The Verge AI (both verified keyless
   2026-09-22; VentureBeat's feed 429s bots and is not used). The filter
   tabs build from whatever tags the wire contains, so the AI tab appears
   on its own. Stock-action headlines stay in Movers even when they
   mention AI.

2. **Top AI Tools strip.** `scripts/build_ai_strip.py` (hourly in the wire
   workflow) ranks the tools in `data/ai-tools.json` by Apple's public US
   Top Free Apps chart (`rss.applemarketingtools.com`, keyless, official).
   The chart is the whole ranking story: a tool that falls off the chart
   falls off the strip, and a new entrant appears once it charts and has a
   config line. Link precedence per tool: Keith's `referralUrl` (drop-in
   slot, zero code changes) > `siteUrl` > the app's App Store page from
   the chart feed. No URL is ever invented; any fetch failure keeps the
   last published strip.

## First-seen timestamps (Keith's freshness rule)

Every Wire item carries `firstSeen`: the time the story first posted to the
Wire, kept as ranking moves it up or down — never a last-refreshed time.
The homepage shows it on each item and on the top story (falls back to the
publisher timestamp on older snapshots).

## Ticker composition (three layers)

The ticker is deliberately *not* a fixed market strip. `ticker.json` and
`crypto.json` express it in three layers, per Keith (2026-09-18, pinned
set updated 2026-09-22):

1. **Permanent benchmarks** — always present: BTC, ETH, SOL (the
   `crypto.json` strip, automated every 15 min) and SPY, QQQ, DIA, IWM,
   USO for oil (the `pinned` list in `ticker.json`, rendered in the
   pinned bar).
2. **Keith's portfolio** — derived by the cloud from
   `site/assets/positions.json` (equities, option underlyings, and
   crypto), flagged `"held": true`. Only the symbol is flagged — never
   sizes or account data. The cloud automation still never touches
   brokerage credentials or runs the MCP connectors; it reads only the
   positions snapshot Keith's own local routine committed.
3. **Rotating daily set** — the remaining symbols, re-picked at every
   local routine run from the day's high-volume names, major movers,
   market-important stories, and what the audience is watching. Churning
   is the point: never carry yesterday's pick forward (the LULU lesson).
   The full routine lives in `docs/TICKER-LOCAL-ROUTINE.md`, including a
   paste-ready prompt for any AI client.

Mechanical enforcement: the hourly wire workflow runs
`scripts/build_ticker.py`, which rebuilds the strip from layers 1 and 2
plus the local routine's layer-3 pick, dedupes across layers (a symbol
shows up exactly once — ETH stays in the crypto pin even though Keith
holds it), and caps the strip at 15, trimming movers first. Prices are
never invented in the cloud: they carry over from the last local
snapshot, and symbols without a quote render "--" under the visible
as-of label.

Data-rights rule for the ticker: Robinhood, Alpaca, Yahoo Finance, and the
other free sources verified on 2026-09-18 are licensed for personal/internal
use only, so they may inform authoring but nothing here republishes their
data on a schedule. Until a display-licensed feed exists, `ticker.json`
keeps its last verified snapshot with a visible as-of label and basis
tooltip (the honesty layer from PR #20). PR #19 (Webull OpenAPI worker) is the
parked starting point if a licensed feed is ever added. The local
routine that writes prices is documented in `docs/TICKER-LOCAL-ROUTINE.md`.

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
