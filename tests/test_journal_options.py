import copy, importlib.util, json, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('validator', ROOT / 'scripts/validate_journal.py')
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)

class JournalOptions(unittest.TestCase):
    def setUp(self): self.data = json.loads((ROOT / 'site/assets/trades.json').read_text())
    def test_valid(self): v.validate(self.data)
    def test_flatten_rejected(self):
        self.data['trades'][0]['assetType'] = 'equity'
        with self.assertRaises(AssertionError): v.validate(self.data)
    def test_scale_rejected(self):
        self.data['trades'][0]['exitPerContract'] = 22.8
        with self.assertRaises(AssertionError): v.validate(self.data)
    def test_missing_contract_rejected(self):
        del self.data['trades'][0]['expiration']
        with self.assertRaises(AssertionError): v.validate(self.data)
    def test_totals_and_fees(self):
        rows = [t for t in self.data['trades'] if t.get('contractId') == 'META:2026-10-02:put:742.5'][:3]
        self.assertEqual(len(self.data['trades']), 353)
        self.assertEqual(self.data['summary']['totalRealizedGain'], 33801.06)
        self.assertEqual(sum(r['entryPerContract'] * r['contracts'] for r in rows), 5470)
        self.assertEqual(sum(r['exitPerContract'] * r['contracts'] for r in rows), 8240)
        self.assertAlmostEqual(sum(r['regulatoryFees'] for r in rows), .16)
        meta_fills = [f for f in self.data['optionOpenFills'] if f.get('contractId') == 'META:2026-10-02:put:742.5']
        self.assertEqual(sum(f['contracts'] for f in meta_fills), 4)

    def test_sep30_repairs(self):
        v.validate_sep30_repairs(self.data)

    def test_futures_positions(self):
        positions = json.loads((ROOT / 'site/assets/positions.json').read_text())
        v.validate_futures(positions)

    def test_no_dust_deleted(self):
        positions = json.loads((ROOT / 'site/assets/positions.json').read_text())
        v.validate_no_dust_deleted(positions)
if __name__ == '__main__': unittest.main()
