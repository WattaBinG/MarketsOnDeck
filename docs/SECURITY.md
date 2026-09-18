# Security Review — Repo, Site, and Automation

Written 2026-09-18 in response to Keith's question: can cloud automation use
an API or MCP connector safely, and is there anything in the repo someone
could use to steal his data?

## Short answer

- **Yes, cloud automation can safely use an API or remotely hosted MCP** —
  if credentials live only in encrypted server-side secrets (GitHub Actions
  secrets or Cloudflare Worker secrets), the token is least-privilege and
  read-only for market data, and the public site only ever receives the
  final JSON data files. The brokerage *login* (password, MFA, full-access
  session) must never be used by automation at all.
- **No passwords, API keys, or brokerage session tokens are in the repo or
  on the deployed site.** Full-history scan of every branch (317 commits),
  the workflows, and the live site assets on 2026-09-18 found none.
- **Two real exposures did turn up** — both private *identifiers*, not
  passwords, and both fixable. See below.

## What the audit covered

- All 317 commits across every branch (main, all PR branches, both
  recovery branches) scanned for key/token/password/private-key patterns
  and brokerage/cloud credential keywords.
- All GitHub Actions workflows and `wrangler` config: no hardcoded
  secrets; the parked Webull worker (PR #19) reads its app key from
  Cloudflare secrets (`requireSecret`), never from code.
- Deployed site assets on the live URL.
- Data files (`trades.json`, `positions.json`): public trade/position data
  the site intentionally publishes — symbols, prices, P&L. No account
  numbers, sizes beyond what Keith publishes, or identifiers.

## Findings

1. **Robinhood account numbers in the public repo** (`CLAUDE.md`,
   `AGENTS.md` on `main`, plus all history). These are identifiers, not
   credentials — nobody can log in with them — but they make targeted
   phishing easier ("hi, this is your broker about account ...").
   **Fix:** scrubbed in the review-only PR `security/scrub-account-ids`
   (numbers replaced by the account nicknames). Note: scrubbing current
   files does not erase git history; a full history purge
   (`git filter-repo` + force push) is possible but destructive and is
   Keith's call — not done here.
2. **The Tape invite code (`TAPE-FOUNDER`) is in the public repo**, which
   defeats invite-only. Same scrub PR removes it; rotate the code if the
   invite gate matters.
3. **Supabase publishable key in `site/assets/tape.js`** — this one is OK
   by design. It is Supabase's browser-tier key, and the migration SQL
   enables Row Level Security on every table (public read, users write
   only their own rows, no update/delete except the service role). Keep
   it that way: the service-role key must never be shipped to the browser
   or committed. Verified RLS policies exist in
   `data/migration_001_predictions_core.sql`.
4. **Alpaca API key stored in a Google Drive note** (found earlier today,
   not in the repo). Keith clarified it is a *paper-trading* key meant for
   price data and a future algo-testing project. Paper keys can't touch
   real money, but it still identifies the account; the tidy home for it
   is the Instinct vault or GitHub Actions secrets, not a Drive doc. Left
   as-is per Keith.
5. **No GitHub Actions secrets are used by the automation in PR #21 at
   all** — the wire, crypto, and calendar workflows use only public,
   keyless sources, so there is nothing to leak.

## Safe pattern for API/MCP-powered automation (when a licensed feed exists)

- Credentials live only in **GitHub Actions secrets** (or Cloudflare
  Worker secrets for the PR #19 design). They are encrypted, write-only
  in the UI, and masked in logs.
- **Least privilege:** a market-data-only, read-only token. Never a
  brokerage login, never a token with account, positions, orders, or
  trading scope. For the Webull design (PR #19) that means the OpenAPI
  market-data subscription only — no account endpoints.
- **The site gets files, not access.** Automation commits plain JSON
  (like `ticker.json` today). The public site never calls the brokerage
  or data provider directly, so a visitor cannot ride the site's
  credentials.
- **No secrets in the repo, ever** — not in code, docs, commit messages,
  or issue text. This doc and `AUTOMATION.md` describe sources by name
  only.
- Alpaca's paper API is the right sandbox for testing future automation;
  paper and live keys must never be mixed, and live-trading scope stays
  out of this repo's jobs regardless.

## Standing rules going forward

- Anyone (human or AI) editing this repo: no account numbers, invite
  codes, tokens, or keys in any file. Refer to accounts by nickname
  ("Trading", "Agentic").
- New data source → check its license *and* where its credential will
  live before writing code.
- `trades.json` / `positions.json` stay exactly as public as they are
  today by Keith's choice — that's the product — but they never gain
  account identifiers.
