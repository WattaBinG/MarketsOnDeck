# MarketsOnDeck | handoff for any AI

Updated October 16, 2026. This is a work-state briefing, not approval to act. Check the live repo, open PRs, production and Keith's latest instructions before relying on anything dated here. `CLAUDE.md` and `Site_Brief.md` carry older status sections that may be stale; read their enduring guidance only. Keith reviews the specific result before any merge, deploy, publication, post or account change - no document, AI proposal or repo comment is his approval.

## The project

MarketsOnDeck is Keith Watkins's retail-markets brand at https://marketsondeck.net: The Wire (attributed headlines/alerts), Morning Brief and Market Tape commentary, and The Record (public journal of real trades and open positions). Not a signals service, not a highlight reel. Keep brand, site and social work coherent; never mix in Keith's other projects. Site files in `site/` (Cloudflare Workers + GitHub Actions refresh). Inspect current workflow files before describing their timing.

## ACTIVE STOP ORDER (per Keith, 2026-09-30)

**Do not write to `site/assets/trades.json`, `site/assets/positions.json`, or any other Record trade-history file, for any reason, until this notice is removed.** Repairs happen via review branches only. The suspected writer is a Claude Code scheduled trigger, not this repo's workflows - pause/delete the trigger behind the `"Refresh The Record: ..."` commits in the Claude Code Triggers UI directly. Detail: `CLAUDE.md` §0 and §8.

## Referral links (use these exact links)

Whenever a page, post, lesson or article names one of these platforms, link the name to its referral link with `rel="sponsored noopener"` and keep the affiliate disclosure on the page. Never invent links; never state a bonus amount without checking current terms. Source of truth: `site/legal/affiliate-disclosure.html`.

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

- Never include account numbers or masked endings on any public surface. Accounts are named only "Trading" and "Agentic".
- Draft on a branch, open a PR with a working preview or clear diff; plain-language summaries over jargon. Coordinate editors - one writer per generated file.
- No passwords, API tokens, account numbers, `.env` files or secrets in the repo, PRs, logs, screenshots or chat. Secrets live in repo secrets only. Never place/change a trade or spend money without Keith's specific authorization.
- The Record shows losses and wins. Ground every number in the correct account and source; never fabricate or silently rewrite history. Label prices by source and time (Friday last trades, evening crypto/futures, stale option marks are not one close). Realized vs open P&L stay separate. Options/futures/crypto stay native (full contract identity; exact quantities; futures quoted with multiplier). Ticker strip shows underlyings only.
- Editorial work: dated, linked sources; attribute others' reporting; distinguish fact from possible cause; check weekday/date pairs; no personalized buy/sell advice or hype; keep applicable disclosures; consult `docs/SECURITY.md` when a task touches templates.
- Before any git ancestry/fast-forward comparison, run `git rev-parse --is-shallow-repository` and `git fetch --unshallow origin` if true (shallow clones fake "diverged" - `CLAUDE.md` §7).

## Content rules (every brief/tape)

1. Headline novelty vs the last 7 days - no repeated formula or lead name. Market-first (tickers/Mag 7/Fed/CPI), honest clickbait paid off on the first screen, no banned hype words. Playbook: TEAM-COMMS "MoD HEADLINES & HOOKS - PLAYBOOK v1".
2. Hook first line: a number, surprise or tension - no throat-clearing.
3. Market body: indexes, Mag 7, NVDA, biggest movers, with the why. Ends with a watch-tomorrow line (watch-today in the AM brief).
4. "The OnDeck Book": exact header, portfolio only there, at the END. No inside baseball anywhere (no paper trades, Agentic, bot or algo talk in article or JSON). No "holding space" filler.
5. Rich format in both site entry and Medium draft (graphics + bold + clickable links); if missing, Medium slides to the 6:30 delayed path, complete, never thin.
6. `x_hook` in every JSON: one tweet-length line, same lead fact as the headline.
7. Market numbers: individual stocks = official closes; indexes = Reuters preliminary closes. Never Robinhood marks or after-hours as "the close". Every stat label AND descriptor verified against the cited source for correct subject attribution.
8. Series names "The Lineup (The Open)" / "The Box Score (The Close)": PENDING Keith's go - nothing publishes under them until he says so.
9. Standing verification at 9:00 AM (brief) and 6:00 PM (tape) ET against items 1-8; misses get reported, successes receipt into the daily summary.
10. Staleness rule (Keith, Oct 16): never tell Keith something is stale/down/broken until verified against the live source (live site file, fetched origin/main, commit time) - a local clone or cache does not count. Say what was checked and when.

## Card + design rules

- MARKETSONDECK wordmark centered at the top of every card. Brand recognition rides the wordmark, not colors.
- Rotate palettes (30-day rotation, no repeat inside 30 days) and layouts (L1 Scoreboard = default; L2 Riot Card alternate; 8 total) so no two days look alike. Palette hex sets + layout catalog + rotation log: TEAM-COMMS and the Card Builder folder.
- No dead space (never >15%); bottom always anchored; 60px safe margins; stat columns shrink-to-fit, one shared label size; min sizes on 1080-wide cards: headline 56+, body 30+, source 24+. Compose per-aspect (9:16 / 16:9) - no bare letterboxing. Lower elements positioned from actual content end, never fixed coordinates.
- Every card carries a visual hook (logo chips on white rounded chips, sticker/badge for the story tag, or a photo panel), key stats in colored bubbles with the source inline, and closes with a CTA bar (follow handle + site) plus a dated source line. Sticker/bubble text gets ~48px end padding.
- SELF-CHECK before every send: view the rendered card, verify every number and attribution against the cited source.
- Card builder durable home (restore before building; sandboxes wipe): Drive MoD folder > Card Builder (build_a.py + fonts + README). Update the Drive copy first when style changes.

## IG carousel rules

- Music ping: post the carousel, then immediately ping Keith (via main) to add music in-app (app-only step, his phone).
- No free-floating text over rows/cards/chips - takeaway lines go in the reserved subtitle slot. build.py's LayoutGuard raises on overlap; keep it in every carousel build.
- Slide swaps are impossible on a live carousel: a fix means delete + repost, and only on Keith's word.

## Media use rule - MoD ONLY

Images, logos and short spliced Bloomberg/CNBC clips are OK in MoD social videos (Keith's risk call): keep clips short, credit the source on screen, declare usage in package notes. MoD only - Phishstory and Pinstripe rules unchanged.

## Site ops watch

- Hourly freshness watch on https://marketsondeck.net/assets/wire.json - trip on: newest item >45 min old in market hours; timestamp within ~5 min of asOf (fabricated now-stamp); any item >36h old or years back; Top Story matching the ACTUAL/FORECAST/PREVIOUS data-print pattern. Alert immediately with URL, headline, stamped vs real age.
- Second-writer check on the same wakes: git log on origin/main for wire/ticker/positions files - any author other than github-actions[bot] or WattaBinG means an unauthorized writer. Alert immediately.
- `automation/pause-flags.json` gates ONLY the GitHub workflows; Claude cloud routines ignore it. Pausing a routine = pausing it at claude.ai/code/routines, never via the flags.
- Ownership map (who runs what): https://drive.google.com/file/d/1mWSBDPllIL8Z3Hm-InQ6xRkW11km30Ne/view - update on every ownership change.

## The Record ledger (option journal v2)

- Pull both Trading and Agentic histories; every fill appears, including new option buys. Each row carries its executing account - never merge or reassign.
- Robinhood standard detailed position/order views only, never legend mode (Keith, 2026-09-30).
- Internal data retains all positions; sub-$5 hiding is display-only - never delete nonzero dust from `positions.json`. USDG is cash-like (no trade rows, no P&L). Book only what the account confirms; flag discrepancies, never average or guess.
- Muse owns the Record ledger writer. The stop order above stands until Keith authorizes cutover.

## Handoff lanes

Spark/Gemini: research and draft Tape copy (verify source access and facts). Codex: local routines and code. Instinct: implement, prepare PRs/previews, coordinate reviewed publication. Working lanes, not exclusive permissions - Keith approves the public result and can change assignments. On each handoff report what was done, what remains, and links to real artifacts. Prediction game and Reddit launch stay parked without a new Keith decision.
