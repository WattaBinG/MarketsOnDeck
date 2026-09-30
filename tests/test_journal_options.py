import copy, importlib.util, json, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('validator', ROOT / 'scripts/validate_journal.py')
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)

class JournalOptions(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'site/assets/trades.json').read_text())
        self.positions = json.loads((ROOT / 'site/assets/positions.json').read_text())

    # --- Core v2 validation ---
    def test_valid(self):
        v.validate(self.data)

    def test_flatten_rejected(self):
        self.data['trades'][0]['assetType'] = 'equity'
        with self.assertRaises(AssertionError):
            v.validate(self.data)

    def test_scale_rejected(self):
        self.data['trades'][0]['exitPerContract'] = 22.8
        with self.assertRaises(AssertionError):
            v.validate(self.data)

    def test_missing_contract_rejected(self):
        del self.data['trades'][0]['expiration']
        with self.assertRaises(AssertionError):
            v.validate(self.data)

    def test_non_v2_option_rejected(self):
        # STRICT: Option rows with v2 fields but no schemaVersion must fail (not be skipped)
        bad = copy.deepcopy(self.data)
        for t in bad['trades']:
            if t.get('id') == 'SPCX-close-1':
                del t['schemaVersion']
                break
        with self.assertRaises(AssertionError):
            v.validate(bad)

    def test_missing_exit_premium_rejected(self):
        # Formatter reads exitPremium; missing must fail
        bad = copy.deepcopy(self.data)
        for t in bad['trades']:
            if t.get('id') == 'SPCX-close-1':
                del t['exitPremium']
                break
        with self.assertRaises(AssertionError):
            v.validate(bad)

    # --- Totals ---
    def test_totals_and_fees(self):
        rows = [t for t in self.data['trades']
                if t.get('contractId') == 'META:2026-10-02:put:742.5'][:3]
        self.assertEqual(len(self.data['trades']), 347)
        self.assertEqual(self.data['summary']['totalRealizedGain'], 33801.22)
        self.assertEqual(self.data['summary']['winRate'], 70.52)
        self.assertEqual(sum(r['entryPerContract'] * r['contracts'] for r in rows), 5470)
        self.assertEqual(sum(r['exitPerContract'] * r['contracts'] for r in rows), 8240)
        self.assertAlmostEqual(sum(r['regulatoryFees'] for r in rows), .16)
        meta_fills = [f for f in self.data['optionOpenFills']
                      if f.get('contractId') == 'META:2026-10-02:put:742.5']
        self.assertEqual(sum(f['contracts'] for f in meta_fills), 4)

    def test_no_buys_in_trades(self):
        # Opening buys belong in optionOpenFills only, not trades[]
        for t in self.data['trades']:
            tid = t.get('id', '')
            self.assertFalse(tid.startswith('HD-open'),
                             f'{tid} should not be in trades[]')
            self.assertFalse(tid.startswith('TSLA-open'),
                             f'{tid} should not be in trades[]')

    # --- Sep 30 repairs ---
    def test_sep30_repairs(self):
        v.validate_sep30_repairs(self.data)

    def test_spcx_v2_fields(self):
        # SPCX close must have full v2 fields for the formatter
        spcx = [t for t in self.data['trades'] if t.get('id') == 'SPCX-close-1'][0]
        self.assertEqual(spcx['schemaVersion'], 2)
        self.assertEqual(spcx['positionSide'], 'long')
        self.assertEqual(spcx['exitPremium'], 0.94)
        self.assertEqual(spcx['entryPremium'], 4.25)
        self.assertEqual(spcx['entryPerContract'], 425.0)
        self.assertEqual(spcx['exitPerContract'], 94.0)
        self.assertIn('regulatoryFees', spcx)
        self.assertEqual(spcx['entryFillIds'], ['SPCX-open-1'])

    def test_ccl_v2_fields(self):
        # CCL close must have full v2 fields for the formatter
        ccl = [t for t in self.data['trades'] if t.get('id') == 'CCL-close-1'][0]
        self.assertEqual(ccl['schemaVersion'], 2)
        self.assertEqual(ccl['positionSide'], 'long')
        self.assertEqual(ccl['exitPremium'], 1.05)
        self.assertEqual(ccl['entryPremium'], 0.86)
        self.assertEqual(ccl['entryPerContract'], 86.0)
        self.assertEqual(ccl['exitPerContract'], 105.0)
        self.assertIn('regulatoryFees', ccl)
        self.assertEqual(ccl['entryFillIds'], ['CCL-open-1'])

    def test_spcx_lot_link(self):
        # SPCX-close-1 must link to Sep 22 $4.25 lot, not Sep 28 $0.87
        fills = {f['id']: f for f in self.data['optionOpenFills']}
        spcx = [t for t in self.data['trades'] if t.get('id') == 'SPCX-close-1'][0]
        self.assertEqual(spcx['entryFillIds'], ['SPCX-open-1'])
        self.assertEqual(fills['SPCX-open-1']['premium'], 4.25)
        self.assertEqual(fills['SPCX-open-2']['premium'], 0.87)

    # --- Positions ---
    def test_futures_positions(self):
        v.validate_futures(self.positions)

    def test_no_dust_deleted(self):
        v.validate_no_dust_deleted(self.positions)

    def test_position_bases(self):
        v.validate_position_bases(self.positions)

if __name__ == '__main__':
    unittest.main()
