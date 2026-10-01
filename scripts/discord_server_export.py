#!/usr/bin/env python3
"""Read-only Discord server structure export.

Runs in GitHub Actions with DISCORD_BOT_TOKEN from repo secrets.
Fetches the bot's guilds and each guild's channels/roles, and writes
them to discord-export/server-map.json for the server-cleanup review.

Read-only: only GET requests. Never prints or logs the token.
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = "https://discord.com/api/v10"

TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
if not TOKEN:
    sys.exit("DISCORD_BOT_TOKEN is not set")


def api(path):
    req = urllib.request.Request(
        BASE + path,
        headers={
            "Authorization": "Bot " + TOKEN,
            "User-Agent": "MarketsOnDeck-server-export (read-only)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        sys.exit(f"Discord API error on {path}: HTTP {exc.code}: {body[:200]}")


bot = api("/users/@me")
guilds = api("/users/@me/guilds")

result = {
    "exported_by": bot.get("username"),
    "bot_id": bot.get("id"),
    "guilds": [],
}
for g in guilds:
    gid = g["id"]
    channels = api(f"/guilds/{gid}/channels")
    roles = api(f"/guilds/{gid}/roles")
    result["guilds"].append(
        {
            "id": gid,
            "name": g.get("name"),
            "icon": g.get("icon"),
            "channels": channels,
            "roles": [
                {
                    "id": r.get("id"),
                    "name": r.get("name"),
                    "permissions": r.get("permissions"),
                }
                for r in roles
            ],
        }
    )

os.makedirs("discord-export", exist_ok=True)
with open("discord-export/server-map.json", "w") as f:
    json.dump(result, f, indent=2)
print(f"exported {len(guilds)} guild(s) to discord-export/server-map.json")
