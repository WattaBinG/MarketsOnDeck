#!/usr/bin/env python3
"""Broker-backed asset-type check for trades.json. Exit 1 on any mismatch.

usage: check_asset_types.py <broker-activity-export.csv> [trades.json]
Authority is the broker export: a ledger row typed 'equity' on a (date, symbol) where the export shows
ONLY option-contract closes fails; a row typed 'option' where the export shows ONLY stock closes fails.
Days with both are checked per row by the caller's evidence, not guessed here (reported, not failed).
The price heuristic (per-contract premium stored as a share price) is advisory only and never decides a type.
"""
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from relabel_options_from_export import export_closes, classify

def check(trades, closes, account='Trading'):
    fails, mixed, advisory = [], [], []
    for t in trades:
        if t.get('account') != account or t.get('assetType') not in ('equity', 'option'):
            continue
        if t.get('schemaVersion') == 2 and t.get('assetType') == 'option':
            pass
        kind, _ = classify(t, closes)
        if kind == 'option' and t['assetType'] == 'equity':
            fails.append(('option close typed equity', t['date'], t['symbol'], t.get('quantity'), t.get('realizedGain')))
        elif kind == 'equity' and t['assetType'] == 'option':
            fails.append(('stock close typed option', t['date'], t['symbol'], t.get('quantity'), t.get('realizedGain')))
        elif kind == 'unresolved':
            mixed.append((t['date'], t['symbol'], t['assetType']))
        if t['assetType'] == 'equity' and isinstance(t.get('price'), (int, float)) and t.get('price') and t['price'] == int(t['price']) and t['price'] % 5 == 0 and t['price'] >= 50:
            advisory.append((t['date'], t['symbol'], t['price']))
    return fails, mixed, advisory

def main(argv):
    closes = export_closes(argv[1])
    data = json.loads(pathlib.Path(argv[2] if len(argv) > 2 else pathlib.Path(__file__).resolve().parent.parent / 'site/assets/trades.json').read_text())
    fails, mixed, advisory = check(data['trades'], closes)
    for f in fails: print('FAIL', *f)
    print('fails=%d mixed-days-unchecked=%d advisory-flags=%d' % (len(fails), len(mixed), len(advisory)))
    return 1 if fails else 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
