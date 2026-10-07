import importlib.util,json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('trust',ROOT/'scripts/build_trust_views.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class TrustViews(unittest.TestCase):
 def test_episode_totals_match_ledger(self):
  trades=json.loads((ROOT/'site/assets/trades.json').read_text())['trades']
  for p in (ROOT/'site/episodes').glob('*.html'):
   for a,b,key,text in re.findall(r'<span data-ledger-start="([^"]+)" data-ledger-end="([^"]+)" data-ledger-metric="([^"]+)">(.*?)</span>',p.read_text()):self.assertEqual(text,m.period(trades,a,b)[key])
 def test_old_claims_removed(self):
  s=(ROOT/'site/episodes/02-the-august-swing.html').read_text();self.assertNotIn("doesn't yet have entries past August 20",s)
  s=(ROOT/'site/overview/index.html').read_text();self.assertNotIn('Trading vs. Agentic vs. The Market',s);self.assertIn('287.5 call',s)
 def test_decimal_math(self):self.assertEqual(m.period([{'date':'2026-01-01','realizedGain':.1},{'date':'2026-01-01','realizedGain':.2}],'2026-01-01','2026-01-01')['net'],'+$0.30')
