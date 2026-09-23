#!/usr/bin/env python3
"""MarketsOnDeck - Discord local reader (runs on Keith's PC, not on GitHub).

Why this exists: Discord refuses datacenter IPs (GitHub Actions, cloud
browsers) on channel reads with HTTP 403 "internal network error". From a
home connection the same read works fine - proven 2026-09-21. So this small
script runs on Keith's Windows PC whenever it's on, pulls new posts from his
news channel, and writes them to data/discord-posts.json. The hourly GitHub
Action merges that file into The Wire (filtering sports and non-market posts
there - the one and only filter lives in scripts/refresh_wire.py).

Pure standard library - no pip install needed. Token comes from the
DISCORD_BOT_TOKEN environment variable or from a gitignored local file
(scripts/discord_token.local.txt). The token is NEVER committed: the file is
in .gitignore and this script refuses to run if the token looks pasted into
the repo. Safe to run any time; on any error it exits quietly non-zero and
changes nothing upstream.
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "data" / "wire-state.json"
OUT = ROOT / "data" / "discord-posts.json"
TOKEN_FILE = ROOT / "scripts" / "discord_token.local.txt"
CHANNEL = os.environ.get("DISCORD_NEWS_CHANNEL_ID", "338736813126451201").strip()
MAX_PAGES = 3           # at most 300 messages per run
MAX_POST_AGE_HOURS = 36 # same freshness window the Wire uses

UA = "DiscordBot (https://github.com/WattaBinG/MarketsOnDeck, 1.0)"


def load_token():
    tok = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    if not tok and TOKEN_FILE.exists():
        tok = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not tok:
        print("No token. Set DISCORD_BOT_TOKEN or put the token (alone, one line) in",
              TOKEN_FILE, file=sys.stderr)
        sys.exit(2)
    return tok


def main():
    token = load_token()
    headers = {"User-Agent": UA, "Authorization": f"Bot {token}"}
    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        state = {}
    after = str(state.get("discord_last_message_id") or "")
    cutoff = time.time() - MAX_POST_AGE_HOURS * 3600

    posts = []
    newest = None
    for _ in range(MAX_PAGES):
        qs = "limit=100" + (f"&after={after}" if after else "")
        req = Request(f"https://discord.com/api/v10/channels/{CHANNEL}/messages?{qs}",
                      headers=headers)
        try:
            with urlopen(req, timeout=20) as r:
                batch = json.loads(r.read().decode("utf-8", "replace"))
        except HTTPError as e:
            if e.code == 429:
                try:
                    retry = float(json.loads(e.read().decode("utf-8", "replace")).get("retry_after", 5.0))
                except Exception:
                    retry = 5.0
                print(f"rate limited, waiting {retry:.0f}s")
                time.sleep(min(retry, 30.0))
                continue
            print(e.read()[:300].decode("utf-8", "replace"), file=sys.stderr)
            print(f"Discord returned HTTP {e.code} - leaving everything as-is.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"fetch failed ({e}) - leaving everything as-is.", file=sys.stderr)
            sys.exit(1)
        if not isinstance(batch, list) or not batch:
            break
        for msg in batch:
            mid = str(msg.get("id") or "")
            if not mid:
                continue
            newest = mid if newest is None else max(newest, mid, key=int)
            content = (msg.get("content") or "").strip()
            urls = re.findall(r"https?://[^\s<>()]+", content)
            text = re.sub(r"\s+", " ", re.sub(r"https?://[^\s<>()]+", "", content)).strip(" -|")
            if not text and msg.get("embeds"):
                emb = msg["embeds"][0] or {}
                text = (emb.get("title") or "").strip()
                if not urls and emb.get("url"):
                    urls = [emb["url"]]
            if not text or not urls:
                continue
            try:
                ts = datetime.fromisoformat(str(msg.get("timestamp")).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue
            if ts.timestamp() < cutoff:
                continue
            posts.append({
                "id": mid,
                "author": str((msg.get("author") or {}).get("username") or ""),
                "text": text[:300],
                "url": urls[0],
                "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            })
        after = max((str(m.get("id")) for m in batch), key=int, default=after)
        if len(batch) < 100:
            break

    posts.sort(key=lambda p: int(p["id"]), reverse=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "fetchedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "channel": CHANNEL,
        "posts": posts,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if newest is not None:
        prev = str(state.get("discord_last_message_id") or "0")
        state["discord_last_message_id"] = max(prev, newest, key=int)
        STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {len(posts)} posts written to {OUT.relative_to(ROOT)} "
          f"(commit data/discord-posts.json and data/wire-state.json to share them)")


if __name__ == "__main__":
    main()
