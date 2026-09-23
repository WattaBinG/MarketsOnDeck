#!/usr/bin/env python3
"""Approved: GAME ROOM category. Adds game channels (bots join later via Keith's
invite taps), updates topics and the bot's pinned welcome post. Idempotent."""
import json
src = open("audit/discord_makeover.py").read().replace("\nmain()\n", "\n")
mk = {}; exec(compile(src, "mk", "exec"), mk)
api, G, LOG, SITE = mk["api"], mk["G"], mk["LOG"], mk["SITE"]
CAT = "1481877185185845318"
api("PATCH", f"/channels/{CAT}", {"name": "🎮 GAME ROOM"})
c, chans = api("GET", f"/guilds/{G}/channels"); byname = {x["name"]: x["id"] for x in chans}
PLAN = [  # name, existing id or None, topic
 ("stock-draft", None, "📈 Weekly stock-pick tournament (GameStock). /tournaments to see what's open, /play to lock in 2-4 picks at real prices, /portfolio for your P&L. Play money, real prices."),
 ("prediction-pit", None, "🔮 Play-money prediction markets (Manifold). Will SPY close green Friday? Is CPI hot? Bet with the reaction buttons, climb the all-time leaderboard."),
 ("casino-24-7", "988917279108526080", "🎰 24/7 Casino: /slots, /blackjack and more. Fake money, real bragging rights."),
 ("work-and-earn", None, "💼 Dank Memer economy: /work list to pick a job, /work apply, then /work shift every ~45 min. /daily, /beg, /market to trade items. Miss shifts and you get fired."),
 ("level-ups", None, "⭐ MEE6 level-ups land here. Chat anywhere to earn XP. /rank to see yours. Regular unlocks at level 5, SuperStonks at 15."),
 ("sports-scores", "1424038460565487679", None),
]
ids = {}
for name, cid, topic in PLAN:
    cid = cid or byname.get(name)
    if not cid:
        c, ch = api("POST", f"/guilds/{G}/channels", {"name": name, "type": 0, "parent_id": CAT, "topic": topic})
        cid = ch["id"] if c < 300 else None
    elif topic:
        api("PATCH", f"/channels/{cid}", {"topic": topic})
    ids[name] = cid
for pos, (name, _, _) in enumerate(PLAN):
    if ids.get(name):
        api("PATCH", f"/guilds/{G}/channels", [{"id": ids[name], "parent_id": CAT, "position": pos, "lock_permissions": False}])
# level-ups: read-only for people (bot announcements)
if ids.get("level-ups"):
    api("PUT", f"/channels/{ids['level-ups']}/permissions/{G}", {"type": 0, "allow": "0", "deny": str(1 << 11)})
# edit the bot's own pinned welcome post: casino line -> game room line
WID, MID = "1481866548581761126", "1552223621756354660"
c, m = api("GET", f"/channels/{WID}/messages/{MID}")
if c == 200 and "stock-draft" not in m["content"]:
    old = "🎰 <#988917279108526080> - kill time, stack fake money"
    new = (f"🎮 <#{ids['stock-draft']}> <#{ids['prediction-pit']}> <#988917279108526080> <#{ids['work-and-earn']}> - "
           "stock tournaments, prediction markets, casino, work-for-coins")
    if old in m["content"]:
        api("PATCH", f"/channels/{WID}/messages/{MID}", {"content": m["content"].replace(old, new), "allowed_mentions": {"parse": []}})
rep = {"ids": ids, "after_channels": api("GET", f"/guilds/{G}/channels")[1], "log": LOG}
json.dump(rep, open("audit/report.json", "w"), indent=1)
print(f"ops: {len(LOG)}, failed: {len([l for l in LOG if l['status'] >= 300])}")
