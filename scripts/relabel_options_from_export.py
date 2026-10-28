#!/usr/bin/env python3
"""One-time, label-only backfill: type ledger rows from a broker activity export.

Authority is the broker export (Robinhood activity CSV), never a row's own label or price.
A (date, symbol) is an OPTION close only if every close in the export for that symbol and day is an
option contract (description has "MM/DD/YYYY Call|Put $strike"). Stock-only days stay equity. Mixed or
missing days are left untouched and reported. realizedGain, quantity, dates and totals are never edited.
Existing permanent anchors are preserved by writing the old registry anchor into row['id'].

usage: relabel_options_from_export.py <export.csv> [--write]
The export is private: do not commit it.
"""
import csv, json, re, sys, collections, datetime, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
OPT = re.compile(r'^(?P<u>[A-Z.]+) (?P<m>\d+)/(?P<d>\d+)/(?P<y>\d{4}) (?P<t>Call|Put) \$(?P<k>[\d,.]+)$')
CLOSE_CODES = ('STC', 'BTC', 'OEXP', 'Sell', 'OASGN', 'OEXCS')

def money(s):
    s = (s or '').strip()
    return float(re.sub(r'[^0-9.]', '', s)) if s else 0.0

def export_closes(path):
    """{(iso_date, symbol): [{'kind','contract'|None,'qty'}]} for close-type rows."""
    out = collections.defaultdict(list)
    for r in csv.DictReader(open(path)):
        code = r['Trans Code']
        if code not in CLOSE_CODES:
            continue
        m, d, y = r['Activity Date'].split('/')
        day = '%s-%02d-%02d' % (y, int(m), int(d))
        desc = r['Description'].replace('Option Expiration for ', '').strip()
        o = OPT.match(desc)
        if o:
            c = {'underlying': o['u'], 'strike': float(o['k'].replace(',', '')),
                 'expiration': '%s-%02d-%02d' % (o['y'], int(o['m']), int(o['d'])),
                 'optionType': o['t'].lower(), 'multiplier': 100}
            out[(day, o['u'])].append({'kind': 'option', 'contract': c})
        elif r['Instrument']:
            out[(day, r['Instrument'])].append({'kind': 'equity', 'contract': None})
    return out

def classify(row, closes):
    """-> ('option', contract_dict|None) | ('equity', None) | ('unresolved', None)"""
    cl = closes.get((row['date'], row['symbol']), [])
    kinds = {c['kind'] for c in cl}
    if kinds == {'option'}:
        cs = {json.dumps(c['contract'], sort_keys=True) for c in cl}
        return 'option', (json.loads(next(iter(cs))) if len(cs) == 1 else None)
    if kinds == {'equity'}:
        return 'equity', None
    return 'unresolved', None

def anchor_keys(trades):
    seen = {}
    for t in trades:
        q = t.get('quantity', '')
        if isinstance(q, (int, float)) and float(q).is_integer():
            q = str(int(q))
        base = '|'.join([str(t.get('timestamp', '')), str(t.get('account', '')), str(t.get('symbol', '')), str(t.get('assetType', '')), str(q)])
        n = seen.get(base, 0); seen[base] = n + 1
        yield t, base + '|' + str(n)

def main(argv):
    export, write = argv[1], '--write' in argv
    path = ROOT / 'site/assets/trades.json'
    data = json.loads(path.read_text())
    reg = json.loads((ROOT / 'site/assets/trade-anchors.json').read_text())
    closes = export_closes(export)
    report = collections.Counter(); unresolved = []
    for t, k in anchor_keys(data['trades']):
        if t.get('account') != 'Trading' or t.get('assetType') not in ('equity', 'option') or t.get('schemaVersion') == 2:
            continue
        if t['date'] > '2026-10-19' or t['symbol'] == 'SOXL':   # SOXL Aug 7 rows are spread legs: left as is
            continue
        kind, contract = classify(t, closes)
        if kind == 'unresolved':
            report['unresolved'] += 1; unresolved.append((t['date'], t['symbol'], t['assetType'], t['quantity'], t['realizedGain'])); continue
        if kind == 'equity':
            report['equity-confirmed' if t['assetType'] == 'equity' else 'OPTION-ROW-BUT-EXPORT-STOCK'] += 1; continue
        if t['assetType'] == 'equity':
            if not t.get('id') and k in reg:
                t['id'] = reg[k]          # keep the permanent Record link
            t['assetType'] = 'option'; t['price'] = None
            report['relabeled-equity-to-option'] += 1
        else:
            report['option-already'] += 1
        if contract and 'strike' not in t:
            t.update(contract); report['contract-detail-added'] += 1
        elif not contract:
            t.setdefault('contractNote', 'Several contracts closed this day under one row; not split'); report['multi-contract-no-detail'] += 1
    print(dict(report))
    for u in unresolved: print('UNRESOLVED', u)
    if write:
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n')

if __name__ == '__main__':
    main(sys.argv)
