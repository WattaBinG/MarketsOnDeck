import csv, io, re
from datetime import date

raw = open("D:/AI Projects/MarketsOnDeck/data/trade_journal_raw.txt", encoding="utf-8").read()

# Split into rows by the repeating date-date-days pattern is unreliable via naive split;
# instead find each trade row by regex on the leading "YYYY-MM-DD,YYYY-MM-DD,digits," pattern.
row_pattern = re.compile(r'(\d{4}-\d{2}-\d{2},\d{4}-\d{2}-\d{2},\d+,.*?)(?=\d{4}-\d{2}-\d{2},\d{4}-\d{2}-\d{2},\d+,|Summary Trade Ledger|$)')
rows = row_pattern.findall(raw)

trades = []
for r in rows:
    r = r.strip().rstrip(',')
    # naive CSV split respecting quotes
    reader = csv.reader(io.StringIO(r))
    fields = next(reader)
    if len(fields) < 15:
        continue
    opened, closed = fields[0], fields[1]
    try:
        pl = float(fields[13].replace('$','').replace(',','').replace('(','-').replace(')',''))
    except Exception:
        continue
    account = fields[15] if len(fields) > 15 else ''
    trades.append({"opened": opened, "closed": closed, "pl": pl, "account": account, "ticker": fields[3]})

print(f"Total parsed trades: {len(trades)}")

def in_range(d, start, end):
    return start <= d <= end

aug = [t for t in trades if in_range(t["closed"], "2026-08-01", "2026-08-28")]
jul14_aug28 = [t for t in trades if in_range(t["closed"], "2026-07-14", "2026-08-28")]

def summarize(name, subset):
    total = sum(t["pl"] for t in subset)
    wins = [t for t in subset if t["pl"] > 0]
    losses = [t for t in subset if t["pl"] < 0]
    print(f"\n=== {name} ===")
    print(f"Trades: {len(subset)}  Wins: {len(wins)}  Losses: {len(losses)}  Win rate: {len(wins)/len(subset)*100:.1f}%")
    print(f"Net P/L: ${total:,.2f}")
    if subset:
        best = max(subset, key=lambda t: t["pl"])
        worst = min(subset, key=lambda t: t["pl"])
        print(f"Best: {best['ticker']} ${best['pl']:,.2f} on {best['closed']}")
        print(f"Worst: {worst['ticker']} ${worst['pl']:,.2f} on {worst['closed']}")

summarize("August 1-28 (by close date)", aug)
summarize("July 14 - August 28 (by close date)", jul14_aug28)

# Account breakdown for August
trading_aug = [t for t in aug if t["account"] == "Trading"]
agentic_aug = [t for t in aug if t["account"] == "Agentic"]
print(f"\nAugust Trading-account-only net: ${sum(t['pl'] for t in trading_aug):,.2f} ({len(trading_aug)} trades)")
print(f"August Agentic-account-only net: ${sum(t['pl'] for t in agentic_aug):,.2f} ({len(agentic_aug)} trades)")
