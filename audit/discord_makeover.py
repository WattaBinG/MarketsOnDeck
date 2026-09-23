#!/usr/bin/env python3
"""One-time server makeover approved by Keith (temporary branch, never merged).
Renames/moves existing channels (IDs, webhooks, invites keep working), adds a few
channels, removes only webhooks that duplicate another follow of the SAME source
channel into the SAME destination, rewrites descriptions/welcome screen, recolors
human roles. Idempotent. Writes audit/report.json (encrypted by the workflow)."""
import json, os, sys, time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
UA = "DiscordBot (https://github.com/WattaBinG/MarketsOnDeck, 1.0)"
TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
G = "338736813126451201"
SITE = "https://marketsondeck.wattabing.workers.dev"
LOG = []
def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    for _ in range(6):
        req = Request("https://discord.com/api/v10" + path, data=data, method=method,
                      headers={"User-Agent": UA, "Authorization": f"Bot {TOKEN}", "Content-Type": "application/json",
                               "X-Audit-Log-Reason": "MarketsOnDeck makeover approved by Keith"})
        try:
            with urlopen(req, timeout=25) as r:
                raw = r.read().decode("utf-8", "replace")
                out = (r.status, json.loads(raw) if raw else None)
                break
        except HTTPError as e:
            raw = e.read().decode("utf-8", "replace")[:500]
            if e.code == 429:
                try: time.sleep(min(float(json.loads(raw).get("retry_after", 2)) + 0.3, 30))
                except Exception: time.sleep(3)
                continue
            out = (e.code, raw); break
    else:
        out = (429, "rate limited")
    if method != "GET":
        LOG.append({"op": f"{method} {path}", "status": out[0], "err": None if out[0] < 300 else out[1]})
        time.sleep(0.6)
    return out

EVERYONE = G
SEND, THREADS_SEND, REACT, CREATE_PUB_THREADS = 1 << 11, 1 << 38, 1 << 6, 1 << 35
TOP_DAWG = "818655560458567760"
read_only = [{"id": EVERYONE, "type": 0, "allow": "0", "deny": str(SEND | CREATE_PUB_THREADS)}]
record_ow = [{"id": EVERYONE, "type": 0, "allow": str(THREADS_SEND | REACT), "deny": str(SEND)},
             {"id": TOP_DAWG, "type": 0, "allow": str(SEND), "deny": "0"}]

CAT = {"start": "1481866340170993725", "wire": "1481868775258062878", "floor": "1424038459286356039",
       "live": "1481879579256688681", "fun": "1481877185185845318", "admin": "1481880130761527317"}
CAT_NAMES = {"start": "📌 START HERE", "wire": "📰 THE WIRE", "floor": "💬 TRADING FLOOR",
             "live": "🎙️ LIVE", "fun": "🎰 OFF THE CLOCK", "admin": "🛠️ ADMIN"}
EXIST = {  # id: (new name or None, category, position, topic or None)
 "1481866548581761126": ("welcome", "start", 0, "👋 Start here: what's where, the rules, and links to the site. Read this first."),
 "338736813126451201": ("wire-headlines", "wire", 0, "📰 Market headlines as they hit, 24/7 (FinancialJuice, OpenBB, Unusual Whales). Feeds only - talk about it in #market-talk."),
 "1481866631012552724": ("market-talk", "floor", 0, "💬 Talk markets with people, not bots. Tickers, macro, what you're watching today. Keep bot commands in #ticker-lab."),
 "813650796214353931": ("stream-chat", "live", 0, "🔴 Chat during live streams and live sessions."),
 "988914657022578748": ("youtube-live", "live", 1, "📺 New videos, stream links and replays."),
 "818652638345560066": (None, "live", 2, None),
 "849472692310114324": (None, "live", 3, None),
 "988917279108526080": ("casino-24-7", "fun", 0, "🎰 Kill time and stack fake money: /slots and /blackjack with 24/7 Casino, /work, /beg and /daily with Dank Memer. Top the leaderboard, flex responsibly."),
 "1424038460565487679": ("sports-scores", "fun", 1, "🏒 Scores and game alerts (NHLBot and friends). Sports live here so the market channels stay clean."),
 "813649382179471370": (None, "admin", 0, None),
}
NEW = [  # name, type, category, position, topic, overwrites
 ("announcements", 5, "start", 1, "📣 Site updates, new Morning Briefs and Record posts. Follow this channel to get it in your own server.", read_only),
 ("earnings-and-ratings", 0, "wire", 1, "📅 Earnings, economic calendar, upgrades and downgrades (Walter Bloomberg feeds).", read_only),
 ("chart-alerts", 0, "wire", 2, "🚀 Markets On Deck TradingView alerts: price levels hit, as they fire.", read_only),
 ("ticker-lab", 0, "wire", 3, "🧪 Bot commands live here. Type / and pick Alpha.bot, OpenBB, StockBot or unusual_whales_crier for charts, quotes, flow and alerts.", None),
 ("the-record", 0, "floor", 1, f"🧾 Keith's trades as they happen, wins and losses. Reply in threads. Full history: {SITE}/record/", record_ow),
 ("charts-and-ideas", 0, "floor", 2, "📊 Post a chart, a setup or a thesis. Say why, not just what.", None),
]
WELCOME = f"""**Welcome to Markets On Deck** 📈

Live market headlines, chart alerts, and one trader's public record - losses included.

**Where to go**
📰 <#WIRE> - headlines as they hit, 24/7
📅 <#EARN> - earnings, calendar, upgrades and downgrades
🚀 <#ALERTS> - TradingView alerts
🧪 <#LAB> - charts and quotes: type / and pick a bot
💬 <#TALK> - talk markets with people, not bots
🧾 <#RECORD> - Keith's trades, wins and losses
🎰 <#CASINO> - kill time, stack fake money

**House rules**
1. Be decent. No harassment, hate or spam.
2. Nothing here is financial advice. Do your own homework.
3. No pump-and-dumps, paid signals or referral spam.
4. Bot commands go in <#LAB>, sports in <#SPORTS>.

Site: {SITE}/"""

def main():
    if not TOKEN: print("no token"); sys.exit(1)
    c, _ = api("GET", "/users/@me")
    if c != 200: print("TOKEN STATUS: FAILED", c); sys.exit(1)
    rep = {}
    c, chans = api("GET", f"/guilds/{G}/channels"); rep["before_channels"] = chans
    byname = {ch["name"]: ch["id"] for ch in chans}
    # 1) categories
    for k, cid in CAT.items():
        api("PATCH", f"/channels/{cid}", {"name": CAT_NAMES[k]})
    # 2) existing channels: rename + topic
    for cid, (name, cat, pos, topic) in EXIST.items():
        body = {}
        if name: body["name"] = name
        if topic: body["topic"] = topic
        if body: api("PATCH", f"/channels/{cid}", body)
    # 3) new channels (skip if already there)
    ids = {}
    for name, typ, cat, pos, topic, ow in NEW:
        if name in byname:
            ids[name] = byname[name]; continue
        body = {"name": name, "type": typ, "parent_id": CAT[cat], "topic": topic}
        if ow: body["permission_overwrites"] = ow
        c, ch = api("POST", f"/guilds/{G}/channels", body)
        if c < 300: ids[name] = ch["id"]
    rep["new_ids"] = ids
    # 4) positions (categories then children)
    order = ["start", "wire", "floor", "live", "fun", "admin"]
    moves = [{"id": CAT[k], "position": i} for i, k in enumerate(order)]
    for cid, (_, cat, pos, _) in EXIST.items():
        moves.append({"id": cid, "parent_id": CAT[cat], "position": pos, "lock_permissions": False})
    for name, typ, cat, pos, topic, ow in NEW:
        if name in ids: moves.append({"id": ids[name], "parent_id": CAT[cat], "position": pos, "lock_permissions": False})
    api("PATCH", f"/guilds/{G}/channels", moves)
    # 5) webhooks: remove true duplicates, move feeds
    c, wh = api("GET", f"/guilds/{G}/webhooks")
    wh = wh if isinstance(wh, list) else []
    rep["webhooks_before"] = [{"id": w["id"], "name": w.get("name"), "type": w["type"], "channel_id": w["channel_id"],
                               "src": (w.get("source_channel") or {}).get("id")} for w in wh]
    groups = {}
    for w in wh:
        src = (w.get("source_channel") or {}).get("id")
        if w["type"] == 2 and src:
            groups.setdefault((src, w["channel_id"]), []).append(w)
    keep_wb = []
    for (src, dest), ws in groups.items():
        ws.sort(key=lambda w: int(w["id"]))
        keep = ws[-1]  # newest follow of this source survives
        if (keep.get("source_guild") or {}).get("id") == "708365137660215327":
            keep_wb.append(keep["id"])
        for w in ws[:-1]:
            api("DELETE", f"/webhooks/{w['id']}")
    if "earnings-and-ratings" in ids:
        for wid in keep_wb:
            api("PATCH", f"/webhooks/{wid}", {"channel_id": ids["earnings-and-ratings"]})
    if "chart-alerts" in ids:
        for w in wh:
            if w.get("name") == "TV ALERT Bot" and w["type"] == 1:
                api("PATCH", f"/webhooks/{w['id']}", {"channel_id": ids["chart-alerts"]})
    # 6) guild settings
    api("PATCH", f"/guilds/{G}", {
        "description": "Live market headlines, chart alerts, and one trader's public record - losses included. Talk markets, then kill time in the casino.",
        "rules_channel_id": "1481866548581761126",
        "public_updates_channel_id": "813649382179471370"})
    # 7) welcome screen
    wc = [{"channel_id": "1481866548581761126", "description": "Start here: what's where and the rules", "emoji_name": "👋"},
          {"channel_id": "338736813126451201", "description": "Market headlines as they hit, 24/7", "emoji_name": "📰"},
          {"channel_id": "1481866631012552724", "description": "Talk markets with people, not bots", "emoji_name": "💬"}]
    if "the-record" in ids: wc.append({"channel_id": ids["the-record"], "description": "Keith's trades, wins and losses", "emoji_name": "🧾"})
    wc.append({"channel_id": "988917279108526080", "description": "Kill time: casino, work, get paid", "emoji_name": "🎰"})
    api("PATCH", f"/guilds/{G}/welcome-screen", {"enabled": True,
        "description": "Market headlines, live alerts and a public trading record. Grab a seat.", "welcome_channels": wc})
    # 8) human role colors (site palette)
    for rid, color in (("818655560458567760", 0xF5B700), ("857468805119082537", 0x7C8BE0),
                       ("818654579762659338", 0x34D07A), ("866223855253454919", 0x9AA3B7)):
        api("PATCH", f"/guilds/{G}/roles/{rid}", {"color": color})
    # 9) welcome post (once)
    c, msgs = api("GET", "/channels/1481866548581761126/messages?limit=20")
    rep["welcome_msgs_before"] = [{"id": m["id"], "author": m["author"]["username"], "content": m.get("content"),
                                   "embeds": len(m.get("embeds") or [])} for m in (msgs if isinstance(msgs, list) else [])]
    if not any("House rules" in (m.get("content") or "") for m in (msgs if isinstance(msgs, list) else [])) and len(ids) == len(NEW):
        text = (WELCOME.replace("#WIRE", "#338736813126451201").replace("#EARN", "#" + ids["earnings-and-ratings"])
                .replace("#ALERTS", "#" + ids["chart-alerts"]).replace("#LAB", "#" + ids["ticker-lab"])
                .replace("#TALK", "#1481866631012552724").replace("#RECORD", "#" + ids["the-record"])
                .replace("#CASINO", "#988917279108526080").replace("#SPORTS", "#1424038460565487679"))
        c, m = api("POST", "/channels/1481866548581761126/messages", {"content": text, "allowed_mentions": {"parse": []}})
        if c < 300: api("PUT", f"/channels/1481866548581761126/pins/{m['id']}")
    # after-state
    rep["after_channels"] = api("GET", f"/guilds/{G}/channels")[1]
    rep["after_webhooks"] = [{"id": w["id"], "name": w.get("name"), "channel_id": w["channel_id"]} for w in (api("GET", f"/guilds/{G}/webhooks")[1] or [])]
    rep["after_guild"] = {k: v for k, v in (api("GET", f"/guilds/{G}")[1] or {}).items() if k in ("description", "rules_channel_id", "public_updates_channel_id")}
    rep["after_welcome"] = api("GET", f"/guilds/{G}/welcome-screen")[1]
    rep["log"] = LOG
    json.dump(rep, open("audit/report.json", "w"), indent=1)
    bad = [l for l in LOG if l["status"] >= 300]
    print(f"ops: {len(LOG)}, failed: {len(bad)}")
main()
