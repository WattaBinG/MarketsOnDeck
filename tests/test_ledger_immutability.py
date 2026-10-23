import sys, pathlib, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'scripts'))
from check_ledger_immutability import compare

R = lambda **k: dict({'id': 'A-1', 'date': '2026-10-01', 'account': 'Trading', 'symbol': 'X', 'quantity': 2, 'realizedGain': 10.0, 'assetType': 'option'}, **k)

class T(unittest.TestCase):
    def test_new_rows_ok(self):
        self.assertEqual(compare([R()], [R(), R(id='A-2')]), [])
    def test_removed(self):
        self.assertTrue(compare([R()], []))
    def test_retype_blocked_unless_allowed(self):
        self.assertTrue(compare([R()], [R(assetType='equity')]))
        self.assertEqual(compare([R()], [R(assetType='equity')], True), [])
    def test_gain_change_always_blocked(self):
        self.assertTrue(compare([R()], [R(realizedGain=11.0)], True))
    def test_legacy_row_gaining_id(self):
        a = dict(R(), id=None); a.pop('id'); a.update(timestamp='t')
        b = dict(a, id='A-9')
        self.assertEqual(compare([a], [b]), [])

if __name__ == '__main__':
    unittest.main()
