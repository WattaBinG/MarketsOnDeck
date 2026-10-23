#!/usr/bin/env python3
"""PR guard for trades.json: existing rows may not be removed or silently re-typed.

usage: check_ledger_immutability.py <base-trades.json> <head-trades.json> [--allow-relabel]

For every row in base, the same row must exist in head with the same date, account, symbol,
quantity and realizedGain. assetType may only change with --allow-relabel (a label-only PR).
New rows are allowed. Rows are matched by id, else by timestamp|account|symbol|quantity|n-th duplicate.
This needs no broker export, so it can run in CI. It does not prove a label is right (that needs the
broker export: scripts/check_asset_types.py); it stops a refresh from rewriting history unnoticed.
"""
import json, sys, pathlib

def keyed(trades):
    seen = {}
    out = {}
    for t in trades:
        if t.get('id'):
            out[('id', t['id'])] = t
            continue
        base = (t.get('timestamp'), t.get('account'), t.get('symbol'), t.get('quantity'))
        n = seen.get(base, 0); seen[base] = n + 1
        out[('k',) + base + (n,)] = t
    return out

def compare(base, head, allow_relabel=False):
    b, h = keyed(base), keyed(head)
    # rows that gained an id in head: match them back by the legacy key via 'legacyKey' fallback
    h_by_legacy = {}
    seen = {}
    for t in head:
        k = (t.get('timestamp'), t.get('account'), t.get('symbol'), t.get('quantity'))
        n = seen.get(k, 0); seen[k] = n + 1
        h_by_legacy[('k',) + k + (n,)] = t
    problems = []
    for key, t in b.items():
        u = h.get(key) or h_by_legacy.get(key)
        if u is None and key[0] == 'id':
            problems.append(('removed', key[1]))
            continue
        if u is None:
            problems.append(('removed', key))
            continue
        for f in ('date', 'account', 'symbol', 'quantity', 'realizedGain'):
            if t.get(f) != u.get(f):
                problems.append(('changed ' + f, key, t.get(f), u.get(f)))
        if t.get('assetType') != u.get('assetType') and not allow_relabel:
            problems.append(('retyped', key, t.get('assetType'), u.get('assetType')))
    return problems

def main(argv):
    allow = '--allow-relabel' in argv
    args = [a for a in argv[1:] if not a.startswith('--')]
    base = json.loads(pathlib.Path(args[0]).read_text())['trades']
    head = json.loads(pathlib.Path(args[1]).read_text())['trades']
    problems = compare(base, head, allow)
    for p in problems[:25]: print('FAIL', *p)
    print('existing rows checked=%d problems=%d%s' % (len(base), len(problems), ' (relabel allowed)' if allow else ''))
    return 1 if problems else 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
