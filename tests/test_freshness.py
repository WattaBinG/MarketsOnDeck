import json, tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_freshness import check

def build(root, trades_asof, positions_asof, overview_label):
    root = Path(root)
    (root / 'site/assets').mkdir(parents=True)
    (root / 'site/overview').mkdir(parents=True)
    (root / 'site/assets/trades.json').write_text(json.dumps({'summary': {'asOf': trades_asof}, 'trades': []}))
    (root / 'site/assets/positions.json').write_text(json.dumps({'asOf': positions_asof}))
    (root / 'site/overview/index.html').write_text(
        f'<p class="data-freshness">Snapshot through {overview_label}. Win rate is not investment return.</p>')

class TestFreshness(unittest.TestCase):
    def test_fresh_passes(self):
        with tempfile.TemporaryDirectory() as d:
            build(d, '2099-01-01', '2099-01-01', '2099-01-01')
            self.assertEqual(check(d), [])
    def test_stale_static_block_fails(self):
        with tempfile.TemporaryDirectory() as d:
            build(d, '2099-01-02', '2099-01-02', '2099-01-01')
            fails = check(d)
            self.assertTrue(any('static label' in f for f in fails), fails)
    def test_feed_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as d:
            build(d, '2099-01-02', '2099-01-01', '2099-01-02')
            fails = check(d)
            self.assertTrue(any('positions.json' in f for f in fails), fails)
    def test_ancient_feed_tripwire_fails(self):
        with tempfile.TemporaryDirectory() as d:
            build(d, '2020-01-01', '2020-01-01', '2020-01-01')
            fails = check(d)
            self.assertTrue(any('days old' in f for f in fails), fails)

if __name__ == '__main__':
    unittest.main()
