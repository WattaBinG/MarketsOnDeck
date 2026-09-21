# First Release — Handoff & Audit Doc

Written 2026-09-18 so Keith (and Claude, reading this repo) can audit the
first-release work without digging through chat history. Everything in this
release is review-only until Keith merges it. Nothing here is deployed to
production by these branches on their own.

## Architecture, in one pass

- The site is plain static HTML/CSS/JS in `site/`, deployed as Cloudflare
  Workers static assets (`wrangler.jsonc`, no build step).
- Cloudflare does not auto-deploy a git push. The three refresh workflows deploy their own successful commits with Wrangler using repository secrets; other pushes still require a manual Cloudflare deployment.
  Non-`main` branches get automatic preview URLs of the form
  `https://<branch-name>-marketsondeck.wattabing.workers.dev` — that is how
  the review previews work; they are separate from production and go away
  when the branch is deleted.
- All live numbers come from JSON files in `site/assets/` (`ticker.json`,
  `crypto.json`, `wire.json`, `wire-archive.json`, `watch-today.json`,
  `trades.json`, `positions.json`) that client-side JS renders. Who writes
  each file is the whole story of the site's automation:

| File | Writer today | Writer after this release |
|---|---|---|
| `crypto.json` | Claude Desktop routine on Keith's PC | `refresh-crypto.yml` GitHub Action, every 15 min |
| `wire.json` + homepage wire blocks | Claude Desktop routine | `refresh-wire.yml` GitHub Action, hourly, sticky lead |
| `watch-today.json` | Claude Desktop routine | `refresh-watch-today.yml` GitHub Action, Sun-Thu evenings |
| `ticker.json` (US stocks/ETFs) | Claude Desktop routine + Robinhood MCP quotes | unchanged — last verified snapshot, honest as-of label |
| `trades.json`, `positions.json`, The Record | Keith's brokerage-backed routines | unchanged |
| Morning Brief / Market Tape | authored (claude.ai routine opens draft PRs when credits exist) | unchanged — authored analysis, never scripted |

The GitHub Actions run in GitHub's cloud, commit straight to `main`, then deploy the committed snapshot with Wrangler. They do not need
Claude Desktop, Keith's Windows PC to be on, or any Claude credits.

## The pull requests, and how they interact

| PR | Branch | What it is | State |
|---|---|---|---|
| #17 | `fix/brief-2026-09-17-accuracy` | Morning Brief Sep 17 accuracy corrections (supersedes #15) | open |
| #18 | `fix/tape-2026-09-17-accuracy` | Market Tape Sep 17 accuracy corrections (supersedes #16) | open |
| #19 | `fix/webull-ticker-pipeline` | Webull OpenAPI ticker worker, 15-min cache + cron | open, **parked** — needs a paid Webull market-data subscription and a display-license check |
| #20 | `design/first-release-pass` | Design pass: homepage record band + equity curve, Wire filters/freshness stamps, Record mobile P&L fix, honest as-of/basis labels | open |
| #21 | `automation/self-running-updates` | This branch: GitHub Actions for crypto/wire/calendar, sticky-lead wire scoring, ticker-composition docs, this handoff doc | open |

Recommended merge order: **#17, #18** (correct the public articles first),
then **#20** (design), then **#21** (automation). Interactions to know:

- #21 rewrites the same `WIRE_TOP`/`WIRE_LIST` marker blocks the old routine
  used, byte-compatibly, so it works with #20's design pass.
- #21's crypto script adds a `source` field to `crypto.json`; the site's JS
  ignores extra fields, so #20 and `main` both render it fine.
- #19 overlaps conceptually with #21's "no free licensed US-equity feed"
  finding: if #19 is ever deployed (paid Webull subscription + license
  confirmed), update `AUTOMATION.md`'s ticker section at the same time.
- The older open Brief/Tape PRs (#2, #4-#9) are stale daily drafts; closing
  them loses nothing that #17/#18 don't supersede.

## Data sources and what we're allowed to publish

Verified 2026-09-18:

| Source | Used for | Public-display rights |
|---|---|---|
| Publishers' own RSS (CNBC, MarketWatch, Yahoo Finance, Benzinga, Investing.com, NBC News, France 24, Federal Reserve) | The Wire | Headline + link aggregation only — publisher's own headline, named source, outbound link. No article text copied. Same Fark/Drudge-style aggregation the site has always done. |
| Coinbase Exchange public market-data API | crypto.json | Public market data, no key; `source` field carried in-file. |
| BEA/BLS official calendars, Census economic-indicators calendar, Fed 2026 FOMC calendar, NYSE 2026 holidays, fixed weekly releases | watch-today.json | Official published schedules. |
| Twelve Data free tier | — | **Not licensed for public display** (internal non-display only; display starts at ~$149/mo Venture plan). https://support.twelvedata.com/en/articles/5332349-commercial-and-personal-usage |
| Robinhood / Alpaca / Webull / Massive / Alpha Vantage free tiers | — | Personal/internal-use only; **do not** pipe their quotes into the public site on a schedule without verified display rights. |

Rule that follows from this: brokerage MCP connectors (Robinhood, Webull)
stay **authoring-time only**. They inform Keith's own authored commits.
They are never wired into the GitHub Actions, never given credentials in
this repo, and their data is not republished autonomously.

## Known limitations (honest list)

- **US stock/ETF prices are a stale snapshot.** There is no free feed
  licensed for public display. The ticker shows its last verified snapshot
  with a visible as-of label and basis tooltip instead of pretending to be
  live. This is a deliberate choice, not a bug.
- **The calendar fails closed if an official BEA, BLS, or Census source is unavailable.** The prior verified snapshot stays published and the workflow reports red rather than silently dropping a major release. Trading holidays and FOMC dates are explicitly supported for 2026; a later year is rejected until its official calendars are loaded.
- **RSS quality varies.** Free feeds sometimes surface evergreen/opinion
  pieces with fresh timestamps. The corroboration scoring keeps genuinely
  big stories on top; the promo/filler blocklist (`BLOCK` in
  `refresh_wire.py`) is the tuning knob.
- **GitHub Actions cron is best-effort** — scheduled runs can be delayed a
  few minutes under load. Fine for this site.
- **Morning Brief / Market Tape have no free autonomous writer.** A
  template would produce invented commentary, which this project bans.
  They resume when Keith has Claude credits again, or as reviewed drafts.

## Rollback

Every version of every file is in git, and production only changes when
`main` changes.

- **Unmerged PR:** close it. Nothing else to do — production never touched.
- **Merged PR:** revert the merge (`git revert -m 1 <merge-commit-sha>`)
  and push; Cloudflare redeploys `main` in a minute or two. Reverting just
  the automation is: delete the three files in `.github/workflows/` (or
  toggle them off under GitHub → Actions → ⋯ → Disable workflow) and revert
  the `scripts/` + `AUTOMATION.md` commit.
- **Workflow misbehaving:** Actions tab → select workflow → Disable. The
  site keeps the last good data files; every file shows its own age.
- **Old routines:** the Claude Desktop routines were only paused, not
  deleted — re-enable them if the Actions are retired.
- **Previews:** delete a branch and its `*-marketsondeck.wattabing.workers.dev`
  preview URL stops existing.

## Claude / MCP handoff notes

If Keith points Claude Code (or Claude Desktop) at this repo:

1. Read this file and `AUTOMATION.md` first; they describe the current
   ground truth of how the site updates.
2. After #21 merges, the local Claude Desktop scheduled routines for
   **crypto**, **The Wire**, and **What to Watch Today** should be turned
   off — the Actions cover those files, and two writers for one file will
   fight. The Morning Brief / Market Tape / Record routines do not conflict
   with the Actions and are Keith's call to keep or retire.
3. Brokerage MCP connectors (Robinhood, Webull) are authoring-time tools:
   use them to ground Keith's authored numbers, never commit tokens or
   account data, and never wire them into scheduled publishing (licensing
   above).
4. When editing `site/index.html`, keep the `WIRE_TOP_START/END` and
   `WIRE_LIST_START/END` marker structure exactly intact — the hourly
   Action rewrites between those markers and a broken marker breaks the
   wire update.
5. Accuracy rule that caught real bugs already: Brief, Tape, Record, and
   Overview all read the same numbers — check them against each other
   before opening a content PR.

## Audit checklist (what to verify when reviewing this release)

- [ ] `wire.json` `asOf` is recent; `topStory.leadSince` behaves (stable
      while the story leads, resets on a new lead); workflow run log shows
      the score table and the lead decision.
- [ ] `crypto.json` `asOf` within ~15 min during a run; `source` field
      present; change basis is the 24h open, as labeled.
- [ ] `watch-today.json` matches the next trading day's known events.
- [ ] Homepage wire list items all link out to real publishers; no copied
      article text anywhere.
- [ ] Ticker shows its as-of label visibly; nothing on the site claims
      "real-time" US equity data.
- [ ] No credentials, tokens, account numbers, or position sizes anywhere
      in the repo or workflow logs.
