#!/usr/bin/env python3
"""Read-only probe (temporary branch): webhook source channels and which
webhooks actually post, so only true duplicates get removed. GET only.
Writes audit/report.json (encrypted by the workflow)."""
import json, os, sys, time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
UA = "DiscordBot (https://github.com/WattaBinG/MarketsOnDeck, 1.0)"
TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
GID = "338736813126451201"
def get(path):
    for _ in range(5):
        req = Request("https://discord.com/api/v10" + path, headers={"User-Agent": UA, "Authorization": f"Bot {TOKEN}"})
        try:
            with urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read().decode("utf-8", "replace"))
        except HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            if e.code == 429:
                try: time.sleep(min(float(json.loads(body).get("retry_after", 2)), 10))
                except Exception: time.sleep(2)
                continue
            return e.code, body
    return 429, None
def scan(ch, pages):
    out = {}; before = ""; n = 0; oldest = None
    for _ in range(pages):
        c, b = get(f"/channels/{ch}/messages?limit=100" + (f"&before={before}" if before else ""))
        if c != 200 or not b: break
        for m in b:
            n += 1
            key = m.get("webhook_id") or ("bot:" + (m.get("author") or {}).get("username", "?"))
            d = out.setdefault(key, {"count": 0, "last": None, "names": {}})
            d["count"] += 1
            d["last"] = max(d["last"] or "", m.get("timestamp") or "")
            nm = (m.get("author") or {}).get("username", "?"); d["names"][nm] = d["names"].get(nm, 0) + 1
            if len(d.setdefault("samples", [])) < 2:
                d["samples"].append(((m.get("content") or "") or ((m.get("embeds") or [{}])[0].get("title") or ""))[:120])
            oldest = m.get("timestamp")
        before = b[-1]["id"]
        if len(b) < 100: break
    return {"scanned": n, "oldest": oldest, "by_source": out}
def main():
    c, me = get("/users/@me")
    if c != 200: print("TOKEN STATUS: FAILED", c); sys.exit(1)
    print("TOKEN STATUS: OK")
    rep = {}
    c, wh = get(f"/guilds/{GID}/webhooks")
    rep["webhooks"] = [{k: w.get(k) for k in ("id", "name", "type", "channel_id", "application_id")} |
        {"src_ch": (w.get("source_channel") or {}).get("id"), "src_ch_name": (w.get("source_channel") or {}).get("name"),
         "src_guild": (w.get("source_guild") or {}).get("id")} for w in (wh if isinstance(wh, list) else [])]
    rep["scan"] = {ch: scan(ch, p) for ch, p in (("338736813126451201", 20), ("813650796214353931", 3),
                   ("1424038460565487679", 3), ("988917279108526080", 2), ("1481866631012552724", 3), ("1481866548581761126", 1))}
    json.dump(rep, open("audit/report.json", "w"), indent=1)
    print("webhooks:", len(rep["webhooks"]), "scanned:", {k: v["scanned"] for k, v in rep["scan"].items()})
main()
