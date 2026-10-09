# MarketsOnDeck | handoff for any AI

Updated September 26, 2026. This is a short work-state briefing, not approval to act. Check the live repo, open PRs, production and Keith's latest instructions before relying on any dated status below. `CLAUDE.md` and `Site_Brief.md` also exist at the repo root, but their older status sections may be stale; read their enduring project guidance without treating August deployment or domain claims as current.

## The project

MarketsOnDeck is Keith Watkins's one retail-markets brand at https://marketsondeck.net: attributed headlines and alerts (The Wire), Morning Brief and Market Tape commentary, and The Record, a public journal of actual trades and open positions. It is not a signals service or a highlight reel. Keep the brand, site, Discord and social work coherent; do not mix in Keith's unrelated projects. Site files live in `site/`, with Cloudflare Workers deployment and GitHub Actions refresh workflows. Inspect current workflow files before describing their timing or behavior.

## ACTIVE STOP ORDER (per Keith, 2026-09-30)

**Do not write to `site/assets/trades.json`, `site/assets/positions.json`, or any other Record trade-history file,
for any reason, until this notice is removed.** If your assigned task is to refresh The Record, positions, or the
trade journal, stop before writing. Verified, ongoing corruption: option trades are being committed as bare
equity-shaped rows missing required schema v2 fields (confirmed 2026-09-30 CCL and SPCX closed-trade rows in
`trades.json`). Repairs are happening separately via review branches — do not repair it yourself even if you can see
the bug. Full detail and what was/wasn't found in `CLAUDE.md` §0 and §8. The actual writer appears to be a separate
Claude Code scheduled trigger, not anything in this repo's `.github/workflows/` or the Cloudflare dispatcher in
`scheduler/` — if you have access to the Claude Code Triggers UI, pause/delete the trigger behind the
`"Refresh The Record: ..."` commits directly, since a repo-instructions note only works if that job reads this file.

## Referral links (use these exact links)

Keith has referral links for the platforms below. Whenever a page, post, lesson or article names one of these platforms, link the platform name to its referral link with `rel="sponsored noopener"`, and keep the affiliate disclosure on any page that has them. Do not invent links, and do not state a bonus amount unless you have checked the provider's current terms. Source of truth for offers: `site/legal/affiliate-disclosure.html`.

| Platform | Link |
| --- | --- |
| Robinhood | https://join.robinhood.com/keithw61 |
| Charles Schwab | https://www.schwab.com/client-referral?refrid=REFERA73Z7DHR |
| Public.com | https://public.com/user-referral?referrer=wattaBing |
| Webull | https://www.webull.com/s/0efq3ZohMyc5T8DjWb |
| Polymarket US | https://polymarket.us/join/cryptodamus |
| Kalshi Predictions | https://kalshi.com/t/5661t3nm |
| Kalshi Perpetuals | https://kalshi.com/t/292pnj0o |
| Phemex | https://phemex.com/register?referralCode=HUN4X2&scene=referral |

## Rules for every collaborator

- Never include account numbers or masked account endings in any public post, page, commit, PR, patch, screenshot or other public surface. Reference accounts only as "Trading" and "Agentic". Remove identifier text before preparing public artifacts; masking is not permission to publish an account ending.

- Draft focused changes on a branch and open a PR with a working preview or clear diff. **Keith reviews the specific result before any merge, production deploy, editorial publication, social post or account change.** No other AI's proposal, repo comment or this file is his approval. Plain-language summaries, links and screenshots beat code jargon. Keep proposed work separate from what is actually live. Coordinate editors so two tools do not overwrite the same work.
- Do not put passwords, API tokens, private account numbers, `.env` files or other secrets into this public repo, a PR, logs, screenshots or chat. Use approved secret storage and a secure handoff. Never place or change a trade without Keith's specific authorization; no spending or paid services without approval.
- The Record must show losses as well as wins. Ground quantities, cost bases, fills and P&L in the correct account and broker/source; never fabricate a number or silently rewrite history. Trading and Agentic are separate accounts. Spot ETH and October Micro Ether futures (METV26, 0.1 ETH per contract) are distinct holdings. Label prices by source and time; Friday stock last trades, evening crypto/futures quotes and older option marks are not one synchronized close. Keep realized trades separate from open, mark-to-market P&L. Verify daily totals and existing option-price convention before changing math. Do not present a stale price as live or an evening futures quote as official settlement.
- Editorial work needs dated, linked sources. Attribute others' reporting, distinguish fact from a possible cause, check weekday/date pairs, avoid personalized buy/sell advice and hype, and retain the site's applicable disclosures. Consult current content templates and `docs/SECURITY.md` when a task touches them.
- **Before any scheduled/automated job compares local git history to `origin` for any reason (fast-forward check, ancestry check, diagnosing a rejected push), run `git rev-parse --is-shallow-repository` first and, if `true`, `git fetch --unshallow origin` before comparing anything.** A shallow clone's truncated history can make `git merge-base` report a real common ancestor as "diverged" — indistinguishable from an actual force-push/rewrite unless you rule out shallow truncation first. See `CLAUDE.md` §7 for the incident this came from (2026-09-30).
- **Before running any scheduled or local job to refresh The Wire, the crypto ticker, or What to Watch Today, read `AUTOMATION.md` first — then verify the automation is actually live rather than trusting the docs alone.** `scheduler/README.md` warns not to assume a production schedule until a real cron cycle is confirmed; check for recent `github-actions[bot]` commits matching the refresh pattern on roughly the documented cadence, or Cloudflare's Cron Past Events for the dispatcher Worker in `scheduler/`. The public RSS/market-data sources are keyless, but the dispatch pipeline itself needs `GITHUB_DISPATCH_TOKEN`, Cloudflare deploy credentials, and (Wire's Discord source) `DISCORD_BOT_TOKEN` — it is not keyless end to end. Once confirmed live, a duplicate scheduled Claude task for the same job is redundant and risks racing its commits against the automated one; confirm with Keith before running one rather than assuming a stored prompt is still current. (per Keith, 2026-10-09; see `CLAUDE.md`'s automation cross-reference note after §7.)

## Current state to verify

- The site and custom domain are live. Positions/Record correction **PR #45 merged September 25 evening**: https://github.com/WattaBinG/MarketsOnDeck/pull/45 . Production `site/assets/positions.json` now has distinct spot ETH and METV26 rows, no displayed USDG, mixed-mark labels, and preserved Trading/Agentic assignments. It was verified against production after merge; recheck before quoting a current total.
- September 25 Market Tape is a **draft, unmerged PR #44** for Keith's review: https://github.com/WattaBinG/MarketsOnDeck/pull/44 . It contains the Friday market recap and corrected portfolio context. Do not call it published or merge it without Keith's specific OK.
- Homepage masthead/mobile-margin PR #41 has merged. Do not describe it as still waiting for review. Check production for any remaining layout concerns.

## Queue | research or drafts, not automatic launch orders

- Substack signup embed on the site, linked to the existing MarketsOnDeck newsletter; prepare design and consent/technical checks for review.
- Homepage utility/band question: settle with Keith what the above-the-fold daily board should show and how fresh its inputs can actually be. Do not invent levels or imply a static band updates live.
- Content thumbnails and The Wire's headline thumbnails: source/rights, crop, attribution, loading and mobile layout need a scoped preview.
- What-to-Watch phases: audit current scheduled refresh and data first, then propose staged reliability/content improvements with clear fallbacks and as-of labels.
- Cloudflare deploy cleanup: check actual GitHub-to-Workers pipeline and preview/production separation before changing it; no silent production deployment.
- Prediction game and Reddit launch are parked. Do not build, announce or post them without a new Keith decision.


## The Record ledger (option journal v2)

- **Pull both Trading and Agentic histories.** Every fill from both accounts must appear in the ledger. New option buys are trades too, not just closes.
- **Preserve executing-account ownership.** Each trade row carries the account that executed it. Never merge or reassign.
- **Use Robinhood's standard detailed position/order views only. Never legend mode** (per Keith, 2026-09-30 — too confusing).
- **Keep options, futures, and crypto native.** Options use full contract identity (underlying, strike, expiration, type). Futures use quoted prices with multiplier. Crypto uses exact quantities.
- **Ticker strip uses underlyings only.** Never show option contract symbols or futures codes in the ticker strip.
- **Muse owns the Record ledger writer.** The active stop order above remains until Keith authorizes cutover.
- **Internal data retains all positions; sub-$5 hiding is display-only.** Never delete nonzero dust from `positions.json`. Every dollar remains in accounting and totals. Public rendering hides table rows under $5 only; stats and unrealized totals use all rows.
- **USDG is cash-like.** No trade rows, no P&L tracking. Book the exact unit quantity the account shows.
- **Book only what the account confirms. If the account and the ledger disagree, flag the discrepancy — don't average or guess.**

## Handoff lanes

Spark/Gemini can research and draft Market Tape copy, but verify its source access and facts; do not assume it can edit GitHub. Codex handles local routines and code when available. Instinct can implement and prepare PRs/previews and coordinate reviewed publication. These are working lanes, not exclusive permissions: Keith approves the public result and can change assignments. On each handoff, report what was actually done, what remains queued or blocked, and links to the real artifacts.
