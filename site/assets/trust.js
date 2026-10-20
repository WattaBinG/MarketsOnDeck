/* Dated snapshots, not live brokerage access. ET dates use Intl, including DST. */
(function (root) {
  'use strict';
  function etDate(now) {
    return new Intl.DateTimeFormat('en-CA', {timeZone:'America/New_York', year:'numeric', month:'2-digit', day:'2-digit'}).format(now || new Date());
  }
  function validDate(s) { return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s) && !isNaN(Date.parse(s+'T12:00:00Z')) && new Date(s+'T12:00:00Z').toISOString().slice(0,10)===s; }
  function datePart(s) {
    if (validDate(s)) return s;
    if(typeof s==='string' && /^\d{4}-\d{2}-\d{2}$/.test(s))return null;
    var d = new Date(s);
    return s && !isNaN(d) ? etDate(d) : null;
  }
  function staleDate(stamp, now) { var day=datePart(stamp); return !day || day < etDate(now); }
  function olderStockClose(stamp, now) {
    var today=etDate(now), h=+new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',hour:'numeric',hourCycle:'h23'}).format(now||new Date());
    var d=new Date(today+'T12:00:00Z');
    if (h<16) d.setUTCDate(d.getUTCDate()-1);
    while ([0,6].indexOf(d.getUTCDay())!==-1) d.setUTCDate(d.getUTCDate()-1);
    return !datePart(stamp) || datePart(stamp)<d.toISOString().slice(0,10);
  }
  function period(trades,start,end) {
    var rows=trades.filter(function(t){return t.date>=start && t.date<=end;});
    var cents=rows.reduce(function(n,t){return n+Math.round(t.realizedGain*100);},0);
    var wins=rows.filter(function(t){return t.realizedGain>0;}).length;
    var losses=rows.filter(function(t){return t.realizedGain<0;}).length;
    return {net:cents/100,count:rows.length,winRate:(wins+losses?100*wins/(wins+losses):0).toFixed(2)+'% ('+wins+'W / '+losses+'L)'};
  }
  function money(n) {return (n<0?'-':'+')+'$'+Math.abs(n).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});}
  var api={etDate:etDate,staleDate:staleDate,olderStockClose:olderStockClose,period:period,money:money,datePart:datePart};
  if (typeof module!=='undefined' && module.exports) module.exports=api;
  root.ModTrust=api;
  if (typeof document==='undefined') return;
  function readableStamp(stamp) {
    var d=new Date(stamp);
    if(!stamp || isNaN(d)) return 'unknown time';
    return new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}).format(d)+' ET';
  }
  function notice(anchor,key,text,stale) {
    if(!anchor) return;
    var n=document.getElementById(key);
    if(!n){n=document.createElement('p');n.id=key;n.className='data-freshness';anchor.insertAdjacentElement('afterend',n);}
    n.textContent=text;n.classList.toggle('data-stale',!!stale);n.setAttribute('role','status');
  }
  var feeds={};
  function load(path) { if(feeds[path])return feeds[path];return feeds[path]=fetch('/assets/'+path+'.json',{cache:'no-store'}).then(function(r){if(!r.ok)throw Error(path);return r.json();}); }
  function datedModules() {
    var today=etDate();
    var earn=document.querySelector('.earn-box[data-earn-date]');
    if(earn) load('earnings').then(function(d){
      var day=new Date(today+'T12:00:00Z'), fri=new Date(day);
      fri.setUTCDate(fri.getUTCDate()+(5-day.getUTCDay()+7)%7);
      var end=fri.toISOString().slice(0,10), rows=(d.today||[]).concat(d.weekAhead||[]);
      var nowRows=rows.filter(function(r){return r.date===today;}), later=rows.filter(function(r){return r.date>today && r.date<=end;});
      var fallback='';
      if(!nowRows.length&&!later.length){var future=rows.filter(function(r){return r.date>today;}).sort(function(a,b){return a.date.localeCompare(b.date);});if(future.length){var next=future[0].date;later=future.filter(function(r){return r.date===next;});fallback='No major earnings this week. Next scheduled: '+next;}else{fallback='No major earnings listed this week. Next schedule update pending.';}}
      earn.dataset.earnDate=today;earn.classList.remove('data-stale');
      function link(r){return '<a class="earn-ticker" target="_blank" rel="noopener" href="'+escape(r.link)+'">'+escape(r.ticker)+'</a>';}
      earn.innerHTML='<div class="earn-box-header">Earnings Today</div><div class="earn-box-date">'+escape(day.toLocaleDateString('en-US',{timeZone:'UTC',weekday:'long',month:'long',day:'numeric'}))+'</div><ul class="earn-list">'+nowRows.map(function(r){return '<li><span class="earn-slot">'+escape(r.slot||'TBD')+'</span><span class="earn-id">'+link(r)+'<span class="earn-name">'+escape(r.company)+'</span></span><span class="earn-eps">Est: '+(r.epsEst==null?'TBD':'$'+Number(r.epsEst).toFixed(2))+'</span></li>';}).join('')+'</ul>'+(later.length?'<div class="earn-week"><div class="earn-week-header">Coming up</div><ul class="earn-week-list">'+later.map(function(r){return '<li><span class="earn-week-day">'+escape(r.dayLabel)+'</span>'+link(r)+'<span class="earn-slot">'+escape(r.slot||'TBD')+'</span></li>';}).join('')+'</ul></div>':'')+'<div class="legend">BMO = Before Market Open · AMC = After Market Close · EPS = earnings per share<br>Schedule snapshot: '+escape(d.date)+'</div>';
      window.dispatchEvent(new Event('resize'));
      if(fallback)earn.querySelector('.earn-box-date').textContent=fallback;
    }).catch(function(){earn.querySelector('.earn-box-header').textContent='Earnings Schedule Snapshot';});
    var watch=document.querySelector('.watch-box[data-watch-date]');
    if(watch){var day=watch.dataset.watchDate;notice(watch,'watchFreshness','Economic schedule: '+day+(day<today?' - older schedule, not today.':day>today?' - upcoming schedule.':''),day<today);if(day<today)watch.querySelector('.watch-box-header').textContent='Economic Schedule Snapshot';}
  }
  function escape(s){return String(s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  function refresh() {
    datedModules();
    var title=document.querySelector('main h1');
    if(document.getElementById('recordTbody') || document.getElementById('homeStats') || document.getElementById('recordBand') || document.querySelector('[data-ledger-start]')) {
      load('trades').then(function(d){
        var stamp=d.summary && d.summary.asOf;
        var recent=document.getElementById('ledgerRecent');
        if(recent)recent.innerHTML=d.trades.slice().sort(function(a,b){return (b.date+(b.timestamp||'')).localeCompare(a.date+(a.timestamp||''));}).slice(0,3).map(function(t){var identity=t.symbol;if(t.assetType==='option')identity+=' '+(t.strike||'?')+' '+(t.optionType||'option')+' · '+(t.expiration||'unknown expiration');return '<div class="card"><span class="badge">'+escape(t.date)+'</span><h3>'+escape(identity)+'</h3><p>'+escape(t.assetType+' · '+t.account)+'</p><p>'+money(t.realizedGain)+'</p></div>';}).join('');
        var accounts=document.getElementById('ledgerAccounts');
        if(accounts)accounts.innerHTML=Array.from(new Set(d.trades.map(function(t){return t.account;}))).sort().map(function(a){var p=period(d.trades.filter(function(t){return t.account===a;}),'0000','9999');return '<div class="card"><h3>'+escape(a)+'</h3><p>Closed-trade win rate (excluding flats): '+p.winRate+'</p><p>Net realized: '+money(p.net)+' · '+p.count+' closes</p></div>';}).join('');
        var anchor=document.getElementById('recordBandAsOf') || title;
        notice(anchor,'ledgerFreshness','Ledger through '+(stamp||'unknown date')+'.'+(olderStockClose(stamp)?' Historical snapshot: later trades may be missing.':''),olderStockClose(stamp));
        document.querySelectorAll('[data-ledger-start]').forEach(function(n){var p=period(d.trades,n.dataset.ledgerStart,n.dataset.ledgerEnd);n.textContent=n.dataset.ledgerMetric==='net'?money(p.net):String(p[n.dataset.ledgerMetric]);});
      }).catch(function(){notice(title || document.getElementById('recordBand'),'ledgerFreshness','Ledger freshness unavailable. Do not treat these figures as current.',true);});
    }
    var pos=document.getElementById('positionsStats');
    if(pos) load('positions').then(function(d){var expired=(d.positions||[]).some(function(p){return p.expiration && p.expiration<etDate();});notice(pos,'positionsFreshness','Positions and marks as recorded: '+(d.asOf||'unknown date')+'. Not verified current holdings.'+(expired?' Snapshot includes contracts whose expiration date has passed; outcomes are not reconciled here.':''),staleDate(d.asOf)||expired);}).catch(function(){notice(pos,'positionsFreshness','Positions snapshot freshness unavailable.',true);});
    var ticker=document.getElementById('tickerStrip') || document.getElementById('tickerPinned');
    if(ticker) {
      var ti=document.getElementById('tickerInfo');
      load('ticker').then(function(d){if(ti)ti.textContent='Quotes are delayed snapshots, not live (stock snapshot: '+readableStamp(d.asOf)+'). Held flags reflect the published positions snapshot, not verified current holdings.';}).catch(function(){if(ti)ti.textContent='Quotes are delayed snapshots, not live.';});
      load('crypto').then(function(d){var tic=document.getElementById('tickerInfoCrypto');if(tic)tic.textContent='Crypto quotes: snapshot as of '+readableStamp(d.asOf)+', not live.';}).catch(function(){});
    }
    var pulse=document.getElementById('sentimentDate');
    if(pulse)load('sentiment-history').then(function(d){var rows=Array.isArray(d)?d:(d.history||d.entries||[]);var last=rows[rows.length-1];if(last)notice(pulse,'pulseFreshness','Trend score history through '+last.date+'. Not a live market sentiment measure.',olderStockClose(last.date));}).catch(function(){notice(pulse,'pulseFreshness','Trend history date unavailable.',true);});
    var wire=document.getElementById('wireUpdated');
    if(wire)load('wire').then(function(d){var age=Date.now()-Date.parse(d.asOf);notice(wire,'wireFreshness','News feed updated: '+readableStamp(d.asOf)+(age>3600000||!isFinite(age)?' - older snapshot.':'.'),age>3600000||!isFinite(age));}).catch(function(){notice(wire,'wireFreshness','News feed freshness unavailable.',true);});
  }
  document.addEventListener('DOMContentLoaded',function(){refresh();setInterval(refresh,60000);});
})(typeof window!=='undefined'?window:globalThis);
