# Robinhood ticker leg - replication spec (Claude-free target)

Source: Keith pasted BOTH live routine prompts on 2026-10-16 as the spec to
replicate without Claude ("Ticker Refresh - Market Close" and "Ticker
Refresh - Intraday"). The two are the same recipe; differences:

- Intraday: fires hourly on weekdays around 9:30 AM-3:30 PM ET (scheduled
  at :30 past the hour). asOfLabel is the real Eastern time, e.g.
  "11:30 AM ET". Commit message: `Refresh ticker: <asOfLabel>`.
- Market Close: asOfLabel "Market Close". Commit message:
  `Refresh ticker: Market Close`.

Same symbol list, same positions step on both accounts, same quote math
and skip rules. Account numbers from his paste are deliberately not
recorded anywhere.

Connection: Robinhood_Trading MCP, READ-ONLY. No trading calls, ever.
Credentials stay in the MCP client config on Keith's machine - never in
this repo, commit messages, Drive previews, or tickets.

1. `get_equity_quotes` for the fixed ordered list:
   SPY QQQ DIA IWM NVDA LULU SPCX QUBT INTC TSLA AAPL MSFT AMZN GOOGL META
   AMD SOFI KLAC SPCH COIN PLTR
2. `get_accounts`, then `get_equity_positions` on both accounts (Trading
   and Agentic) to build the held-symbols set.
3. Per symbol: price = whichever of last_trade_price /
   last_non_reg_trade_price has the LATER timestamp; baseline =
   previous_close; change = price - previous_close;
   changePercent = change / previous_close * 100; both rounded to 2
   decimals. Drop symbols with a missing quote or has_traded false. Add
   `"held": true` only for held symbols (omit the key otherwise).
4. Overwrite `site/assets/ticker.json` ONLY:
   `{asOf: <UTC ISO now>, asOfLabel: "Market Close" (Intraday uses its own
   label), pinned: ["SPY","QQQ","DIA"], items: [{symbol, price, change,
   changePercent, held?}]}`
5. Commit `Refresh ticker: <label>` and push straight to main, touching no
   other file.

Skip the write entirely on a US market holiday, if Robinhood is
unreachable, or if fewer than half the symbols return quotes.

Known consideration (flagged to Keith 2026-10-16): the `held` flag
publishes WHICH symbols he holds (not sizes) - pre-existing behavior he
has run since the strip launched; kept as-is unless he says otherwise.

Interaction with the GitHub Yahoo bot: this leg is PRIMARY. The bot skips
any snapshot fresher than 12 minutes and only resumes if this leg goes
stale (see AUTOMATION.md, Keith's 2026-10-16 decision).

---

# Morning Brief Draft - replication spec (Claude-free target)

Source: Keith sent the live "Morning Brief Draft" routine prompt on
2026-10-16 as spec material, same purpose as the ticker prompts. This
records the RECIPE only. Approval state is NOT taken from the prompt text:
the prompt's self-merge wording is covered by Keith's separately logged
morning-brief auto-publish exception, which stays the governing grant.
Account identifiers are stripped here on purpose - accounts are named
Trading and Agentic, nothing more.

Schedule: weekday mornings around 7:30 AM ET.

Connectors: Robinhood_Trading MCP (READ-ONLY - never place, modify, or
cancel any trade) and Alpha_Vantage_MCP_Server (market data), plus
WebSearch.

Recipe:
1. Read `content/morning-brief-template-and-sample.md` IN FULL every run -
   it changes periodically; follow whatever is currently there, including
   the Full Coverage Requirement: SPY/QQQ/DIA + crypto benchmarks AND both
   the Trading and Agentic accounts, checked every run.
2. Read `site/brief/index.html` fully. New card gets
   `id="brief-YYYY-MM-DD"` with `scroll-margin-top:24px`, plus a new
   5-10 word `<li>` at the TOP of the jump-list (newest first). Never
   remove or reorder existing cards/items.
3. Apply CLAUDE.md section 3 (Monetization & Compliance): process
   language only, never directive ("you should buy", "guaranteed").
4. Sanity: if a card dated today already exists, STOP - no duplicate, no
   PR. Skip entirely on US market holidays.
5. Data sources, in order: `site/assets/ticker.json` for SPY/QQQ/DIA (the
   site's canonical figures - do not re-query and risk a mismatch);
   `site/assets/crypto.json` for BTC/ETH/SOL; Alpha Vantage
   (TOP_GAINERS_LOSERS, MARKET_STATUS, NEWS_SENTIMENT) for
   overnight/premarket movers and news; WebSearch only for genuinely
   important scheduled econ events next week, with a confirmed real date
   or leave it out; Robinhood get_accounts + get_equity_positions on BOTH
   accounts (Trading and Agentic) every run.
6. If a currently-held position in EITHER account is genuinely relevant to
   today's market story, weave it in truthfully; never force an irrelevant
   holding; skip the personal angle when nothing fits.
7. Never invent a number, date, or claim - leave it out instead.
8. Write per the current template. Branch `morning-brief-YYYY-MM-DD`,
   commit (card + jump-list entry together), push, open PR
   "Morning Brief - <date>" with a one-paragraph data-sources note.
9. Merge per the standing logged auto-publish exception for the morning
   brief (PR first for the paper trail); check once for automated
   review-bot comments after merge and fix any real, verifiable issue with
   a follow-up commit on main.
