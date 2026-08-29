# Video Series Frameworks — Sourced from Gemini Spark & Codex, Synthesized

Both were given the same brief: turn real trade history since July 11, 2026 into a documented video series, no fabricated numbers, no "you can do this too" framing, no personalized advice.

## Verdict: Codex's editorial framework + Spark's production spec

Both independently converged on the same shape (monthly long-form anchor + recurring shorts + eventual flagship documentary) — that convergence is a good signal it's the right structure. Where they differ, Codex's analytical discipline wins; Spark's visual/production language is more concrete and worth keeping.

**Take from Codex:**
- The **decision ledger** — group trades by behavior, not just win/loss: *followed the plan / exited early / oversized / chased momentum / thesis invalidated / profitable despite poor execution / lost despite acceptable execution.* This is the actual credibility mechanism — it separates outcome from process quality.
- **Hindsight-bias discipline** — reconstruct only what was known at entry; never show the completed chart before walking through the decision.
- **Deposits/withdrawals shown separately from realized trading results** — never let an equity curve imply a deposit was a trading gain.
- **Correction cards** — when a past figure needs revision, show the correction, don't silently edit it. Matches the "immutable log, separate resolution table" principle already in `CLAUDE.md`.
- **Titles** — sharper because they're built on a specific tension (one screenshot vs. the full record), not just "look how much data exists."

**Take from Spark:**
- **Tier structure naming** (monthly anchor / micro trade-autopsy shorts / flagship documentary) — clean, easy to reference internally.
- **Trade card field spec** — Setup Category, Planned Risk vs. Realized Return ($ and R-multiple), Hold Duration, Execution Grade.
- **Equity curve as episode spine** with a moving cursor tracking timestamps — concrete production idea, not just "show a chart."
- **Split-screen "what social media would show vs. what the complete record shows"** — a strong, repeatable signature visual.

## Recommended Starting Point (Not the Full Vision on Day One)

Both frameworks describe a mature, multi-month production system. Building all of it before publishing anything is a real risk — start with:
1. **Shorts first** (Tier 2/supporting format) — raw fill + chart, minimal motion graphics, prove the format gets watched.
2. **One monthly chapter**, simple version — decision ledger + full scorecard, basic equity curve, no candle-replay animation yet.
3. Only invest in the heavier production (masked chart replay, animated equity spine, GitHub-style heatmaps) once the simple version is validated.

## Standing Disclaimer (Codex's version, cleanest of the two)

> This series documents my own trades and decision-making after the fact. It is not a recommendation, trade alert, or representation of typical results.

Use this verbatim or close to it on every episode, matching the FTC disclosure + investment-advice disclaimer rule already in `CLAUDE.md` §3.
