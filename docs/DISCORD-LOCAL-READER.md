# Discord Local Reader (runs on Keith's PC)

Discord refuses datacenter IPs (GitHub Actions, cloud browsers) on channel
reads: HTTP 403 "internal network error". From a home connection the same
read works fine - proven September 21, 2026. So the Discord leg of The Wire
runs in two pieces, same pattern as trades.json:

- **Local (this script, on Keith's PC):** fetches new posts from the news
  channel and commits them to the repo as `data/discord-posts.json`. It is a
  dumb fetcher - no filtering, no formatting.
- **Cloud (the hourly Action):** merges that file into The Wire. All
  filtering (sports drop, market-relevance keep) lives in
  `scripts/refresh_wire.py`, so there is exactly one filter to maintain.

## One-time setup

1. Have Python 3 installed (check: open a terminal, `python --version`).
2. Give the script the bot token, one of two ways:
   - **File (easiest):** create `scripts/discord_token.local.txt` containing
     ONLY the token, one line. This file is in `.gitignore` - it will never
     be committed, and it stays on this PC only.
   - **Environment variable:** set `DISCORD_BOT_TOKEN` in Windows user
     environment variables.
3. Never paste the token into any other file, chat, or doc. If it ever leaks
   (screenshot, commit), reset it in the Discord developer portal and update
   the file.

## Run it

From the repo folder:

```
python scripts/discord_local_reader.py
```

It writes `data/discord-posts.json` and updates `data/wire-state.json`
(remembers the last post it saw, so nothing repeats). Then share the posts
with the cloud:

```
git add data/discord-posts.json data/wire-state.json
git commit -m "Discord posts (local reader)"
git push
```

The next hourly Action picks them up. The script is safe to run any time -
on error it says what failed and changes nothing upstream.

## If Claude Desktop runs it for you

Paste this into the routine or chat:

> Run `python scripts/discord_local_reader.py` in the MarketsOnDeck repo
> folder. If it prints OK, git-add `data/discord-posts.json` and
> `data/wire-state.json`, commit as "Discord posts (local reader)", and
> push. If it errors, show me the error and stop. Never show me or anyone
> the bot token.

Optional later: Windows Task Scheduler can run the fetch+commit every hour
while the PC is on. Not required - running it a few times a day is fine;
posts stay fresh for 36 hours.

## Details

- Channel: `338736813126451201` (default; override with env
  `DISCORD_NEWS_CHANNEL_ID`).
- Output shape: `{fetchedAt, channel, posts: [{id, author, text, url,
  timestamp}]}`.
- The Action merges up to 15 kept items per run, after filtering
  (sports-score language dropped, non-market chatter dropped).
- The repo secret `DISCORD_BOT_TOKEN` / variable `DISCORD_NEWS_CHANNEL_ID`
  still exist so the REST path works automatically if Discord ever unblocks
  datacenter IPs. Until then the local reader is the feed.
