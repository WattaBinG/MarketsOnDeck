#!/usr/bin/env python3
"""Freshness gate: fail loudly when published ledger views lag the ledger feeds.

Deterministic, no network. Checks:
  1. trades.json asOf == positions.json asOf (feeds must move together).
  2. Every 'Snapshot through DATE' / 'Ledger through DATE' label in static
     pages matches trades.json asOf (build_trust_views.py must have run).
     Matching is case-insensitive: build_trust_views.py emits episode text
     as lowercase 'ledger through'.
  3. Required pages/labels must exist: a missing page or a page with no
     freshness label is a failure, not a pass.
  4. Tripwire: trades.json asOf no older than MAX_AGE_DAYS from today and
     not in the future (guards a silently dead pipeline and a bad clock).

Exit 1 with a report on any failure; exit 0 when fresh.
"""
import json, re, sys
from datetime import date
from pathlib import Path

MAX_AGE_DAYS = 7
LABEL_RE = re.compile(r'(?:Snapshot through|Ledger through)\s*(\d{4}-\d{2}-\d{2})', re.IGNORECASE)
# Pages whose freshness labels are stamped by build_trust_views.py: these must
# exist and carry current labels. (site/record/index.html renders its label
# client-side from the feeds, so it is checked only if a static label appears.)
GENERATED_PAGES = ('site/overview/index.html',)
OPTIONAL_PAGES = ('site/record/index.html',)


def feed_asof(root, name):
    data = json.loads((root / name).read_text())
    return data.get('asOf') or data.get('summary', {}).get('asOf')


def page_labels(root, failures):
    labels = []
    required = [(root / rel, rel) for rel in GENERATED_PAGES]
    eps = root / 'site/episodes'
    if eps.is_dir():
        required.extend((p, str(p.relative_to(root))) for p in sorted(eps.glob('*.html')))
    for p, rel in required:
        if not p.exists():
            failures.append(f'{rel}: required static page missing')
            continue
        found = LABEL_RE.findall(p.read_text())
        if not found:
            failures.append(f'{rel}: no freshness label found (run build_trust_views.py)')
        labels.extend((rel, d) for d in found)
    for rel in OPTIONAL_PAGES:
        p = root / rel
        if p.exists():
            labels.extend((rel, d) for d in LABEL_RE.findall(p.read_text()))
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
    for rel, label_date in page_labels(root, failures):
        if label_date != trades_asof:
            failures.append(f'{rel}: static label {label_date} != trades.json asOf {trades_asof} (run build_trust_views.py)')
    try:
        age = (date.today() - date.fromisoformat(trades_asof)).days
        if age > MAX_AGE_DAYS:
            failures.append(f'trades.json asOf {trades_asof} is {age} days old (max {MAX_AGE_DAYS})')
        elif age < 0:
            failures.append(f'trades.json asOf {trades_asof} is {-age} days in the future')
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
