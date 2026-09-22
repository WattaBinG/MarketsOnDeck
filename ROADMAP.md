# MarketsOnDeck Roadmap / Backlog

Living list of what Keith wants next, written 2026-09-22 so any AI tool
(Claude, Insight, whoever) can pick up a piece without a live conversation
with Keith first. Read `AGENTS.md`, `AUTOMATION.md`, and `docs/SECURITY.md`
before touching anything here — the account-nickname rule and the
no-secrets-in-git rule apply to every item below without exception.

Keith is intermittently out of Claude credits, so items here are meant to be
independently pickable — each has enough context to start cold.

## 1. Discord local reader — currently blocked, needs a clean test

`docs/DISCORD-LOCAL-READER.md` assumes Keith's PC gives a residential IP
Discord won't block. Tested 2026-09-22 from a Claude Code session running
"locally" on Keith's machine — still got the same HTTP 403 "internal network
error" (code 40333) that GitHub Actions gets. Two possibilities:
- Claude Code's shell layer routes through non-residential infrastructure
  even when it looks local (files are local, network egress might not be).
- Discord's block is broader than "just datacenter IPs."

**Next step:** Keith runs `python scripts\discord_local_reader.py` from a
plain Command Prompt/PowerShell window he opens himself (Start menu, not
through any AI tool). If that also 403s, the local-reader design itself
needs rethinking (maybe a phone/browser-based fetch instead, or accepting
Discord as a source is currently not viable and dropping it from the Wire's
source list until Discord's policy changes). If it works, wire it into
Windows Task Scheduler (the doc already has the steps) so it runs on its own
without Keith or any AI needing to trigger it — matches Keith's general ask
that things "run on their own" rather than needing a session to kick them.

The bot token is already in `scripts/discord_token.local.txt` (gitignored)
as of 2026-09-22 — no need to ask Keith for it again unless it's rotated.

## 2. What to Watch Today — make it intraday, not just a morning snapshot

Current state: `refresh-watch-today.yml` runs once, Sun-Thu evenings
(9:30pm UTC), and writes tomorrow's event list. Fixed 2026-09-22 (was stuck
on Friday Sept 18 data from a Cloudflare-deploy bug, itself fixed in PR #25;
the *scheduled* run since that fix hasn't fired yet as of this writing —
check it actually ran clean tonight before trusting the cron alone).

**What Keith wants, not yet built:** the list should update through the
trading day as each scheduled event's time passes — e.g. once 8:30am ET
passes, that line gets a strikethrough (or similar "this already happened"
treatment) and, where the actual result is available (a number that gets
published, like a CPI print or jobless claims figure), show it right next
to the line. Goal: give people a reason to check back on the site multiple
times a day, not just once each morning.

Rough shape of what this needs:
- A more frequent cadence than once nightly — hourly during market hours
  would let the strikethrough/result update feel live without over-building.
- A results source per event type. Not all of `scripts/refresh_watch_today.py`'s
  event types have a machine-readable public result feed (BEA/BLS/Census
  calendars give the *schedule*, not always the *print* immediately after).
  Scope this realistically: start with whichever event types actually have
  a fetchable public result (e.g. FRED's series for CPI/jobless claims/NFP
  often post same-day), and leave events without a reliable result source
  showing only the strikethrough (happened, no auto-fetched number) rather
  than guessing or leaving a placeholder.
- Keep the "fail closed, never publish invented data" rule from
  `AUTOMATION.md` — a missing result should show nothing, never a fabricated
  number.

## 3. Morning Brief & Market Tape — deepen portfolio + news coverage

The *content requirements* are already fully specified in
`content/morning-brief-template-and-sample.md` (both benchmarks-plus-crypto
coverage and both-accounts coverage are already mandatory rules there,
added 2026-09-14). What Keith is asking for now is enforcement/depth, not a
new spec:
- Every Brief and every Tape entry should actually walk both accounts'
  real positions (equities, options, crypto) and pull genuine ticker-level
  news for anything held — not just the broad-market story of the day.
- The Market Tape (after-close piece) in particular should function as the
  end-of-day portfolio recap: what moved in the accounts today, tied to
  real news where a real cause exists, written in the narrative-thread style
  already documented — never inventing a reason for a move that doesn't
  have one.
- This still requires a human or Claude session with live brokerage access
  (MCP) — per `AUTOMATION.md`, this is explicitly NOT something the
  keyless GitHub Actions automation can do, since it needs real account
  data. When Claude credits are available, this is `trig_017Ph8RYYJqrhMYgHUDCG53W`'s job.

## 4. Morning Brief & Market Tape — visual redesign

Keith's words: "right now its like just basic text... really bland." Wants:
- Bigger, more readable type for the entry body (current styling reads like
  a plain paragraph block).
- Tasteful emoji use as visual anchors (e.g. a ticker-move arrow, a
  sentiment cue) — sparingly, this is still a financial-content site, not
  meant to look unserious.
- Inline links styled distinctly (not just default blue-underline) so a
  reader can visually scan "where can I click."
- Some kind of visual "pop" per entry — a pull-quote treatment for the "why
  this matters" closer, a stat callout for the day's key number, etc.
This is a CSS/template pass on `site/brief/index.html` and
`site/market-tape/index.html` (and their shared card styles in
`site/assets/style.css`) — no new data plumbing needed, purely presentation.
Check the existing brand fonts/colors already established (Oswald + IBM
Plex, per every page's `<head>`) and stay inside that system rather than
introducing new fonts.

## 5. Substack — auto-publish + rebrand

Two distinct pieces:
- **Auto-publish the Brief/Tape to Keith's Substack.** Important
  constraint to know before promising anything: **Substack does not have a
  public write API.** The realistic paths are (a) Substack's email-to-post
  feature if it still exists on his plan (publishing by sending a
  formatted email to a special address), or (b) browser automation logging
  in as Keith to use the compose UI, which is slower/fragile and needs
  Keith's actual login (never store that credential in this repo — browser
  automation would need to run interactively with Keith present, or through
  a tool with its own credential vault, never a plaintext password in code
  or GitHub Actions secrets). Research the current state of Substack's
  publish options before building anything — this may have changed.
- **Rebrand the existing Substack.** Keith has an old Substack that
  predates the current MarketsOnDeck branding (logo, colors, fonts — see
  item 6). Needs a pass to bring its About page, logo, and colors in line
  with the site once that branding exists. Low priority until item 6 lands
  since there's nothing to match yet.

## 6. Banner / logo redesign

Current brand assets are in `site/assets/brand/` (icon-32/128/180,
badge-1200 used for social previews). Keith wants a better banner/logo —
no specific direction given yet beyond "we need a better banner or
something too." Before generating anything, get a one-line steer from
Keith on style direction (the existing icon is worth looking at first to
see what to keep vs. replace) rather than guessing blind.

## 7. Housekeeping

- 12 stale PRs (#1, #2, #4–#9, #17–#20, #22) are old Morning Brief/Market
  Tape drafts and superseded design/security passes from Sept 4–18. Keith
  wants them closed. No GitHub API token is available in the Claude Code
  session as of 2026-09-22 (closing was attempted, blocked by Claude Code's
  own safety layer when it tried to pull a stored git credential without
  Keith's explicit say-so) — Keith can close them himself in the GitHub UI,
  or hand a scoped PAT to whichever AI tool is doing this work.

## Security note for every item above

Every new integration in this list (Substack, any future browser-automation
login, any new data source) must follow the same rule already proven out
for Discord, the brokerage MCP, and Cloudflare: **credentials never enter
git** — local gitignored files or platform-native secret stores only, never
hardcoded, never pasted into a committed doc, never logged. See
`docs/SECURITY.md` before adding any credential anywhere in this project.
