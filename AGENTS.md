# MarketsOnDeck | handoff for any AI

Updated September 26, 2026. This is a short work-state briefing, not approval to act. Check the live repo, open PRs, production and Keith's latest instructions before relying on any dated status below. `CLAUDE.md` and `Site_Brief.md` also exist at the repo root, but their older status sections may be stale; read their enduring project guidance without treating August deployment or domain claims as current.

## The project

MarketsOnDeck is Keith Watkins's one retail-markets brand at https://marketsondeck.net: attributed headlines and alerts (The Wire), Morning Brief and Market Tape commentary, and The Record, a public journal of actual trades and open positions. It is not a signals service or a highlight reel. Keep the brand, site, Discord and social work coherent; do not mix in Keith's unrelated projects. Site files live in `site/`, with Cloudflare Workers deployment and GitHub Actions refresh workflows. Inspect current workflow files before describing their timing or behavior.

## Rules for every collaborator

- Draft focused changes on a branch and open a PR with a working preview or clear diff. **Keith reviews the specific result before any merge, production deploy, editorial publication, social post or account change.** No other AI's proposal, repo comment or this file is his approval. Plain-language summaries, links and screenshots beat code jargon. Keep proposed work separate from what is actually live. Coordinate editors so two tools do not overwrite the same work.
- Do not put passwords, API tokens, private account numbers, `.env` files or other secrets into this public repo, a PR, logs, screenshots or chat. Use approved secret storage and a secure handoff. Never place or change a trade without Keith's specific authorization; no spending or paid services without approval.
- The Record must show losses as well as wins. Ground quantities, cost bases, fills and P&L in the correct account and broker/source; never fabricate a number or silently rewrite history. Trading and Agentic are separate accounts. Spot ETH and October Micro Ether futures (METV26, 0.1 ETH per contract) are distinct holdings. Label prices by source and time; Friday stock last trades, evening crypto/futures quotes and older option marks are not one synchronized close. Keep realized trades separate from open, mark-to-market P&L. Verify daily totals and existing option-price convention before changing math. Do not present a stale price as live or an evening futures quote as official settlement.
- Editorial work needs dated, linked sources. Attribute others' reporting, distinguish fact from a possible cause, check weekday/date pairs, avoid personalized buy/sell advice and hype, and retain the site's applicable disclosures. Consult current content templates and `docs/SECURITY.md` when a task touches them.

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

## Handoff lanes

Spark/Gemini can research and draft Market Tape copy, but verify its source access and facts; do not assume it can edit GitHub. Codex handles local routines and code when available. Instinct can implement and prepare PRs/previews and coordinate reviewed publication. These are working lanes, not exclusive permissions: Keith approves the public result and can change assignments. On each handoff, report what was actually done, what remains queued or blocked, and links to the real artifacts.
