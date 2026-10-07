#!/usr/bin/env python3
"""Generate dated display fields from the published ledger. Never writes ledger feeds."""
from pathlib import Path
from decimal import Decimal
import html,json,re
ROOT=Path(__file__).resolve().parents[1]
def money(n):return ('-' if n<0 else '+')+f'${abs(n):,.2f}'
def period(trades,start,end):
 rows=[t for t in trades if start<=t['date']<=end]
 gain=sum((Decimal(str(t['realizedGain'])) for t in rows),Decimal(0))
 wins=sum(t['realizedGain']>0 for t in rows);losses=sum(t['realizedGain']<0 for t in rows)
 return {'net':money(gain),'count':str(len(rows)),'winRate':f'{100*wins/(wins+losses) if wins+losses else 0:.2f}% ({wins}W / {losses}L)'}
def replace_block(s,key,value):
 pattern=r'<!-- '+key+r'_START -->.*?<!-- '+key+r'_END -->'
 if len(re.findall(pattern,s,re.S))!=1:raise ValueError('missing/duplicate '+key)
 return re.sub(pattern,lambda m:'<!-- '+key+'_START -->\n'+value+'\n<!-- '+key+'_END -->',s,flags=re.S)
def main():
 data=json.loads((ROOT/'site/assets/trades.json').read_text());trades=data['trades'];asof=html.escape(data['summary']['asOf'])
 for p in (ROOT/'site/episodes').glob('*.html'):
  s=p.read_text()
  pat=r'(<span data-ledger-start="([^"]+)" data-ledger-end="([^"]+)" data-ledger-metric="([^"]+)">).*?(</span>)'
  s=re.sub(pat,lambda m:m[1]+period(trades,m[2],m[3])[m[4]]+m[5],s)
  s=re.sub(r'<p class="ledger-version">.*?</p>','',s)
  s=s.replace('<h1','<p class="ledger-version data-freshness">Historical period totals from ledger through '+asof+'. Both accounts; not account return.</p>\n<h1',1)
  p.write_text(s)
 p=ROOT/'site/overview/index.html';s=p.read_text();cards=[]
 for acct in sorted(set(t['account'] for t in trades)):
  rows=[t for t in trades if t['account']==acct];r=period(rows,'0000','9999');name=html.escape(acct)
  cards.append(f'<a class="card" href="/record/?account={name}"><h3>{name}</h3><p>Closed-trade win rate (excluding flats): {r["winRate"]}</p><p>Net realized: {r["net"]} · {r["count"]} closes</p></a>')
 s=replace_block(s,'LEDGER_ACCOUNTS',f'<p class="data-freshness">Snapshot through {asof}. Win rate is not investment return.</p><div class="grid grid-2" id="ledgerAccounts">'+''.join(cards)+'</div>')
 recent=sorted(trades,key=lambda t:(t['date'],t.get('timestamp','')),reverse=True)[:3];cards=[]
 for t in recent:
  identity=t['symbol']
  if t['assetType']=='option':identity+=' '+str(t.get('strike','?'))+' '+t.get('optionType','option')+' · '+t.get('expiration','unknown expiration')
  cards.append('<div class="card"><span class="badge">'+html.escape(t['date'])+'</span><h3>'+html.escape(identity)+'</h3><p>'+html.escape(t['assetType'].title()+' · '+t['account'])+'</p><p>'+money(Decimal(str(t['realizedGain'])))+'</p></div>')
 s=replace_block(s,'LEDGER_RECENT',f'<p class="data-freshness">Ledger through {asof}; later closes may be missing.</p><div class="grid grid-3" id="ledgerRecent">'+''.join(cards)+'</div>');p.write_text(s)
if __name__=='__main__':main()
