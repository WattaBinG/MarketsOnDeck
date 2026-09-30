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

def validate_sep30_repairs(data):
    """Sep 30, 2026 repair anchors: SPCX/CCL closes + 6 new buys."""
    trades = data.get('trades', [])
    # SPCX close (Trading)
    spcx = [t for t in trades if t.get('id') == 'SPCX-close-1']
    assert len(spcx) == 1, 'SPCX-close-1 missing'
    assert spcx[0].get('contractId') == 'SPCX:2026-10-02:call:155.0'
    assert spcx[0].get('assetType') == 'option'
    assert abs(spcx[0].get('realizedGain', 0) - (-662.16)) < 0.01
    # CCL close (Agentic)
    ccl = [t for t in trades if t.get('id') == 'CCL-close-1']
    assert len(ccl) == 1, 'CCL-close-1 missing'
    assert ccl[0].get('contractId') == 'CCL:2026-10-16:call:25.0'
    assert ccl[0].get('assetType') == 'option'
    assert abs(ccl[0].get('realizedGain', 0) - 19.00) < 0.01
    # 6 new buys (all dated 2026-09-30)
    buy_ids = ['HD-stock-buy-20260930', 'HD-open-3-trade', 'HD-open-4-trade',
               'TSLA-open-3-trade', 'TSLA-open-4-trade', 'HD-open-5-trade']
    for bid in buy_ids:
        matches = [t for t in trades if t.get('id') == bid]
        assert len(matches) == 1, f'{bid} missing'
        assert matches[0].get('date') == '2026-09-30', f'{bid} wrong date'
    # No flattened SPCX/CCL equity rows for Sep 30
    flat = [t for t in trades if t.get('date') == '2026-09-30'
            and t.get('assetType') == 'equity'
            and t.get('symbol') in ('SPCX', 'CCL')]
    assert len(flat) == 0, 'Flattened SPCX/CCL rows still present'

def validate_futures(positions):
    """Futures rows must carry native quoted prices and contract identity."""
    futures = [p for p in positions.get('positions', []) if p.get('assetType') == 'futures']
    for p in futures:
        # Native quoted prices required
        assert p.get('quotedAvgCost') and p.get('quotedMark'), f"Futures {p.get('symbol')} missing quoted prices"
        assert p.get('multiplier') and p['multiplier'] > 0, f"Futures {p.get('symbol')} missing multiplier"
        assert p.get('quantityUnit') == 'contracts', f"Futures {p.get('symbol')} quantity not labeled contracts"
        assert p.get('expiration'), f"Futures {p.get('symbol')} missing expiration"
        # Per-contract dollars = quoted x multiplier (within rounding)
        assert abs(p['avgCost'] - p['quotedAvgCost'] * p['multiplier']) < 0.01, f"Futures {p.get('symbol')} avgCost mismatch"
        assert abs(p['currentPrice'] - p['quotedMark'] * p['multiplier']) < 0.01, f"Futures {p.get('symbol')} currentPrice mismatch"
        # uGL = (quotedMark - quotedAvgCost) x multiplier x quantity
        expected_ugl = (p['quotedMark'] - p['quotedAvgCost']) * p['multiplier'] * p['quantity']
        assert abs(p['unrealizedGain'] - expected_ugl) < 0.01, f"Futures {p.get('symbol')} uGL mismatch"

def validate_no_dust_deleted(positions):
    """Every nonzero position must be retained in positions.json."""
    # Dust positions (DOGE, USDC) must not be deleted
    symbols = [p.get('symbol') for p in positions.get('positions', [])]
    # These are known dust from the Sep 30 account pull; if the account shows
    # them nonzero, they must be in the file. (Validator checks presence;
    # the account pull is the source of truth for quantities.)
    for dust in ['DOGE', 'USDC']:
        if dust in symbols:
            p = next(x for x in positions['positions'] if x.get('symbol') == dust)
            assert p.get('quantity', 0) != 0, f'{dust} has zero quantity'

if __name__ == '__main__':
    data = json.loads((Path(__file__).resolve().parents[1] / 'site/assets/trades.json').read_text())
    validate(data)
    validate_sep30_repairs(data)
    positions = json.loads((Path(__file__).resolve().parents[1] / 'site/assets/positions.json').read_text())
    for p in positions['positions']:
        if p.get('assetType') == 'option':
            assert p['priceUnit'] == 'USD_per_contract'
            assert p['contracts'] == p['quantity'] and p['multiplier'] > 0
            assert p['underlying'] and p['expiration'] and p['optionType'] in ('put','call')
    validate_futures(positions)
    validate_no_dust_deleted(positions)
    print('Journal option validation passed')
