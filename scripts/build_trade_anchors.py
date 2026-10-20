#!/usr/bin/env python3
"""Append-only registry of permanent per-trade anchors for The Record.

Link format: https://marketsondeck.net/record/#t-<anchor>
- Trades that already have a ledger id use it as the anchor.
- Other trades get <date>-<SYMBOL>-<n> once, stored in site/assets/trade-anchors.json keyed by
  timestamp|account|symbol|assetType|quantity|dupIndex. An assigned anchor is NEVER changed or reused.
- Also writes site/record/trade-links.csv (lookup list).
"""
import json, csv, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
TR = ROOT / 'site/assets/trades.json'
REG = ROOT / 'site/assets/trade-anchors.json'

def keys(trades):
    seen = {}
    for t in trades:
        q = t.get('quantity', '')
        if isinstance(q, (int, float)) and float(q).is_integer(): q = str(int(q))
        base = '|'.join([str(t.get('timestamp', '')), str(t.get('account', '')), str(t.get('symbol', '')), str(t.get('assetType', '')), str(q)])
        n = seen.get(base, 0); seen[base] = n + 1
        yield t, base + '|' + str(n)

def main():
    trades = json.loads(TR.read_text())['trades']
    reg = json.loads(REG.read_text()) if REG.exists() else {}
    used = set(reg.values()) | {t['id'] for t in trades if t.get('id')}
    for t, k in keys(trades):
        if t.get('id') or k in reg:
            continue
        n = 1
        while True:
            a = '%s-%s-%d' % (t['date'], t['symbol'].replace(' ', '').upper(), n)
            if a not in used: break
            n += 1
        reg[k] = a; used.add(a)
    REG.write_text(json.dumps(reg, indent=1, sort_keys=True) + '\n')
    with open(ROOT / 'site/record/trade-links.csv', 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(['date', 'account', 'asset', 'symbol', 'quantity', 'realized_gain', 'link'])
        for t, k in keys(trades):
            a = t.get('id') or reg[k]
            w.writerow([t['date'], t['account'], t['assetType'], t['symbol'], t.get('quantity'), t['realizedGain'], 'https://marketsondeck.net/record/#t-' + a])
    print('anchors:', len(trades), 'registry:', len(reg))
main()
