#!/usr/bin/env python3
"""Approved polish: upload brand emojis (skip existing names) and add two
AutoMod safety rules (slur preset, suspected spam) if not present."""
import json, base64, os
src = open("audit/discord_makeover.py").read().replace("\nmain()\n", "\n")
mk = {}; exec(compile(src, "mk", "exec"), mk)
api, G, LOG = mk["api"], mk["G"], mk["LOG"]
c, have = api("GET", f"/guilds/{G}/emojis"); names = {e["name"] for e in (have if isinstance(have, list) else [])}
for fn in sorted(os.listdir("audit/emoji")):
    n = fn[:-4]
    if n in names: continue
    data = base64.b64encode(open(f"audit/emoji/{fn}", "rb").read()).decode()
    api("POST", f"/guilds/{G}/emojis", {"name": n, "image": f"data:image/png;base64,{data}"})
c, rules = api("GET", f"/guilds/{G}/auto-moderation/rules")
types = {r["trigger_type"] for r in (rules if isinstance(rules, list) else [])}
block = [{"type": 1, "metadata": {"custom_message": "Blocked by Markets On Deck AutoMod."}}]
if 4 not in types:
    api("POST", f"/guilds/{G}/auto-moderation/rules", {"name": "Block slurs", "event_type": 1, "trigger_type": 4,
        "trigger_metadata": {"presets": [3]}, "actions": block, "enabled": True})
if 3 not in types:
    api("POST", f"/guilds/{G}/auto-moderation/rules", {"name": "Block suspected spam", "event_type": 1, "trigger_type": 3,
        "actions": [{"type": 1}], "enabled": True})
rep = {"emojis_after": [e["name"] + ":" + e["id"] for e in (api("GET", f"/guilds/{G}/emojis")[1] or [])],
       "automod_after": [(r["name"], r["trigger_type"], r["enabled"]) for r in (api("GET", f"/guilds/{G}/auto-moderation/rules")[1] or [])],
       "log": LOG}
json.dump(rep, open("audit/report.json", "w"), indent=1)
print("done")
