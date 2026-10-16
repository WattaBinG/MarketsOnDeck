# Robinhood ticker leg - replication spec (Claude-free target)

Source: Keith pasted the live "Ticker Refresh - Market Close" routine prompt
on 2026-10-16 as the spec to replicate without Claude. The Intraday variant
is the same shape with its own asOfLabel; confirm against its prompt when
Keith pastes it.

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
