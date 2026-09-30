#!/usr/bin/env python3
"""Validate explicit option rows. Legacy incomplete history is not guessed."""
import json
from pathlib import Path

def validate(data):
    for row in data.get('trades', []):
        # Explicit option fields must never be silently reclassified as shares.
        if any(k in row for k in ('contractId', 'contracts', 'entryPremium', 'exitPremium')):
            assert row['assetType'] == 'option', 'Option fields on a non-option row'
        if row.get('schemaVersion') != 2:
            continue
        assert row['assetType'] == 'option'
        for k in ('underlying', 'contractId', 'expiration', 'positionSide', 'action', 'entryFillIds'):
            assert row.get(k), 'Missing ' + k
        assert row['optionType'] in ('call', 'put')
        assert row['positionSide'] in ('long', 'short')
        assert row['action'] in ('sell_to_close', 'buy_to_close', 'expire', 'exercise', 'assignment')
        assert row['contracts'] > 0 and int(row['contracts']) == row['contracts'] == row['quantity']
        assert row['strike'] > 0 and row['multiplier'] > 0
        assert row['priceUnit'] == 'USD_per_share'
        assert row['price'] is None, 'Ambiguous legacy option price'
        for field in ('entry', 'exit'):
            assert row[field + 'Premium'] >= 0
            assert abs(row[field + 'PerContract'] - row[field + 'Premium'] * row['multiplier']) < .0001
        fills = {f['id']: f for f in data.get('optionOpenFills', [])}
        assert all(i in fills for i in row['entryFillIds'])
        assert all(fills[i]['contractId'] == row['contractId'] and fills[i]['account'] == row['account'] for i in row['entryFillIds'])
    # Repair anchors reject a later refresh flattening these verified contracts.
    repaired = [t for t in data['trades'] if t['date'] == '2026-09-28' and t['symbol'] == 'META' and t['account'] == 'Trading']
    assert len(repaired) == 3
    assert all(t.get('contractId') == 'META:2026-10-02:put:742.5' and t.get('schemaVersion') == 2 for t in repaired)
    assert sum(t['contracts'] for t in repaired) == 4
    assert sum(t['realizedGain'] for t in repaired) == 2770

if __name__ == '__main__':
    validate(json.loads((Path(__file__).resolve().parents[1] / 'site/assets/trades.json').read_text()))
    positions = json.loads((Path(__file__).resolve().parents[1] / 'site/assets/positions.json').read_text())
    for p in positions['positions']:
        if p.get('assetType') == 'option':
            assert p['priceUnit'] == 'USD_per_contract'
            assert p['contracts'] == p['quantity'] and p['multiplier'] > 0
            assert p['underlying'] and p['expiration'] and p['optionType'] in ('put','call')
    print('Journal option validation passed')
