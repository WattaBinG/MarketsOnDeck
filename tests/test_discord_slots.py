import ast
import pathlib
import unittest

source = (pathlib.Path(__file__).resolve().parents[1] / 'scripts/refresh_wire.py').read_text()
tree = ast.parse(source)
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'select_fresh_with_source_slots')
ns = {'MAX_ITEMS':17, 'ARK_SOURCE':'ARK Invest', 'WB_SOURCE':'Walter Bloomberg (unofficial mirror)', 'DISCORD_SOURCE':'MarketsOnDeck Discord'}
exec(compile(ast.Module(body=[fn], type_ignores=[]), '<source>', 'exec'), ns)
select = ns['select_fresh_with_source_slots']

class SourceSlots(unittest.TestCase):
    def test_discord_already_in_initial_keep_is_pinned(self):
        fresh = [{'source':'MarketsOnDeck Discord','url':f'd{i}','_ts':30-i} for i in range(4)] + [{'source':'RSS','url':f'r{i}','_ts':26-i} for i in range(24)]
        keep=select(fresh)
        visible=([x for x in keep if x.get('_pinned')] + [x for x in keep if not x.get('_pinned')])[:17]
        self.assertEqual(4, sum(x['source']=='MarketsOnDeck Discord' for x in visible))
        self.assertEqual(len(keep),len({x['url'] for x in keep}))
    def test_discord_outside_initial_keep_is_added_once(self):
        fresh = [{'source':'RSS','url':f'r{i}','_ts':100-i} for i in range(23)] + [{'source':'MarketsOnDeck Discord','url':f'd{i}','_ts':77-i} for i in range(5)]
        keep=select(fresh)
        visible=([x for x in keep if x.get('_pinned')] + [x for x in keep if not x.get('_pinned')])[:17]
        self.assertEqual(4, sum(x['source']=='MarketsOnDeck Discord' for x in visible))
        self.assertEqual(len(keep), len({x['url'] for x in keep}))

if __name__=='__main__': unittest.main()
