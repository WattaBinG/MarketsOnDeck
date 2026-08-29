import csv

trades = []
with open("trade_journal_raw.txt", encoding="utf-8") as f:
    reader = csv.reader(f)
    for fields in reader:
        if len(fields) < 16:
            continue
        opened, closed = fields[0], fields[1]
        try:
            pl = float(fields[13].replace('$', '').replace(',', '').replace('(', '-').replace(')', ''))
        except Exception:
            continue
        trades.append({"opened": opened, "closed": closed, "pl": pl, "account": fields[15], "ticker": fields[3]})

print("Total parsed trades:", len(trades))

def summarize(name, subset):
    total = sum(t["pl"] for t in subset)
    wins = [t for t in subset if t["pl"] > 0]
    losses = [t for t in subset if t["pl"] < 0]
    print("")
    print("===", name, "===")
    if subset:
        print("Trades:", len(subset), " Wins:", len(wins), " Losses:", len(losses),
              " Win rate: {:.1f}%".format(len(wins) / len(subset) * 100))
    print("Net P/L: ${:,.2f}".format(total))

aug = [t for t in trades if "2026-08-01" <= t["closed"] <= "2026-08-28"]
jul14_aug28 = [t for t in trades if "2026-07-14" <= t["closed"] <= "2026-08-28"]

summarize("August 1-28 (by close date)", aug)
summarize("July 14 - August 28 (by close date)", jul14_aug28)

trading_aug = [t for t in aug if t["account"] == "Trading"]
agentic_aug = [t for t in aug if t["account"] == "Agentic"]
print("")
print("August Trading-only: ${:,.2f} ({} trades)".format(sum(t['pl'] for t in trading_aug), len(trading_aug)))
print("August Agentic-only: ${:,.2f} ({} trades)".format(sum(t['pl'] for t in agentic_aug), len(agentic_aug)))
