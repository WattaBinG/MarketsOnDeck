# Morning Brief — Template + Real Sample

## The Format (revised 2026-09-03, per Keith — emulating Michael Kramer's Investing.com style)

Kramer's real posts (Mott Capital Management, published on Investing.com) are the reference point Keith wants to
emulate. Two of his actual pieces were studied directly for structure — not copied, the structure/approach is what
carries over, never his specific wording. What makes his format work:

1. **Open with yesterday's actual close, given meaning by a comparison point** — not just "the S&P was up 46bps,"
   but something like "the index closed at 7,631, versus 7,609 on June 2" — a reference point that tells the reader
   *why* the number matters, not just what it was.
2. **One connected analytical thread, in flowing paragraphs — not bullets.** Pick a real storyline for the day and
   follow it: each paragraph builds on the last, using specific real numbers throughout (not "volatility is low,"
   but "21-day realized volatility fell to 7.4%, about a 46bps daily move"). Multiple sub-threads are fine if they
   connect to one bigger-picture read (e.g., dispersion → CTA flows → oil → yields, all feeding one thesis).
3. **Charts as supporting evidence**, referenced inline as the thread develops (even just naming the chart/data
   series if an actual embedded chart isn't feasible yet).
4. **Never a directive prediction — always process language.** Kramer's pieces end on "we're watching for the
   trigger event," "I'd like to see X pull back first," never "this will happen." This already matches
   `CLAUDE.md` §3's compliance rule against directive language — Kramer's style and Keith's compliance
   requirement point the same direction, which is exactly why this format works here.

**Where this site's version diverges from Kramer's on purpose (keep these, they're Keith's actual differentiators,
not oversights):**
- **Tie the thread to a real held position when genuinely relevant** — Kramer is a pure market commentator with no
  personal-position angle; MarketsOnDeck's whole premise is real, personal, checkable trading. Weave this into the
  narrative naturally (as part of a paragraph, not a bolted-on separate section) — never force it on a day where
  nothing held is actually relevant.
- **Close with an explicit "why this matters" beat, in plain language.** Kramer writes for a sophisticated
  derivatives-literate audience and just ends on his last analytical point. Keith's audience is broader (retail
  traders/investors, not exclusively options/vol specialists) — so every brief still needs one closing sentence or
  short paragraph that translates the thread into "why a normal trader should care," even if the body itself gets
  more technical than the old bullet format did.
- **FTC + investment-advice disclaimer: covered once, at the bottom of the brief archive page, not per-entry
  (changed 2026-09-16, per Keith).** Previously every entry opened with its own disclosure paragraph; Keith wants
  that gone from individual entries — it's a small, early-stage site and the per-entry banner was too loud/repeated.
  `site/brief/index.html` now carries ONE disclosure notice near the bottom of the page (`.footer-disclosure` style,
  small/muted) covering every entry on it, plus the site-wide footer disclosure present on every page. **Do NOT add
  a disclosure paragraph to a new entry's card** — that page-bottom notice already covers it. If an entry needs a
  short factual note (e.g. "Drafted premarket, before the CPI release"), that's fine to keep as its own small italic
  line, just without the disclosure sentence itself.

5. **Selective week-ahead awareness (added 2026-09-09, per Keith).** Kramer routinely names specific upcoming
   scheduled events that are genuinely likely to move markets — a CPI/PPI print, a Fed or ECB meeting, a jobs
   report — usually in the opening or closing paragraph, with the actual date. Every brief should do the same,
   **but selectively**: only flag events that are (a) actually scheduled within roughly the next week and (b) the
   kind that realistically moves markets (CPI/PPI, FOMC/ECB rate decisions, NFP/jobs reports, and major earnings
   from mega-cap names the reader would recognize). This is explicitly NOT a full economic-calendar dump — skip
   minor/routine releases (housing starts, consumer sentiment revisions, regional Fed surveys, etc.) unless one of
   them is unusually relevant that week. Source real dates via WebSearch (search something like "US economic
   calendar this week" or the specific event + date) since Alpha Vantage's economic-indicator tools return
   historical time series, not a forward release calendar — never invent a date or figure; if a real date can't be
   confirmed, leave the event out rather than guess. One or two sentences is enough — this is a mention, not its
   own section.

---

## The After Market Tape — End-of-Day Wrap (added 2026-09-09, per Keith)

A second daily piece, published after the close (~4:15pm ET, once the day's real closing prints are in) —
**not a rename of the Morning Brief**, a companion to it. Morning Brief still opens the day; The After Market Tape closes
it. "Tape" here is plain market slang ("reading the tape") — this is unrelated to the buried predictions-ledger
feature that also used the name "The Tape" internally (`site/tape/`, still hidden from nav/robots.txt, still
parked). Two different things sharing a name on purpose; don't confuse them.

**Format — same narrative-thread discipline as the Morning Brief (see the numbered rules above), applied to the
close instead of the open:**
1. Open with the actual close, given meaning by a real comparison point (yesterday's close, a recent high/low,
   etc.) — same rule as the Morning Brief's rule 1.
2. One connected analytical thread through the day's real action — what actually moved, and why, in flowing
   paragraphs, not bullets.
3. Tie to a real held position when genuinely relevant, same as the Morning Brief.
4. Process language only, never directive.
5. Same selective week-ahead awareness as the Morning Brief — if something material is now one day closer (e.g. a
   CPI print landing the next morning), that's worth a closing-paragraph mention.
6. Close with the same "why this matters" plain-language beat.
7. Same disclosure handling as the Morning Brief (see above, updated 2026-09-16) — no per-entry disclosure
   paragraph; the page-bottom notice on `site/brief/index.html` already covers After Market Tape entries too.

**Publishing (changed 2026-09-16, per Keith):** Morning Brief and After Market Tape now each get their own page —
`site/brief/index.html` (Morning Brief only) and `site/market-tape/index.html` (After Market Tape only, unrelated to
`site/tape/`, the separate parked predictions feature). Each page has its own jump-list and its own set of `.card`
entries with ids `brief-YYYY-MM-DD` / `tape-YYYY-MM-DD` respectively. This reverses the 2026-09-02 "one shared page"
decision — Keith wants the two treated as genuinely separate daily pieces, each with real depth (account moves,
market news, and how it's affecting his specific holdings), not a shared feed. Still keep the type badge on each
card for now (harmless, and every existing entry already has one) even though it's no longer load-bearing for
telling entries apart on a page that's now single-type.

---

**Honest tradeoff to watch, not yet resolved:** this format is denser and takes real analytical work per entry —
it's no longer the ~30-second bullet read the original design leaned on ("a daily habit read, not an article").
That may be exactly what Keith wants now (it's what he's asking to emulate), but it's a real shift in the size of
the daily commitment — worth revisiting after a few real entries land, per the original template's own "reality
check on the daily commitment" note below.

---

## Full Coverage Requirement (added 2026-09-14, per Keith)

Both daily pieces (Morning Brief and After Market Tape) must cover, every time, not just when convenient:

1. **All four benchmarks, not just SPY** — SPY, QQQ, DIA (Dow proxy), and crypto (BTC/ETH/SOL). Pull benchmark
   levels from `site/assets/ticker.json` (refreshed at/near market open and close) rather than a fresh Alpha
   Vantage quote where possible — it's the site's own canonical figure and re-querying risks a stale-quote
   mismatch against numbers already published elsewhere on the site (this happened once, 2026-09-14, caught by
   a PR review bot). Pull crypto from `site/assets/crypto.json` (refreshed hourly, 24/7) the same way. Not every
   benchmark needs its own paragraph — weave them into the thread, but don't silently drop QQQ/DIA/crypto just
   because SPY is carrying the day's story.
2. **Both accounts, not just Trading** — pull positions from BOTH the Trading account AND the Agentic account via
   `get_accounts` → `get_equity_positions` for each (account numbers come from the live MCP call, never hardcode
   one in this repo — if an account number ever needs to appear in published prose, mask it to the last 4 digits
   only, e.g. •••8840). Same rule as before on when to mention a position: weave it
   in only if genuinely relevant to the day's real action; don't force an irrelevant holding into the thread just
   to cover both accounts. But both accounts must actually be checked every time — silently checking only Trading
   is the bug that prompted this note.
3. Everything else in this doc (narrative-thread format, process language, week-ahead awareness, disclosure block,
   "why this matters" close) still applies unchanged — this section adds required data coverage, not a new format.

---

## Real Sample — Rewritten in the New Style (same underlying facts as the original Aug 29, 2026 sample)

*Built from the same real data as the original bullet-format sample below — restyled to show the difference, not a
new day's data.*

**Disclosure:** This brief contains affiliate links and reflects my own opinions and positions. Nothing here is
investment advice or a recommendation to buy or sell any security.

---

### MarketsOnDeck Morning Brief

NVDA closed Friday at $227.98, up 8.74% on nearly 293 million shares — for context, that's roughly triple its
recent average daily volume, not a routine up-day. This is a name I actually hold, so it's worth walking through
rather than just flagging.

Volume that heavy on a single-name 8%+ move usually means one of two things: a real catalyst working through the
stock specifically, or a sector-wide rotation using NVDA as its most liquid vehicle. INTC moved alongside it,
+4.36% to $92.09 — not as dramatic, but enough to suggest this wasn't purely an NVDA-specific story. If semis
broadly are catching a bid, the read on today is different than if this was isolated to NVDA's own news.

Crypto, for comparison, stayed open all weekend as usual and barely moved — BITO up a modest 1.84%. Low drama
there is itself a small data point: whatever moved semis didn't spill into risk appetite broadly, which leans
toward "sector-specific" over "everything's repricing."

**Why this matters:** the open question today is whether this was a name-specific event or the start of a
sector-wide move — and since I'm actually holding the name in question, that's not an academic distinction. Worth
checking the actual news behind the move before reacting to it either way.

---

## Original Format (kept for reference — superseded 2026-09-03)

The old bullet format was: disclosure → **The One Thing** (1-2 sentences) → **Worth Watching** (2-3 bullets) →
**Any graded-call updates** (skip until live) → **Why This Matters** (one closing sentence). Faster to write, but
Keith wants the narrative-thread version above going forward. Keeping this here as a reference, not deleting it —
same "nothing gets quietly edited away" discipline as the rest of the site.

---

## Under the Hood (Internal Note — do not publish)

The reformat was driven by two real pieces of Michael Kramer's writing (Mott Capital Management, published via
Investing.com) that Keith pasted in directly on 2026-09-03 — his actual differentiator over the old format is that
he wants Kramer's analytical depth and narrative flow, applied to a site whose whole premise is real personal
positions rather than pure commentary. This sample deliberately keeps that personal tie-in explicit ("this is a
name I actually hold") since that's the connection Kramer's own writing structurally can't make.

**Reality check on the daily commitment (still true, arguably more true now):** a genuinely daily brief in this
denser style is a real ongoing production commitment — every trading day, indefinitely, and now with more
analytical work per entry than the old bullet format required. Worth deciding up front whether this is truly daily,
or whether "most trading days" with an honest occasional skip is the more sustainable version before the format
becomes a source of guilt instead of a habit.


## Daily page presentation (2026-09-26 review)

Publish the newest card first on each page with `daily-entry daily-entry-latest`; older cards use `daily-entry` and remain beneath the Jump To archive. Add the newest archive link at the start of the list and move the former latest card under it. Keep the existing `/market-tape/` path so older links work.

Use short, useful headings and occasional relevant emoji, never decoration in every paragraph. A verified market symbol may be written as `$NVDA` (or `$SPY`) in a new entry; the site links recognized symbols to their Yahoo Finance quote pages. Check symbol spelling and the actual security before publication. An unrecognized symbol remains plain text, never silently corrected to another instrument. Dollar prices such as `$50` are not symbols. Link story references directly to the original report or primary source you checked, with meaningful link text; don't invent a source link or turn a vague claim into a citation. Existing prose is historical and should not be rewritten merely to insert new links.
