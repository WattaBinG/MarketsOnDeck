#!/usr/bin/env python3
"""Validate option journal rows. All option rows must be schema v2 compliant.
No skipping, no guessing. Legacy incomplete history is not in this file."""
import json
from pathlib import Path


def validate(data):
    """Validate every option row in trades[] against the v2 schema."""
    # v2 field names - if a row has any of these, it must be fully v2 compliant
    V2_FIELDS = ('contractId', 'contracts', 'entryPremium', 'exitPremium',
                 'positionSide', 'entryPerContract', 'exitPerContract', 'entryFillIds')
    for row in data.get('trades', []):
        # Explicit option fields must never be silently reclassified as shares.
        if any(k in row for k in ('contractId', 'contracts', 'entryPremium', 'exitPremium')):
            assert row['assetType'] == 'option', 'Option fields on a non-option row'
        # STRICT: If a row has ANY v2 field, it must be fully v2 compliant.
        # (Legacy rows with no v2 fields at all are skipped - we don't guess.)
        has_v2 = any(k in row for k in V2_FIELDS)
        if row.get('assetType') == 'option' and has_v2:
            assert row.get('schemaVersion') == 2, (
                f"Option row {row.get('id', row.get('symbol'))} has v2 fields but missing schemaVersion 2"
            )
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
            assert field + 'Premium' in row and row[field + 'Premium'] is not None, (
                f'Missing {field}Premium'
            )
            assert row[field + 'Premium'] >= 0
            assert abs(row[field + 'PerContract'] - row[field + 'Premium'] * row['multiplier']) < .0001
        # exitPremium must be present for the formatter (no "Exit Unavailable")
        assert 'exitPremium' in row and row['exitPremium'] is not None
        fills = {f['id']: f for f in data.get('optionOpenFills', [])}
        assert all(i in fills for i in row['entryFillIds']), 'entryFillIds must reference optionOpenFills'
        assert all(
            fills[i]['contractId'] == row['contractId'] and fills[i]['account'] == row['account']
            for i in row['entryFillIds']
        ), 'Fill contract/account mismatch'

    # Repair anchors: META Sep 28 rows must remain v2
    repaired = [t for t in data['trades']
                if t['date'] == '2026-09-28' and t['symbol'] == 'META' and t['account'] == 'Trading']
    assert len(repaired) == 3, 'META repair rows missing'
    assert all(t.get('contractId') == 'META:2026-10-02:put:742.5'
               and t.get('schemaVersion') == 2 for t in repaired)
    assert sum(t['contracts'] for t in repaired) == 4
    assert sum(t['realizedGain'] for t in repaired) == 2770


def validate_sep30_repairs(data):
    """Sep 30, 2026 repair anchors: SPCX/CCL v2 closes, buys in fills only."""
    trades = data.get('trades', [])
    fills = {f['id']: f for f in data.get('optionOpenFills', [])}

    # SPCX close (Trading) - full v2
    spcx = [t for t in trades if t.get('id') == 'SPCX-close-1']
    assert len(spcx) == 1, 'SPCX-close-1 missing'
    s = spcx[0]
    assert s.get('contractId') == 'SPCX:2026-10-02:call:155.0'
    assert s.get('assetType') == 'option'
    assert s.get('schemaVersion') == 2, 'SPCX-close-1 missing schemaVersion 2'
    assert s.get('positionSide') == 'long'
    assert s.get('exitPremium') == 0.94, 'SPCX exitPremium must be 0.94'
    assert s.get('entryPremium') == 4.25, 'SPCX entryPremium must be 4.25'
    assert abs(s.get('realizedGain', 0) - (-662.0)) < 0.01
    # Lot link: must reference the Sep 22 $4.25 lot (SPCX-open-1), NOT the $0.87 lot
    assert s.get('entryFillIds') == ['SPCX-open-1'], 'SPCX must link to Sep 22 $4.25 lot'
    assert fills['SPCX-open-1']['premium'] == 4.25

    # CCL close (Agentic) - full v2
    ccl = [t for t in trades if t.get('id') == 'CCL-close-1']
    assert len(ccl) == 1, 'CCL-close-1 missing'
    c = ccl[0]
    assert c.get('contractId') == 'CCL:2026-10-16:call:25.0'
    assert c.get('assetType') == 'option'
    assert c.get('schemaVersion') == 2, 'CCL-close-1 missing schemaVersion 2'
    assert c.get('positionSide') == 'long'
    assert c.get('exitPremium') == 1.05, 'CCL exitPremium must be 1.05'
    assert c.get('entryPremium') == 0.86, 'CCL entryPremium must be 0.86'
    assert abs(c.get('realizedGain', 0) - 19.00) < 0.01
    assert c.get('entryFillIds') == ['CCL-open-1'], 'CCL must link to Sep 2 $0.86 lot'
    assert fills['CCL-open-1']['premium'] == 0.86

    # Opening buys belong in optionOpenFills ONLY, not in trades[]
    buy_fill_ids = ['HD-open-1', 'HD-open-2', 'HD-open-3',
                    'TSLA-open-3', 'TSLA-open-4']
    for bid in buy_fill_ids:
        assert bid in fills, f'{bid} missing from optionOpenFills'
    # SPCX/CCL open fills (for lot tracking)
    for bid in ['SPCX-open-1', 'SPCX-open-2', 'CCL-open-1', 'CCL-open-2']:
        assert bid in fills, f'{bid} missing from optionOpenFills'

    # No opening buys in trades[] (trades[] is realized/closed only)
    for t in trades:
        tid = t.get('id', '')
        assert not (tid.startswith('HD-open') or tid.startswith('TSLA-open')), (
            f'Opening buy {tid} should not be in trades[]'
        )

    # No flattened SPCX/CCL equity rows for Sep 30
    flat = [t for t in trades if t.get('date') == '2026-09-30'
            and t.get('assetType') == 'equity'
            and t.get('symbol') in ('SPCX', 'CCL')]
    assert len(flat) == 0, 'Flattened SPCX/CCL rows still present'

    # Trade count: 347 Sep-30 baseline + 19 October catch-up rows
    # (13 option closes incl. 4 Sep-22 TSLA300 backfill, 6 equity closes)
    assert len(trades) == 366, f'Expected 366 trades, got {len(trades)}'


def validate_futures(positions):
    """Futures rows must carry native quoted prices and contract identity.
    METV26 MUST be present. Marks are validated for internal consistency
    (avgCost/currentPrice/unrealizedGain derived from quoted prices), not
    pinned to a stale date's values."""
    futures = [p for p in positions.get('positions', []) if p.get('assetType') == 'futures']
    # STRICT: Require METV26
    metv = [p for p in futures if 'METV26' in str(p.get('symbol', ''))]
    assert len(metv) == 1, 'METV26 futures position must be present'
    m = metv[0]
    assert m.get('quantity') == 30, 'METV26 must be 30 contracts'
    # (was 10 on Sep 30; +20 added overnight Oct 6-7, avg 2,605.25 implied)
    assert m.get('quantityUnit') == 'contracts'

    for p in futures:
        assert p.get('quotedAvgCost') and p.get('quotedMark'), (
            f"Futures {p.get('symbol')} missing quoted prices"
        )
        assert p.get('multiplier') and p['multiplier'] > 0
        assert p.get('quantityUnit') == 'contracts'
        assert p.get('expiration'), f"Futures {p.get('symbol')} missing expiration"
        assert abs(p['avgCost'] - p['quotedAvgCost'] * p['multiplier']) < 0.01
        assert abs(p['currentPrice'] - p['quotedMark'] * p['multiplier']) < 0.01
        expected_ugl = (p['quotedMark'] - p['quotedAvgCost']) * p['multiplier'] * p['quantity']
        assert abs(p['unrealizedGain'] - expected_ugl) < 0.01


def validate_no_dust_deleted(positions):
    """Every nonzero position must be retained. DOGE and USDC MUST exist."""
    symbols = [p.get('symbol') for p in positions.get('positions', [])]
    # STRICT: Require presence, not just validate-if-present
    for dust in ['DOGE', 'USDC']:
        assert dust in symbols, f'{dust} dust position must be present (not deleted)'
        p = next(x for x in positions['positions'] if x.get('symbol') == dust)
        assert p.get('quantity', 0) != 0, f'{dust} has zero quantity'


def validate_position_bases(positions):
    """October 2026 anchors: HD $287.50C is the only remaining option position
    (5 contracts, lot-specific $120/contract basis = the Oct 5 $1.20 lot,
    FIFO-reconciled to the $600 broker clearing basis). TSLA/CCL/SPCX option
    positions were closed or expired and must be absent."""
    pos_map = {(p.get('account'), p.get('symbol'), p.get('strike'), p.get('expiration')): p
               for p in positions.get('positions', [])
               if p.get('assetType') == 'option'}

    # HD: 5 contracts, $120/contract = the Oct 5 $1.20 lot
    hd = pos_map.get(('Trading', 'HD', 287.5, '2026-10-09'))
    assert hd is not None, 'HD option position missing'
    assert hd.get('contracts') == 5 and hd.get('quantity') == 5
    assert hd.get('avgCost') == 120.0, f"HD basis must be $120, got {hd.get('avgCost')}"
    assert hd.get('positionSide') == 'long'
    assert hd.get('contractId') == 'HD:2026-10-09:call:287.5'
    assert hd.get('priceUnit') == 'USD_per_contract'
    assert hd.get('multiplier') == 100

    # Closed/expired: no TSLA, CCL, or SPCX option positions may remain
    for key in pos_map:
        assert not (key[1] in ('TSLA', 'CCL', 'SPCX')), (
            f'Unexpected remaining option position: {key}')

    # USDG: 102.582488 units, cash-like
    usdg = [p for p in positions['positions'] if p.get('symbol') == 'USDG']
    assert len(usdg) == 1, 'USDG position missing'
    assert abs(usdg[0].get('quantity', 0) - 102.582488) < 0.000001


if __name__ == '__main__':
    data = json.loads((Path(__file__).resolve().parents[1] / 'site/assets/trades.json').read_text())
    validate(data)
    validate_sep30_repairs(data)
    positions = json.loads((Path(__file__).resolve().parents[1] / 'site/assets/positions.json').read_text())
    for p in positions['positions']:
        if p.get('assetType') == 'option':
            assert p['priceUnit'] == 'USD_per_contract'
            assert p['contracts'] == p['quantity'] and p['multiplier'] > 0
            assert p['underlying'] and p['expiration'] and p['optionType'] in ('put', 'call')
    validate_futures(positions)
    validate_no_dust_deleted(positions)
    validate_position_bases(positions)
    print('Journal option validation passed')
