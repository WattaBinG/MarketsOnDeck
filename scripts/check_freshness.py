#!/usr/bin/env python3
"""Freshness gate: fail loudly when published ledger views lag the ledger feeds.

Deterministic, no network. Three checks:
  1. trades.json asOf == positions.json asOf (feeds must move together).
  2. Every 'Snapshot through DATE' / 'Ledger through DATE' label in static
     pages matches trades.json asOf (build_trust_views.py must have run).
  3. Tripwire: trades.json asOf no older than MAX_AGE_DAYS from today
     (guards a silently dead pipeline; trading gaps are normal, a week is not).

Exit 1 with a report on any failure; exit 0 when fresh.
"""
import json, re, sys
from datetime import date
from pathlib import Path

MAX_AGE_DAYS = 7
LABEL_RE = re.compile(r'(?:Snapshot through|Ledger through)\s*(\d{4}-\d{2}-\d{2})')
STATIC_PAGES = ('site/overview/index.html', 'site/record/index.html')


def feed_asof(root, name):
    data = json.loads((root / name).read_text())
    return data.get('asOf') or data.get('summary', {}).get('asOf')


def page_labels(root):
    labels = []
    for rel in STATIC_PAGES:
        p = root / rel
        if p.exists():
            for m in LABEL_RE.finditer(p.read_text()):
                labels.append((rel, m.group(1)))
    eps = root / 'site/episodes'
    if eps.is_dir():
        for p in sorted(eps.glob('*.html')):
            for m in LABEL_RE.finditer(p.read_text()):
                labels.append((str(p.relative_to(root)), m.group(1)))
    return labels


def check(root):
    root = Path(root)
    failures = []
    trades_asof = feed_asof(root, 'site/assets/trades.json')
    positions_asof = feed_asof(root, 'site/assets/positions.json')
    if not trades_asof:
        failures.append('trades.json has no asOf')
        return failures
    if positions_asof != trades_asof:
        failures.append(f'positions.json asOf {positions_asof} != trades.json asOf {trades_asof}')
    for rel, label_date in page_labels(root):
        if label_date != trades_asof:
            failures.append(f'{rel}: static label {label_date} != trades.json asOf {trades_asof} (run build_trust_views.py)')
    try:
        age = (date.today() - date.fromisoformat(trades_asof)).days
        if age > MAX_AGE_DAYS:
            failures.append(f'trades.json asOf {trades_asof} is {age} days old (max {MAX_AGE_DAYS})')
    except ValueError:
        failures.append(f'trades.json asOf unparseable: {trades_asof!r}')
    return failures


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    failures = check(root)
    if failures:
        print('LEDGER FRESHNESS CHECK FAILED:')
        for f in failures:
            print(' -', f)
        sys.exit(1)
    print('Ledger freshness OK: feeds and static views agree, pipeline alive.')


if __name__ == '__main__':
    main()
