import json, tempfile, unittest
from datetime import date
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_freshness import check

TODAY = date.today().isoformat()

def build(root, trades_asof, positions_asof, overview_label):
    root = Path(root)
    (root / 'site/assets').mkdir(parents=True)
    (root / 'site/overview').mkdir(parents=True)
    (root / 'site/record').mkdir(parents=True)
    (root / 'site/assets/trades.json').write_text(json.dumps({'summary': {'asOf': trades_asof}, 'trades': []}))
    (root / 'site/assets/positions.json').write_text(json.dumps({'asOf': positions_asof}))
    (root / 'site/overview/index.html').write_text(
        f'<p class="data-freshness">Snapshot through {overview_label}. Win rate is not investment return.</p>')
    (root / 'site/record/index.html').write_text(
        f'<p class="data-freshness">Ledger through {overview_label}; later closes may be missing.</p>')

class TestFreshness(unittest.TestCase):
    def test_fresh_passes(self):
        with tempfile.TemporaryDirectory() as d:
            build(d, TODAY, TODAY, TODAY)
            self.assertEqual(check(d), [])
    def test_stale_static_block_fails(self):
        with tempfile.TemporaryDirectory() as d:
            build(d, TODAY, TODAY, '2000-01-01')
            fails = check(d)
            self.assertTrue(any('static label' in f for f in fails), fails)
    def test_feed_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as d:
            build(d, TODAY, '2000-01-01', TODAY)
            fails = check(d)
            self.assertTrue(any('positions.json' in f for f in fails), fails)
    def test_ancient_feed_tripwire_fails(self):
        with tempfile.TemporaryDirectory() as d:
            build(d, '2020-01-01', '2020-01-01', '2020-01-01')
            fails = check(d)
            self.assertTrue(any('days old' in f for f in fails), fails)
    def test_future_feed_fails(self):
        with tempfile.TemporaryDirectory() as d:
            build(d, '2099-01-01', '2099-01-01', '2099-01-01')
            fails = check(d)
            self.assertTrue(any('future' in f for f in fails), fails)
    def test_missing_label_fails(self):
        with tempfile.TemporaryDirectory() as d:
            build(d, TODAY, TODAY, TODAY)
            (Path(d) / 'site/overview/index.html').write_text('<p>no label here</p>')
            fails = check(d)
            self.assertTrue(any('no freshness label' in f for f in fails), fails)
    def test_missing_required_page_fails(self):
        with tempfile.TemporaryDirectory() as d:
            build(d, TODAY, TODAY, TODAY)
            (Path(d) / 'site/overview/index.html').unlink()
            fails = check(d)
            self.assertTrue(any('required static page missing' in f for f in fails), fails)
    def test_episode_lowercase_stale_fails(self):
        with tempfile.TemporaryDirectory() as d:
            build(d, TODAY, TODAY, TODAY)
            eps = Path(d) / 'site/episodes'
            eps.mkdir(parents=True)
            (eps / '01-x.html').write_text('<p>Historical period totals from ledger through 2020-01-01.</p>')
            fails = check(d)
            self.assertTrue(any('01-x.html' in f and 'static label' in f for f in fails), fails)
    def test_episode_lowercase_fresh_passes(self):
        with tempfile.TemporaryDirectory() as d:
            build(d, TODAY, TODAY, TODAY)
            eps = Path(d) / 'site/episodes'
            eps.mkdir(parents=True)
            (eps / '01-x.html').write_text(f'<p>Historical period totals from ledger through {TODAY}.</p>')
            self.assertEqual(check(d), [])

if __name__ == '__main__':
    unittest.main()
