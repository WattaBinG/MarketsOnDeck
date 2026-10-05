#!/usr/bin/env python3
"""Read-only Discord server structure export.

Runs in GitHub Actions with DISCORD_BOT_TOKEN from repo secrets.
Fetches the bot's guilds and each guild's channels/roles, trims the
payload to the minimum needed for the cleanup review, and writes
discord-export/server-map.json. The workflow encrypts it before upload.

Read-only: only GET requests. Never prints or logs the token, and never
prints names of guilds that are filtered out (workflow logs are public).

Trimmed out:
  - channel permission_overwrites
  - role permission bitfields
  - any guild that is not the MarketsOnDeck server
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = "https://discord.com/api/v10"


def get_token():
    token = os.environ.get("DISCORD_BOT_TOKEN", "")
    if not token:
        sys.exit("DISCORD_BOT_TOKEN is not set")
    return token


def api(path):
    req = urllib.request.Request(
        BASE + path,
        headers={
            "Authorization": "Bot " + get_token(),
            "User-Agent": "MarketsOnDeck-server-export (read-only)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        sys.exit(f"Discord API error on {path}: HTTP {exc.code}: {body[:200]}")


def is_our_guild(guild):
    return "markets" in (guild.get("name") or "").lower()


def trim_channel(channel):
    return {
        "id": channel.get("id"),
        "name": channel.get("name"),
        "type": channel.get("type"),
        "parent_id": channel.get("parent_id"),
        "position": channel.get("position"),
        "topic": channel.get("topic"),
    }


def trim_role(role):
    return {
        "id": role.get("id"),
        "name": role.get("name"),
    }


def build_export(bot, guilds, fetch):
    """Assemble the trimmed export. `fetch(guild_id)` returns (channels, roles)."""
    result = {
        "exported_by": bot.get("username"),
        "bot_id": bot.get("id"),
        "guilds": [],
    }
    skipped = 0
    for g in guilds:
        if not is_our_guild(g):
            skipped += 1
            continue
        channels, roles = fetch(g["id"])
        result["guilds"].append(
            {
                "id": g["id"],
                "name": g.get("name"),
                "channels": [trim_channel(c) for c in channels],
                "roles": [trim_role(r) for r in roles],
            }
        )
    return result, skipped


def main():
    bot = api("/users/@me")
    guilds = api("/users/@me/guilds")

    def fetch(gid):
        return api(f"/guilds/{gid}/channels"), api(f"/guilds/{gid}/roles")

    result, skipped = build_export(bot, guilds, fetch)

    os.makedirs("discord-export", exist_ok=True)
    with open("discord-export/server-map.json", "w") as f:
        json.dump(result, f, indent=2)
    print(
        f"exported {len(result['guilds'])} guild(s), "
        f"skipped {skipped} non-MarketsOnDeck guild(s)"
    )


if __name__ == "__main__":
    main()
