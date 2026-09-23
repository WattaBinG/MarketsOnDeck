#!/usr/bin/env python3
"""Retry community rules/updates channels with the features list included."""
import json
src = open("audit/discord_makeover.py").read().replace("\nmain()\n", "\n")
mk = {}; exec(compile(src, "mk", "exec"), mk)
api, G, LOG = mk["api"], mk["G"], mk["LOG"]
c, g = api("GET", f"/guilds/{G}")
c, r = api("PATCH", f"/guilds/{G}", {"features": g["features"], "rules_channel_id": "1481866548581761126",
                                      "public_updates_channel_id": "813649382179471370"})
out = {"status": c, "resp": {k: r.get(k) for k in ("rules_channel_id", "public_updates_channel_id")} if isinstance(r, dict) else r}
c, g2 = api("GET", f"/guilds/{G}")
out["after"] = {k: g2.get(k) for k in ("rules_channel_id", "public_updates_channel_id")}
out["log"] = LOG
json.dump(out, open("audit/report.json", "w"), indent=1)
print("done", c)
