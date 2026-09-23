#!/usr/bin/env python3
"""Read-only Discord server audit (temporary review branch, never merged).
Only GET requests. The full report is written to audit/report.json, which the
workflow encrypts before upload because this repo's logs are public. The log
prints only token status and counts - no names, no webhook URLs, no token."""
import json, os, sys, time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

UA = "DiscordBot (https://github.com/WattaBinG/MarketsOnDeck, 1.0)"
TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
NEWS = os.environ.get("DISCORD_NEWS_CHANNEL_ID", "338736813126451201").strip() or "338736813126451201"

def get(path):
    for _ in range(3):
        req = Request("https://discord.com/api/v10" + path,
                      headers={"User-Agent": UA, "Authorization": f"Bot {TOKEN}"})
        try:
            with urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read().decode("utf-8", "replace"))
        except HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            if e.code == 429:
                try: time.sleep(min(float(json.loads(body).get("retry_after", 2)), 10))
                except Exception: time.sleep(2)
                continue
            try: body = json.loads(body)
            except Exception: pass
            return e.code, body
    return 429, "rate limited"

def main():
    if not TOKEN:
        print("TOKEN STATUS: missing (secret empty)"); sys.exit(1)
    code, me = get("/users/@me")
    if code != 200:
        print(f"TOKEN STATUS: FAILED HTTP {code} {me if code != 401 else '(401 = stale or wrong token)'}")
        sys.exit(1)
    print("TOKEN STATUS: OK (token is valid)")
    rep = {"bot": {k: me.get(k) for k in ("id", "username", "global_name", "bot")}}
    _, app = get("/applications/@me")
    if isinstance(app, dict):
        rep["application"] = {k: app.get(k) for k in ("name", "description", "flags", "bot_public", "approximate_guild_count")}
    _, guilds = get("/users/@me/guilds?with_counts=true")
    rep["guilds"] = []
    for g in guilds if isinstance(guilds, list) else []:
        gid = g["id"]; G = {"summary": g}
        c, full = get(f"/guilds/{gid}?with_counts=true")
        if c == 200:
            G["guild"] = {k: full.get(k) for k in ("id", "name", "description", "icon", "banner", "splash",
                "owner_id", "verification_level", "explicit_content_filter", "default_message_notifications",
                "features", "premium_tier", "premium_subscription_count", "system_channel_id",
                "rules_channel_id", "public_updates_channel_id", "approximate_member_count",
                "approximate_presence_count", "vanity_url_code", "preferred_locale")}
            G["emojis"] = [e.get("name") for e in full.get("emojis", [])]
            G["stickers"] = [s.get("name") for s in full.get("stickers", [])]
        for key, path in (("roles", f"/guilds/{gid}/roles"), ("channels", f"/guilds/{gid}/channels"),
                          ("bot_member", f"/guilds/{gid}/members/{me['id']}"),
                          ("members", f"/guilds/{gid}/members?limit=1000"),
                          ("webhooks", f"/guilds/{gid}/webhooks"),
                          ("integrations", f"/guilds/{gid}/integrations"),
                          ("invites", f"/guilds/{gid}/invites"),
                          ("scheduled_events", f"/guilds/{gid}/scheduled-events"),
                          ("automod", f"/guilds/{gid}/auto-moderation/rules"),
                          ("onboarding", f"/guilds/{gid}/onboarding"),
                          ("welcome_screen", f"/guilds/{gid}/welcome-screen")):
            c, d = get(path)
            if key == "webhooks" and isinstance(d, list):
                d = [{k: w.get(k) for k in ("id", "name", "type", "channel_id")} |
                     {"creator": (w.get("user") or {}).get("username"),
                      "source": (w.get("source_guild") or {}).get("name") or (w.get("source_channel") or {}).get("name")}
                     for w in d]  # never keep webhook tokens/URLs
            if key == "invites" and isinstance(d, list):
                d = [{"channel": (i.get("channel") or {}).get("name"), "uses": i.get("uses"),
                      "max_age": i.get("max_age"), "inviter": (i.get("inviter") or {}).get("username")} for i in d]
            if key == "members" and isinstance(d, list):
                d = [{"username": (m.get("user") or {}).get("username"), "bot": (m.get("user") or {}).get("bot", False),
                      "nick": m.get("nick"), "roles": m.get("roles"), "joined_at": m.get("joined_at")} for m in d]
            G[key] = d if c == 200 else {"error": c, "body": d}
        # News channel: recent-message read test + author mix (last 100)
        if any(isinstance(ch, dict) and ch.get("id") == NEWS for ch in (G.get("channels") or [])):
            c, msgs = get(f"/channels/{NEWS}/messages?limit=100")
            if c == 200:
                authors = {}
                for m in msgs:
                    a = (m.get("author") or {}).get("username", "?")
                    authors[a] = authors.get(a, 0) + 1
                G["news_channel_test"] = {"read": "OK", "count": len(msgs), "authors": authors,
                    "samples": [((m.get("author") or {}).get("username"), (m.get("content") or
                                 ((m.get("embeds") or [{}])[0].get("title") or ""))[:120]) for m in msgs[:40]]}
            else:
                G["news_channel_test"] = {"read": "FAILED", "error": c, "body": msgs}
        rep["guilds"].append(G)
        print(f"guild: {len(G.get('channels') or [])} channels, {len(G.get('roles') or [])} roles, "
              f"news read: {(G.get('news_channel_test') or {}).get('read', 'n/a')}")
    json.dump(rep, open("audit/report.json", "w"), indent=1, default=str)

if __name__ == "__main__":
    main()
