#!/usr/bin/env python3
"""Build the next-trading-day calendar from maintained official sources.

BEA and BLS calendars are mandatory and fail closed. Census releases are read
from its official economic-indicators page. Federal Reserve meeting dates and
NYSE closures are explicit, reviewed data for the supported year; execution
fails outside that year rather than silently classifying a future date.
"""
import html, json, re, sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent.parent; OUT=ROOT/'site/assets/watch-today.json'; INDEX=ROOT/'site/index.html'
ET=ZoneInfo('America/New_York'); UA='MarketsOnDeck calendar bot (+https://marketsondeck.wattabing.workers.dev)'
SUPPORTED_YEAR=2026
HOLIDAYS={date(2026,1,1),date(2026,1,19),date(2026,2,16),date(2026,4,3),date(2026,5,25),date(2026,6,19),date(2026,7,3),date(2026,9,7),date(2026,11,26),date(2026,12,25)}
FOMC={date(2026,1,28),date(2026,3,18),date(2026,4,29),date(2026,6,17),date(2026,7,29),date(2026,9,16),date(2026,10,28),date(2026,12,9)}
SOURCES={
 'BEA':'https://www.bea.gov/news/schedule/ics/online-calendar-subscription.ics',
 'BLS':'https://www.bls.gov/schedule/news_release/bls.ics',
 'Census':'https://www.census.gov/economic-indicators/'
}
IMPORTANT=re.compile(r'consumer price|employment situation|producer price|retail sales|industrial production|gross domestic product|personal income|durable goods|new residential|housing starts',re.I)
def get(url):
 req=Request(url,headers={'User-Agent':UA,'Accept':'text/calendar,text/html;q=0.9,*/*;q=0.8'})
 with urlopen(req,timeout=25) as r: return r.read().decode('utf-8','replace')
def is_trading_day(d):
 if d.year!=SUPPORTED_YEAR: raise RuntimeError(f'unsupported trading-calendar year {d.year}; refusing to publish')
 return d.weekday()<5 and d not in HOLIDAYS
def next_trading_day(d):
 d+=timedelta(days=1)
 while not is_trading_day(d): d+=timedelta(days=1)
 return d
def parse_ics(text,target,important_only=False):
 text=text.replace('\r\n ','').replace('\r\n\t',''); out=[]
 for block in re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT',text,re.S):
  dm=re.search(r'DTSTART[^:]*:(\d{8})(?:T(\d{6})Z?)?',block); sm=re.search(r'SUMMARY[^:]*:(.+)',block)
  if not dm or not sm: continue
  d=datetime.strptime(dm.group(1),'%Y%m%d').date(); label=re.sub(r'\\([,;])',r'\1',sm.group(1)).strip()
  if d!=target or (important_only and not IMPORTANT.search(label)): continue
  if dm.group(2): t=datetime.strptime(dm.group(1)+dm.group(2),'%Y%m%d%H%M%S').replace(tzinfo=timezone.utc).astimezone(ET)
  else: t=datetime(target.year,target.month,target.day,8,30,tzinfo=ET)
  out.append((t.strftime('%-I:%M %p ET'),label))
 return out
def parse_census(text,target):
 # Official page exposes release cards with a month name, day, time, and title.
 plain=re.sub(r'<[^>]+>',' ',text); plain=html.unescape(re.sub(r'\s+',' ',plain))
 pat=re.compile(r'([A-Z][a-z]+)\s+(\d{1,2}),\s+(\d{4}).{0,100}?(\d{1,2}:\d{2}\s*[ap]\.m\.).{0,180}?((?:Retail Sales|Housing Starts|Industrial Production|Durable Goods|New Residential)[^|]{0,100})',re.I)
 out=[]
 for month,day,year,t,label in pat.findall(plain):
  try: d=datetime.strptime(f'{month} {day} {year}','%B %d %Y').date()
  except ValueError: continue
  if d==target: out.append((t.upper().replace('.','')+' ET',label.strip()))
 return out
def render(out):
 lis='\n'.join(f'          <li><span class="watch-time">{html.escape(e["time"])}</span><span class="watch-event">{html.escape(e["event"])}</span></li>' for e in out['events'])
 if not out['events'] and out.get('note'): lis=f'          <li><span class="watch-time">&mdash;</span><span class="watch-event">{html.escape(out["note"])}</span></li>'
 block=('<!-- WATCH_TODAY_START — updated once each morning by the Watch Today routine; keep this exact structure so the automated edit stays a clean find/replace -->\n'
 f'      <div class="watch-box" data-watch-date="{out["date"]}">\n        <div class="watch-box-header">What to Watch Today</div>\n'
 f'        <div class="watch-box-date">{html.escape(out["dateLabel"])}</div>\n        <ul class="watch-list">\n{lis}\n        </ul>\n'
 f'        <a class="watch-box-link" href="{html.escape(out["calendarUrl"],quote=True)}" target="_blank" rel="noopener">Full economic calendar &rarr;</a>\n      </div>\n      <!-- WATCH_TODAY_END -->')
 doc=INDEX.read_text(encoding='utf-8'); doc,n=re.subn(r'<!-- WATCH_TODAY_START.*?WATCH_TODAY_END -->',lambda m:block,doc,flags=re.S)
 if n!=1: raise RuntimeError(f'expected one WATCH_TODAY marker block, found {n}')
 INDEX.write_text(doc,encoding='utf-8')
def key(ev):
 m=re.match(r'(\d+):(\d+) (AM|PM)',ev[0]); return (int(m.group(1))%12+(12 if m.group(3)=='PM' else 0))*60+int(m.group(2))
def main():
 target=next_trading_day(datetime.now(ET).date()); events=[]
 failures=[]
 for name in ('BEA','BLS'):
  try: events+=parse_ics(get(SOURCES[name]),target,important_only=(name=='BLS'))
  except Exception as e: failures.append(f'{name}: {e}')
 if failures: raise RuntimeError('mandatory official calendar unavailable; preserving last good snapshot: '+'; '.join(failures))
 try: events+=parse_census(get(SOURCES['Census']),target)
 except Exception as e: raise RuntimeError(f'Census calendar unavailable; preserving last good snapshot: {e}')
 if target in FOMC: events.append(('2:00 PM ET','FOMC Rate Decision'))
 if any(target==d+timedelta(days=21) for d in FOMC): events.append(('2:00 PM ET','FOMC Minutes'))
 if target.weekday()==2: events.append(('10:30 AM ET','EIA Weekly Petroleum Status Report'))
 if target.weekday()==3: events += [('8:30 AM ET','Initial Jobless Claims'),('10:30 AM ET','EIA Weekly Natural Gas Storage Report')]
 if target.weekday()==4: events += [('1:00 PM ET','Baker Hughes Rig Count'),('3:30 PM ET','CFTC Commitments of Traders')]
 events=sorted(set(events),key=key)
 # Sources verified fine but the day is genuinely quiet: publish the correct
 # date with an honest empty state instead of leaving a stale date up.
 note=None if events else 'No major scheduled releases from tracked official sources (BEA, BLS, Census, Fed).'
 out={'date':target.isoformat(),'dateLabel':target.strftime('%A, %B ')+str(target.day),'events':[{'time':t,'event':e} for t,e in events],'note':note,'calendarUrl':'https://www.census.gov/economic-indicators/','sources':list(SOURCES.values())}
 OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); render(out)
 print('OK:',out['dateLabel'],len(events),'verified events'); print('COMMIT_MSG=Refresh What to Watch Today: '+out['dateLabel'])
if __name__=='__main__':
 try: main()
 except Exception as e: print(e,file=sys.stderr); sys.exit(1)
