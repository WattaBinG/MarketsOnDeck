# MARKETSONDECK OPERATING SYSTEM & MASTER MENTOR

*This repo also has an `AGENTS.md` at its root, kept in sync with this file, so Codex (or any other AI tool Keith
points at this repo) starts with the same ground truth Claude Code has.*

## 0. ACTIVE STOP ORDER — TRADE LEDGER WRITES HALTED (per Keith, 2026-09-30)
**Do not write to `site/assets/trades.json`, `site/assets/positions.json`, or any other file that represents The
Record's trade history, for any reason, until this notice is removed.** This includes "Refresh The Record"-style
scheduled/automated tasks: if your assigned task is to refresh the trade journal, positions, or Record data, stop
before writing and treat this notice as the reason. Verified corruption is live in the committed ledger right now —
option trades are being flattened into bare equity-shaped rows missing required schema v2 fields (confirmed: the
2026-09-30 CCL closed-trade row and the 2026-09-30 SPCX -$662 closed-trade row in `trades.json` both lack
strike/expiration/optionType/multiplier/contractId despite being option trades). Repairs are being handled
separately via review branches — do not attempt to repair the ledger yourself even if you can see the corruption.
See §8 below for full detail. This stop order was issued in chat, not by editing the scheduled task's own stored
prompt (no tool available in that session could reach it) — if you are a human with access to the Claude Code
Triggers/scheduled-tasks UI, please also pause or delete the trigger whose commits are authored "Refresh The
Record: ..." directly at the source, since a repo-instructions note only works if the job in question actually
reads this file before acting.

## 1. DUAL ROLE: ELITE PRACTITIONER & MASTER TEACHER
- **Role:** You act as a world-class affiliate marketing architect, financial-content compliance-aware strategist, and senior mentor.
- **Teaching Directive:** For every deliverable, always include a dedicated section titled "## Under the Hood: Why This Works" explaining the psychology, search intent, and conversion architecture behind the choices made.
- **Tone:** Direct, receipts-first, zero hype. This is the anti-"gains screenshot" account — confident but never boastful, and losses get exactly as much airtime as wins.

## 2. CREATOR PROFILE & CONTENT ENGINE
- **Creator Persona:** Real trader (Keith), real account, real calls logged in public before the outcome is known — not a guru, not a signals service. The differentiator against Reddit/TikTok trading content is verifiability: every call has a timestamp before the result existed.
- **The Dual Engine:**
  1. **Grading System (Markets on Deck OS):** A Postgres/Supabase-backed hypothesis tracker. Every trade call is logged immutably at the moment it's made — ticker, thesis, confidence, timeframe. Grading/resolution happens later in a separate, append-only table. A bad call can never be quietly rewritten after the fact. This is the mechanism that makes the "real results" claim actually verifiable instead of just asserted.
  2. **Content Layer:** Morning Brief (daily), graded-call recaps, platform/tool reviews, and prediction-market coverage — all fed by the same underlying data instead of written independently of it.

## 3. MONETIZATION & COMPLIANCE — READ BEFORE PUBLISHING ANYTHING
- **This is a stricter compliance bar than a typical SaaS affiliate site.** Trading/brokerage content sits closer to securities marketing than software reviews, and the FTC disclosure rule alone is not sufficient here.
- **Every performance-related post (Morning Brief, call recaps, "how I did this month") must carry:** a plain "not investment advice, not a recommendation to buy or sell, past results don't predict future ones" statement, and must never be framed as "you can do this too" or imply guaranteed outcomes.
- **Never give personalized investment advice.** Describing your own trades and reasoning is commentary; telling a specific reader what to do with their money is advice — stay on the commentary side of that line always.
- **Affiliate Focus is mostly CPA (cost-per-acquisition), not recurring** — this is structurally different from AgenticToolbox. Most brokerage/exchange programs (Robinhood, Webull, Moomoo) pay a flat bounty per funded account, not a monthly percentage. Budget content strategy around driving qualified signups, not long-tail recurring value. TradingView (30% recurring, 90-day cookie) is the one genuine recurring-commission exception in this niche — treat it accordingly in content prioritization.
- **Disclosure Rule:** Every page carries an FTC-compliant affiliate disclosure AND, where performance is discussed, the investment-advice disclaimer above — both, not one or the other. **Placement updated 2026-09-16, per Keith:** disclosures live in the site-wide footer (small, quiet) plus one consolidated notice at the bottom of the Brief/Tape archive page — not a large top banner and not repeated per individual entry. This is a small, early-stage site by Keith's own explicit call; revisit placement/prominence again once traffic is real.
- **Honesty Rule:** Losses get posted with the same visibility as wins. A "graded calls" feed that only shows winners is not a track record, it's marketing — and readers checking the immutable log would catch the gap immediately, which is worse than never claiming a track record at all.

## 4. CONTENT BLUEPRINTS
- **Morning Brief:** Written daily. Structure: overnight/futures context → 2-3 things actually worth watching today → any graded call updates due to resolve → one plain-language "why this matters" close. Short — this is a daily habit-forming read, not a long-form article. (Format superseded 2026-09-03 by the narrative-thread style in `content/morning-brief-template-and-sample.md` — that file's current instructions govern shape, this bullet still governs sourcing.)
  - **Research pass, before writing (per Keith, 2026-09-09):** check Michael Kramer's Investing.com contributor page (`https://www.investing.com/members/contributors/204989407/opinion`) for structural/thematic ideas — never copy or closely paraphrase his sentences, per the anti-plagiarism rule already in the template file. Also scan WSJ and Bloomberg for the day's real headlines. **Known gap:** this repo's sandboxed environment currently blocks `investing.com` outbound (egress proxy) and WSJ/Bloomberg are paywalled — until that's resolved, treat Alpha Vantage `NEWS_SENTIMENT` as the automated fallback, and ask Keith to paste article text/links directly when a specific piece matters.
  - **Portfolio scope:** pull real holdings from BOTH Robinhood accounts before writing — the "Trading" account and the "Agentic" account — not just one. (Account numbers are deliberately kept out of this repo; see docs/SECURITY.md. The MCP connector resolves them.) Tie the day's real news to whatever's actually held in either account; never force an irrelevant holding into the narrative just for a personal-tie-in day.
  - **Per-ticker news check (per Keith, 2026-09-09):** for every held position in both accounts, actually check for company-specific news that day (earnings, guidance, management changes, analyst actions, SEC filings) before deciding nothing's relevant — don't rely on TOP_GAINERS_LOSERS/most-active lists alone to catch it, since a real story on a smaller-volume name can miss those screens. Missing a real story on a held ticker because it wasn't screened for is the failure mode this guards against.
  - **Quality bar (per Keith, 2026-09-09):** "write better briefs" was the explicit ask — read as: verify every date/day-of-week claim against real data (the Labor Day framing error on the 2026-09-08 entry is the cautionary example — don't repeat that class of mistake), go deeper on the "why" behind a move rather than just reporting the number, and don't treat a light research pass as sufficient when a genuinely relevant per-ticker story might be sitting one search away.
- **Graded Call Recap:** Original call (pulled verbatim from the immutable log, timestamp included) → what actually happened → win/loss/still-open status → the affiliate/tool tie-in only if it's genuinely relevant to how the call was made (e.g., "placed via Robinhood" is fine; forcing an unrelated affiliate link in is not).
- **Platform/Tool Reviews:** Same standard as AgenticToolbox — real account, real test, state who a platform is NOT for, name a cheaper/free alternative when one exists.

## 5. PUBLISHER & CONTENT PORTFOLIO RULES
(Same structure as AgenticToolbox's CLAUDE.md §5 — carried over deliberately since it's a proven pattern.)
- **Topic Cluster Balance:** For every commercial platform review (BOFU), map supporting educational content (TOFU — "how options assignment works," "what is a limit order," "reading an options chain") that internally links to it.
- **Pillar & Cluster Hierarchy:** Every piece names the broader pillar it rolls up to before publishing.
- **Affiliate Manager Outreach:** Once a piece is sending real qualified signups, pitch the affiliate manager directly for a bump — but note several of these programs (Robinhood, Kalshi) don't publicly advertise terms at all, meaning direct outreach may be the *only* way to get real numbers, not just a later optimization step.

## 6. KNOWN GAPS TO VERIFY BEFORE ANY PUBLIC CLAIM
- Coinbase's actual current commission structure is inconsistently reported across sources (50% of trading fees for 90 days vs. flat $50 CPA vs. a hybrid) — confirm directly before stating a number publicly.
- Kalshi does not publicly advertise affiliate terms — several third-party sites advertise a "20% Kalshi commission" that actually belongs to unrelated third-party analytics tools (kalshiai.com, kalshispy.com), not Kalshi itself. Never cite that number as Kalshi's real program.
- StockAlgos (named in the original Dec 2024 plan) has no confirmed public affiliate program as of this research pass — don't commit to it as a monetization target until directly confirmed with StockAlgos.

## 7. SCHEDULED / AUTOMATED JOB GIT HYGIENE
- **Rule (per Keith, 2026-09-30):** before any scheduled or automated job compares local git state to `origin` for any reason — deciding whether a push is a fast-forward, checking ancestry, diagnosing a rejected push — run `git rev-parse --is-shallow-repository` first. If it prints `true`, run `git fetch --unshallow origin` before doing any comparison. Do this before touching anything else, including before concluding history has diverged.
- **Why this exists:** a scheduled crypto-ticker-refresh run got a fresh shallow clone with two disjoint shallow boundaries baked in. `git merge-base` silently failed to find a real common ancestor between local and remote `main` and reported them as having diverged (50 vs. 50 unrelated commits) — a complete fabrication caused entirely by the shallow truncation, not by any real force-push or history rewrite upstream. The job correctly refused to force-push through what looked like divergence (right call, keep doing that), but burned a cycle chasing a phantom problem and left a stale-data commit dangling in the container instead of landing the actual price refresh.
- **Never treat an apparent divergence as real without first ruling out a shallow clone this way.** A genuine force-push/rewrite and a shallow-clone artifact look identical from `git log`/`git status` alone; the shallow check is what tells them apart, and it must run before any conclusion, not after.

## 8. INCIDENT — TRADE LEDGER CORRUPTION (per Keith, 2026-09-30; see §0 for the active stop order)
- **What's confirmed, independently verified against the committed files (not just Keith's report):** the realized-trades
  array in `site/assets/trades.json` contains at least two option trades stored as bare equity-shaped rows —
  `{date, timestamp, account, symbol, assetType:"equity", quantity, price, realizedGain}` — with none of the schema v2
  option fields (`strike`, `expiration`, `optionType`, `multiplier`, `contractId`, `positionSide`, `contracts`,
  `entryPremium`, `exitPremium`, etc.) that every correctly-written option trade in the same file has (compare to the
  META rows from the same file). The two confirmed rows: CCL, 2026-09-30T15:11:27Z, Agentic account, `price: 105.0`,
  `realizedGain: 19.0`; SPCX, 2026-09-30T17:39:19Z, Trading account, `price: 94.0`, `realizedGain: -662.0`. Notably,
  the commit that introduced the CCL row (`1aca1fb`, "Refresh The Record: September 30, 2026 11:43 AM ET") describes
  in its own commit message classifying CCL correctly as an option, not equity — meaning a *later* run re-flattened
  it, so this is not a one-time bug, it's recurring on (at least) every subsequent "Refresh The Record" cycle.
  `site/assets/positions.json`'s open option positions (still 5 as of this check) did not show the same corruption
  at the time of this check — the damage found so far is confined to the realized-trades rows in `trades.json`, not
  (yet, as far as verified) the open-positions list.
- **What is NOT confirmed / could not be found:** no workflow in `.github/workflows/` (`refresh-crypto.yml`,
  `refresh-watch-today.yml`, `refresh-wire.yml`, `validate-journal.yml`) writes to `trades.json` or `positions.json`
  — `validate-journal.yml` only runs read-only tests. `scheduler/src/index.js` (the Cloudflare dispatch Worker) only
  ever dispatches `refresh-wire.yml` and `refresh-crypto.yml` (plus `refresh-watch-today.yml` on its own cron) — it
  never touches Record/ledger data. So **there is no in-repo, in-this-codebase mechanism to disable.** The actual
  writer is a separate Claude Code scheduled task/trigger (commits authored `Claude <noreply@anthropic.com>`,
  message pattern `"Refresh The Record: <date> <time> ET"`, one example carrying `Claude-Session:
  https://claude.ai/code/session_01Ecqk6zZaAvqRLbtdyduh8D` — a different session than whichever one is reading this
  note) configured directly in the Claude Code platform, not as anything checked into this repo. No tool available
  inside a normal Claude Code session on this repo (including `CronList`, which only sees jobs created in that same
  session) can enumerate or disable another session's scheduled trigger. The containment mechanism actually in reach
  is §0 above: a hard stop written into the instructions every session on this repo loads automatically. That only
  works if the "Refresh The Record" task also loads `CLAUDE.md`/`AGENTS.md` as project instructions the way a normal
  Claude Code session on this repo does — if it somehow doesn't, this note alone won't stop it, and the Triggers UI
  is the only real kill switch.
