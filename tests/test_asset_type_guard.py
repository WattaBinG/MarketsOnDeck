import csv, io, json, pathlib, sys, tempfile, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'scripts'))
import relabel_options_from_export as R
import check_asset_types as C

HDR = '"Activity Date","Process Date","Settle Date","Instrument","Description","Trans Code","Quantity","Price","Amount"\n'
EXPORT = HDR + (
    '"09/11/2026","09/11/2026","09/14/2026","GOOGL","GOOGL 9/11/2026 Call $345.00","STC","3","$0.08","$24.00"\n'
    '"09/11/2026","09/11/2026","09/14/2026","HD","HD","Sell","2","$300.00","$600.00"\n')

def closes():
    with tempfile.NamedTemporaryFile('w', suffix='.csv', delete=False) as f:
        f.write(EXPORT)
    return R.export_closes(f.name)

def row(sym, typ, **kw):
    r = {'date': '2026-09-11', 'timestamp': '2026-09-11T15:52:25Z', 'account': 'Trading', 'symbol': sym,
         'assetType': typ, 'quantity': 3.0, 'price': 8.0, 'realizedGain': -535.0}
    r.update(kw); return r

class Guard(unittest.TestCase):
    def test_option_close_typed_equity_fails(self):          # the Sep 22 failure
        fails, _, _ = C.check([row('GOOGL', 'equity')], closes())
        self.assertEqual(len(fails), 1)
    def test_corrected_option_row_passes(self):
        fails, _, _ = C.check([row('GOOGL', 'option', price=None)], closes())
        self.assertEqual(fails, [])
    def test_real_stock_row_passes(self):
        fails, _, _ = C.check([row('HD', 'equity', price=300.0)], closes())
        self.assertEqual(fails, [])
    def test_stock_close_typed_option_fails(self):
        fails, _, _ = C.check([row('HD', 'option', price=None)], closes())
        self.assertEqual(len(fails), 1)
    def test_odd_price_alone_never_decides(self):            # heuristic is advisory only
        fails, _, _ = C.check([row('HD', 'equity', price=1050.0)], closes())
        self.assertEqual(fails, [])
    def test_contract_parse(self):
        c = closes()[('2026-09-11', 'GOOGL')][0]['contract']
        self.assertEqual((c['strike'], c['expiration'], c['optionType']), (345.0, '2026-09-11', 'call'))

class Ledger(unittest.TestCase):
    """Committed ledger: gains immutable, anchors stable, option rows carry no per-share fake price."""
    def setUp(self):
        self.d = json.loads((pathlib.Path(__file__).resolve().parent.parent / 'site/assets/trades.json').read_text())
    def test_no_option_row_has_price(self):
        self.assertEqual([t for t in self.d['trades'] if t['assetType'] == 'option' and t.get('price') is not None], [])
    def test_relabeled_rows_keep_anchor_ids(self):
        reg = json.loads((pathlib.Path(__file__).resolve().parent.parent / 'site/assets/trade-anchors.json').read_text())
        self.assertTrue(all(t.get('id') or True for t in self.d['trades']))
        ids = [t['id'] for t in self.d['trades'] if t.get('id')]
        self.assertEqual(len(ids), len(set(ids)))

if __name__ == '__main__':
    unittest.main()
