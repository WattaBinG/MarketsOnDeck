#!/usr/bin/env python3
"""Follow-up to the approved makeover: move channels one at a time (Discord
allows one parent change per bulk call), retry community channel settings."""
import json, sys
sys.argv = ["x"]
import importlib.util
spec = importlib.util.spec_from_file_location("mk", "audit/discord_makeover.py")
src = open("audit/discord_makeover.py").read().replace("\nmain()\n", "\n")
mk = {}; exec(compile(src, "mk", "exec"), mk)
api, G, CAT, EXIST, LOG = mk["api"], mk["G"], mk["CAT"], mk["EXIST"], mk["LOG"]
NEW = {"announcements": ("1552223543012626462", "start", 1), "earnings-and-ratings": ("1552223546376192030", "wire", 1),
       "chart-alerts": ("1552223550071373854", "wire", 2), "ticker-lab": ("1552223553657507880", "wire", 3),
       "the-record": ("1552223557277450321", "floor", 1), "charts-and-ideas": ("1552223560678768740", "floor", 2)}
rep = {}
order = ["start", "wire", "floor", "live", "fun", "admin"]
api("PATCH", f"/guilds/{G}/channels", [{"id": CAT[k], "position": i} for i, k in enumerate(order)])
items = [(cid, cat, pos) for cid, (_, cat, pos, _) in EXIST.items()] + list(NEW.values())
for cid, cat, pos in items:
    api("PATCH", f"/guilds/{G}/channels", [{"id": cid, "parent_id": CAT[cat], "position": pos, "lock_permissions": False}])
c, g = api("PATCH", f"/guilds/{G}", {"rules_channel_id": "1481866548581761126", "public_updates_channel_id": "813649382179471370"})
rep["guild_patch_resp"] = {k: g.get(k) for k in ("rules_channel_id", "public_updates_channel_id", "description")} if isinstance(g, dict) else g
rep["after_channels"] = api("GET", f"/guilds/{G}/channels")[1]
c, g2 = api("GET", f"/guilds/{G}")
rep["after_guild"] = {k: g2.get(k) for k in ("rules_channel_id", "public_updates_channel_id", "system_channel_id", "description")}
rep["log"] = LOG
json.dump(rep, open("audit/report.json", "w"), indent=1)
print(f"ops: {len(LOG)}, failed: {len([l for l in LOG if l['status'] >= 300])}")
