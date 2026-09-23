#!/usr/bin/env python3
"""Check whether GameStock / Manifold joined; post a small pinned how-to in each
game channel for bots that are present (bot-authored, once)."""
import json
src = open("audit/discord_makeover.py").read().replace("\nmain()\n", "\n")
mk = {}; exec(compile(src, "mk", "exec"), mk)
api, G, LOG = mk["api"], mk["G"], mk["LOG"]
BOTS = {"GameStock": ("1533269447715066107", "1552227034128982036",
         "**📈 Stock Draft - how it works**\nWeekly stock-pick tournaments with GameStock. Play money, real prices.\n• `/tournaments` - see what's open\n• `/play` - lock in 2-4 picks before the draft closes\n• `/portfolio` - your live P&L\n• `/share` - post your result card\nFirst Deck Draft is coming soon. Winner gets bragging rights and a shoutout in announcements."),
        "Manifold": ("1074829857537663098", "1552227038172151918",
         "**🔮 Prediction Pit - how it works**\nPlay-money prediction markets from Manifold. Bet YES or NO with the reaction buttons on each market.\n• Link your free Manifold account the first time you bet (the bot walks you through it)\n• Weekly market questions land here: Fed, CPI, earnings, where SPY closes Friday\n• Running all-time leaderboard: the best forecaster on the Deck gets crowned")}
rep = {"integrations": [], "members": {}}
c, ints = api("GET", f"/guilds/{G}/integrations")
rep["integrations"] = [{"name": i.get("name"), "app": (i.get("application") or {}).get("id"), "enabled": i.get("enabled")} for i in (ints if isinstance(ints, list) else [])]
for name, (appid, ch, text) in BOTS.items():
    c, m = api("GET", f"/guilds/{G}/members/{appid}")
    app_in = any(i["app"] == appid for i in rep["integrations"])
    rep["members"][name] = {"member_status": c, "integration": app_in}
    if app_in or c == 200:
        c2, msgs = api("GET", f"/channels/{ch}/messages?limit=20")
        if isinstance(msgs, list) and not any("how it works" in (x.get("content") or "") for x in msgs):
            c3, p = api("POST", f"/channels/{ch}/messages", {"content": text, "allowed_mentions": {"parse": []}})
            if c3 < 300: api("PUT", f"/channels/{ch}/pins/{p['id']}")
        rep["members"][name]["recent"] = [(x["author"]["username"], (x.get("content") or "")[:100]) for x in (msgs if isinstance(msgs, list) else [])][:5]
rep["log"] = LOG
json.dump(rep, open("audit/report.json", "w"), indent=1)
print("checked")
