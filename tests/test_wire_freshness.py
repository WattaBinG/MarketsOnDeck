"""Oct 15 incident regression tests: undated RSS items must never pose as
fresh, and flash data prints must never win Top Story."""
import ast
import pathlib
import re
import unittest

source = (pathlib.Path(__file__).resolve().parents[1] / 'scripts/refresh_wire.py').read_text()
tree = ast.parse(source)

ns = {'re': re}
for node in tree.body:
    if isinstance(node, ast.Assign) and any(getattr(t, 'id', '') == 'DATA_PRINT' for t in node.targets):
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<source>', 'exec'), ns)
DATA_PRINT = ns['DATA_PRINT']

fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
ns2 = {'SOURCE_W': {'EIA': 2.0, 'CNBC': 1.5}, 'MAX_AGE_HOURS': 36,
       'MACRO': re.compile(r'x'), 'BROAD': re.compile(r'x'), 'MOVE': re.compile(r'x'),
       'ATTENTION': re.compile(r'x'), 'ATTENTION_BOOST': 1.30}
for name in ('recency_factor', 'cluster_score'):
    exec(compile(ast.Module(body=[fns[name]], type_ignores=[]), '<source>', 'exec'), ns2)

NOW = 1_800_000_000.0
H = 3600.0

def item(src, age_h):
    return {'source': src, 'headline': 'h', '_ts': NOW - age_h * H}

class DataPrint(unittest.TestCase):
    def test_matches_flash_print(self):
        self.assertTrue(DATA_PRINT.search(
            'JAPANESE FOREIGN STOCK INVESTMENT ACTUAL -760.6B (FORECAST -, PREVIOUS 1,324.6B) $MACRO'))
        self.assertTrue(DATA_PRINT.search(
            'US CPI ACTUAL 3.1% (FORECAST 3.0%, PREVIOUS 2.9%)'))
    def test_ignores_real_headlines(self):
        self.assertFalse(DATA_PRINT.search('Fed holds rates, Powell flags forecast risk'))
        self.assertFalse(DATA_PRINT.search('Stocks rally after CPI comes in below forecast'))
        self.assertFalse(DATA_PRINT.search('Previous winners and actual losers of the AI boom'))

class SameSourceCap(unittest.TestCase):
    def test_same_source_twice_does_not_double_base(self):
        one = {'items': [item('MarketsOnDeck Discord', 0.1)]}
        two = {'items': [item('MarketsOnDeck Discord', 0.1), item('MarketsOnDeck Discord', 0.2)]}
        s1 = ns2['cluster_score'](one, NOW)[0]
        s2 = ns2['cluster_score'](two, NOW)[0]
        self.assertAlmostEqual(s1, s2, places=6)
    def test_two_real_sources_still_corroborate(self):
        one = {'items': [item('CNBC', 1)]}
        two = {'items': [item('CNBC', 1), item('EIA', 1)]}
        s1 = ns2['cluster_score'](one, NOW)[0]
        s2 = ns2['cluster_score'](two, NOW)[0]
        self.assertGreater(s2, s1)

class AssumedAge(unittest.TestCase):
    def test_old_assumed_item_loses_to_fresh_real(self):
        fresh_real = {'items': [item('CNBC', 0.5)]}
        stale_undated = {'items': [item('EIA', 12.0)]}  # _ts already carries the assumed age
        s_real = ns2['cluster_score'](fresh_real, NOW)[0]
        s_stale = ns2['cluster_score'](stale_undated, NOW)[0]
        self.assertGreater(s_real, s_stale)

if __name__ == '__main__':
    unittest.main()
