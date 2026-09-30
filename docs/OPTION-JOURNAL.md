# Option journal contract, version 2

Review patch, not a production instruction. Do not merge without Keith's review.

## Data rules

- Never include account numbers or masked account endings in any public post, page, commit, PR, patch, screenshot or other public surface. Reference accounts only as "Trading" and "Agentic". Remove identifier text before preparing public artifacts; masking is not permission to publish an account ending.

- Equities use shares and dollars/share. Do not classify by ticker or the shape of a price. Ask the brokerage instrument metadata for the asset type.
- Explicit closed options retain `symbol` for ticker search and add `underlying`, `strike`, ISO `expiration`, `optionType` (call/put), `contractId`, `multiplier`, `positionSide`, `contracts`, `action`, and a stable close `id`.
- `quantity` remains a compatibility alias for contract count on options. It is not shares. Contract count is not the multiplier.
- Closed-option `entryPremium` and `exitPremium` are dollars per underlying share (`priceUnit: USD_per_share`). `entryPerContract`/`exitPerContract` are those premiums times the explicit multiplier. Ambiguous legacy `price` is null. Never apply the multiplier twice.
- `optionOpenFills` is opening-fill evidence, not extra realized trades. Each fill records `buy_to_open` or `sell_to_open`, contract count, premium, fill time/precision, and fees. Closed rows reference these fills. Partial closes do not duplicate the original opening fill.
- Retain the brokerage's reported `realizedGain` as authoritative. Regulatory fees stay separate; do not silently replace reported P&L with a net arithmetic result. A lot allocation reconciled from gains is labeled as such, not a brokerage lot report.
- Do not assume all contracts have a 100 multiplier. Verify adjusted contracts and short positions separately. The META standard contract multiplier is consistent with the screenshot's cost/credit figures.
- Open positions retain their existing `avgCost`, `currentPrice`, and `priorClose` in USD per contract, now labeled `priceUnit: USD_per_contract`. Display the share premium by dividing once. Preserve cost precision, mark timestamps, unrealized P&L and account labels.
- Legacy options missing contract identity display an explicit missing-details label and unavailable prices. Do not invent historical strikes/expiries. Other older rows marked equity require a separate instrument audit; this repair does not prove that history is all shares.
- The Record renders contract identity and quantity from the shared formatter. The Sep 28 Tape's new verified-fill card reads the same rows; existing editorial paragraphs are not rewritten by JSON refreshes.

## Sep 28 META reconciliation

Owner-provided filled-order screenshots establish META $742.50 put, October 2, four contracts, Trading account. Dates are from the current September 2026 trade context; screenshots abbreviate expiry as 10/2.

Opening fills: September 23, 9:38 AM ET, 1 at $19.80; September 23, noon ET, 1 at $18.40; September 24, 3:59 PM ET, 2 at $8.25. Opening screenshots have minute precision, not seconds.

Closing fills: September 28, 2 at $19.50 ($80 reported profit), 1 at $20.60 ($1,235), 1 at $22.80 ($1,455). Existing close timestamps are retained. The two September 23 fills reconcile to $19.10 average premium; the September 24 fill reconciles to the two later single-contract closes. This is reconciliation, not a new claim of broker-provided tax-lot selection.

Premium cost $5,470; premium proceeds $8,240; displayed profit $2,770. Opening fees total $0.16 and closing fees total $0.16. Net cash difference would be $2,769.68; it does not replace the broker's displayed profit.

No raw brokerage screenshots, account numbers or private source links belong in this public repository.

## Writer handoff and tests

Every external Record writer must preserve this schema and verified close anchors, validate broker asset metadata, and run:

```
python3 scripts/validate_journal.py
python3 -m unittest discover -s tests -p 'test_journal*.py'
node tests/test_journal_format.cjs
```

The new GitHub check detects a flattened META refresh. It is not deployment gating unless the owner configures a required check/branch protection. The external brokerage routine is outside this repo; its instruction must be updated separately. This patch cannot control it.

## Sep 30 reconciliation: both accounts, new buys, futures

- **Both-account sourcing.** The journal covers Trading and Agentic. Every fill from both accounts appears as a trade row, including new option buys (buy_to_open), not just closes. The Sep 30 HD (9 contracts, 3 lots) and TSLA (4 contracts, 2 lots) buys are booked alongside the SPCX and CCL closes.
- **Native asset types.** Futures rows carry native quoted prices (`quotedAvgCost`, `quotedMark`), `multiplier`, `quantityUnit: "contracts"`, and expiration. The per-contract dollar fields (`avgCost`, `currentPrice`) remain for totals math. Display layers show the quoted values.
- **Underlyings-only ticker strip.** The public ticker strip shows underlying symbols (HD, TSLA, SPY) — never option contract IDs or futures codes.
- **Internal accounting vs public display.** `positions.json` retains every nonzero position including dust (DOGE, USDC). Public table rendering hides rows under $5; stats, totals, and unrealized P&L use all rows. A footer notes hidden positions remain counted.
- **USDG is cash-like.** Book the exact unit quantity. No trade rows, no P&L tracking.

## Writer regression rules

- A writer that flattens option closes to equity-shaped rows, drops new buy fills, or deletes dust positions is regressing. The validator (`scripts/validate_journal.py`) checks: contract identity on option rows, fill references resolve, futures carry quoted prices, and no nonzero position is missing.
