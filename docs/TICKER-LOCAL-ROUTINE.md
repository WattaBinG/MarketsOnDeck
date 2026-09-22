# Ticker local routine

The ticker strip refreshes from a routine Keith runs on his own machine
(Claude Desktop, Codex, or any AI client with this repo checked out and a
connected brokerage MCP). The cloud never prices anything: it reshapes
site/assets/ticker.json hourly (scripts/build_ticker.py), but every price
and the as-of label come from a local run. AUTOMATION.md owns the data
rights; this file owns the how.

## What one run does

1. Pull current quotes from the connected brokerage (Robinhood or Webull
   via MCP) for every symbol going into the strip.
2. Re-pick the movers every single run. The movers layer is today's
   market action: biggest gainers/losers, unusual volume, names being
   talked about. Never carry yesterday's pick forward - that is how LULU
   sat on the strip for two weeks.
3. Assemble the strip in three layers and dedupe across them:
   - Layer 1, pinned staples: SPY, QQQ, DIA, IWM, USO (oil rides USO).
     BTC, ETH, SOL are pinned from crypto.json by the site - never put
     them in ticker.json.
   - Layer 2, portfolio: symbols from site/assets/positions.json,
     equities plus option underlyings plus crypto, flagged held: true.
     Keith's own data, not licensed market data.
   - Layer 3, movers: the fresh pick from step 2.
   - No symbol appears twice anywhere (ETH shows once even though Keith
     holds it - it lives in the crypto pin). Total strip: 15 symbols max,
     trimmed from the movers end.
4. Write site/assets/ticker.json with fresh price / change /
   changePercent per symbol and update asOf + asOfLabel to the time the
   quotes were pulled. Prices are a snapshot - the label is the honesty.
5. Commit ticker.json only and push to main. Nothing else changes.

If a portfolio symbol has no clean quote, write its price as null; the
site shows "--" and the as-of label stays truthful.

## Paste-ready prompt (any AI client with the repo + brokerage MCP)

Run the MarketsOnDeck ticker refresh per docs/TICKER-LOCAL-ROUTINE.md in
this repo: pull current quotes from my connected brokerage (Robinhood or
Webull via MCP), re-pick today's movers (biggest gainers, losers, and
unusual-volume names - never reuse yesterday's list, and exclude the
pinned staples SPY, QQQ, DIA, IWM, USO, BTC, ETH, SOL and every symbol in
site/assets/positions.json), rebuild site/assets/ticker.json as pinned
first, then my positions flagged held:true, then the movers, 15 symbols
max with no duplicates, refresh the asOf/asOfLabel to now, then commit
ticker.json only and push to main. Tickers only - no write-ups, no other
files.

## Scheduling notes

- Claude Desktop: create a scheduled routine with the paste-ready prompt
  every 15-30 minutes during market hours (9:30 AM - 4 PM ET weekdays).
  This is how the strip ran before; the only change is the prompt text.
- Codex / Claude Code on the PC: point Windows Task Scheduler at a small
  script that invokes the CLI with the paste-ready prompt on the same
  cadence. Working directory must be the local repo checkout so paths
  resolve.
- ChatGPT scheduled tasks: runs in ChatGPT's cloud, so it cannot reach
  the local repo checkout or the brokerage MCP connections, which live
  in a desktop client. Use it only for a reminder ("run your ticker
  routine"), not to run the refresh itself.
- Whichever client runs it needs two things locally: this repo checked
  out, and the brokerage MCP signed in. The cloud hourly job keeps the
  strip's shape correct between runs but never fabricates prices.
