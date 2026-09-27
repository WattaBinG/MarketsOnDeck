#!/usr/bin/env python3
"""One-shot, read-only Discord Wire eligibility audit. Prints counts, never posts."""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refresh_wire import DISCORD_MONEY, SPORT, DISCORD_UA

cutoff = datetime.fromisoformat('2026-09-25T20:40:00+00:00')
archive = json.loads((Path(__file__).resolve().parents[1] / 'site/assets/wire-archive.json').read_text())
archived_urls = {it.get('url') for it in archive.get('items', [])}
visible = json.loads((Path(__file__).resolve().parents[1] / 'site/assets/wire.json').read_text())
visible_urls = {it.get('url') for it in visible.get('items', [])}
token = os.environ['DISCORD_BOT_TOKEN'].strip()
channels = [x.strip() for x in os.environ['DISCORD_NEWS_CHANNEL_ID'].split(',') if x.strip()]
for index, channel in enumerate(channels, 1):
    counts = {k: 0 for k in ('retrieved', 'in_window', 'text_link', 'sport_excluded', 'market_excluded', 'eligible', 'archived_match', 'visible_match', 'new_candidate')}
    before = None
    seen_ids = set()
    complete = False
    for page in range(30):
        query = {'limit': 100}
        if before: query['before'] = before
        url = f'https://discord.com/api/v10/channels/{channel}/messages?{urlencode(query)}'
        req = Request(url, headers={'User-Agent': DISCORD_UA, 'Authorization': f'Bot {token}'})
        try:
            with urlopen(req, timeout=20) as r: batch = json.load(r)
        except HTTPError as e:
            print(f'channel={index} HTTP={e.code}', file=sys.stderr)
            sys.exit(1)
        if not isinstance(batch, list) or not batch:
            complete = True
            break
        counts['retrieved'] += len(batch)
        ids = [int(m['id']) for m in batch if m.get('id')]
        if not ids or min(ids) in seen_ids:
            print(f'channel={index} pagination stalled', file=sys.stderr)
            sys.exit(1)
        seen_ids.add(min(ids))
        before = str(min(ids))
        older = False
        for msg in batch:
            try: ts = datetime.fromisoformat(str(msg.get('timestamp')).replace('Z', '+00:00'))
            except (ValueError, TypeError): continue
            if ts < cutoff:
                older = True
                continue
            counts['in_window'] += 1
            content = (msg.get('content') or '').strip()
            urls = re.findall(r'https?://[^\s<>()]+', content)
            text = re.sub(r'\s+', ' ', re.sub(r'https?://[^\s<>()]+', '', content)).strip(' -|')
            if not text and msg.get('embeds'):
                emb = msg['embeds'][0] or {}
                text = (emb.get('title') or '').strip()
                if not urls and emb.get('url'): urls = [emb['url']]
            if not text or not urls: continue
            counts['text_link'] += 1
            if SPORT.search(text):
                counts['sport_excluded'] += 1
                continue
            if not DISCORD_MONEY.search(text):
                counts['market_excluded'] += 1
                continue
            counts['eligible'] += 1
            if urls[0] in archived_urls: counts['archived_match'] += 1
            elif urls[0] in visible_urls: counts['visible_match'] += 1
            else: counts['new_candidate'] += 1
        if older or len(batch) < 100:
            complete = True
            break
        time.sleep(.2)
    print(json.dumps({'channel_index': index, 'cutoff_utc': cutoff.isoformat(), 'complete': complete, 'pages': page + 1, **counts}, sort_keys=True))
    if not complete: sys.exit(2)
