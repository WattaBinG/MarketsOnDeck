import ast
import json
import pathlib
import re
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from urllib.request import Request
from urllib.error import HTTPError

SOURCE = pathlib.Path(__file__).resolve().parents[1] / 'scripts/refresh_wire.py'
tree = ast.parse(SOURCE.read_text())
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'fetch_discord')

class FakeResponse:
    def __init__(self, batch): self.batch = json.dumps(batch).encode()
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self): return self.batch

class DiscordPagination(unittest.TestCase):
    def test_walks_back_and_dedupes_archive_before_cursor_advances(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root/'site/assets').mkdir(parents=True)
            (root/'data').mkdir()
            (root/'site/assets/wire-archive.json').write_text(json.dumps({'items':[{'url':'https://news.test/archived'}]}))
            (root/'data/discord-posts.json').write_text('{}')
            now = datetime.now(timezone.utc)
            def msg(i, url):
                return {'id':str(i),'content':f'Stock market update {url}', 'timestamp':(now-timedelta(minutes=i)).isoformat()}
            # The first response is newest-first; one archive item is on the older page.
            first = [msg(i, f'https://news.test/{i}') for i in range(200,100,-1)]
            second = [msg(100,'https://news.test/archived'), msg(99,'https://news.test/99'), msg(1,'https://news.test/old')]
            urls=[]
            def fake_open(req,timeout):
                urls.append(req.full_url)
                return FakeResponse(first if len(urls)==1 else second)
            import os
            ns={'os':os,'json':json,'re':re,'Request':Request,'urlopen':fake_open,'HTTPError':HTTPError,
                'sys':__import__('sys'),'datetime':datetime,'timezone':timezone,'MAX_AGE_HOURS':36,
                'ASSETS':root/'site/assets','ROOT':root,'SPORT':re.compile('homer'),
                'DISCORD_MONEY':re.compile('stock',re.I),'DISCORD_SOURCE':'MarketsOnDeck Discord',
                'DISCORD_MAX_ITEMS':10,'DISCORD_UA':'DiscordBot test',
                'classify':lambda title,bias:bias}
            exec(compile(ast.Module(body=[fn],type_ignores=[]),str(SOURCE),'exec'),ns)
            state={'discord_last_message_id':'50'}
            with patch.dict(os.environ, {'DISCORD_BOT_TOKEN':'token','DISCORD_NEWS_CHANNEL_ID':'123'}):
                items=ns['fetch_discord'](state)
            self.assertEqual(2,len(urls))
            self.assertIn('after=50',urls[0])
            self.assertIn('before=101',urls[1])
            self.assertEqual('200',state['discord_last_message_id'])
            self.assertNotIn('https://news.test/archived',[i['url'] for i in items])
            self.assertEqual(10,len(items))

if __name__=='__main__': unittest.main()
