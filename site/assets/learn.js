(function(){
var $=function(i){return document.getElementById(i)};
var fmt=function(n){var s=Math.abs(n).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});return (n<0?'-$':'$')+s};
// glossary search
var q=$('glq');if(q){var items=[].slice.call(document.querySelectorAll('#gllist .gl-item')),c=$('glcount');
function f(){var v=q.value.trim().toLowerCase(),n=0;items.forEach(function(e){var t=e.textContent.toLowerCase(),show=!v||t.indexOf(v)>-1;e.hidden=!show;if(show)n++});c.textContent=v?(n+' of '+items.length+' terms'):items.length+' terms. Type to filter.'}
q.addEventListener('input',f);f()}
// position size
if($('ps-out')){var ids=['ps-acct','ps-risk','ps-entry','ps-stop'];
function ps(){var a=+$('ps-acct').value,r=+$('ps-risk').value,e=+$('ps-entry').value,s=+$('ps-stop').value,o=$('ps-out');
if(!(a>0&&r>0&&e>0&&s>0)){o.innerHTML='<p class="calc-warn">Enter positive numbers in every field.</p>';return}
var rps=Math.abs(e-s);if(rps===0){o.innerHTML='<p class="calc-warn">Entry and stop can\'t be the same price.</p>';return}
var dollars=a*r/100,sh=Math.floor(dollars/rps),val=sh*e,long=e>s;
o.innerHTML='<div><dt>Dollars at risk</dt><dd>'+fmt(dollars)+'</dd></div><div><dt>Risk per share</dt><dd>'+fmt(rps)+'</dd></div><div><dt>Shares</dt><dd>'+sh.toLocaleString()+'</dd></div><div><dt>Position value</dt><dd>'+fmt(val)+'</dd></div><div><dt>% of account</dt><dd>'+(val/a*100).toFixed(1)+'%</dd></div><div><dt>Direction</dt><dd>'+(long?'Long':'Short')+'</dd></div>'+(val>a?'<p class="calc-warn">This position is bigger than your account. It would need margin.</p>':'')}
ids.forEach(function(i){$(i).addEventListener('input',ps)});ps()}
// options P/L
if($('op-out')){var oi=['op-type','op-side','op-strike','op-prem','op-qty','op-px'];
function pl(px,t,sd,k,p,q){var intr=t==='call'?Math.max(px-k,0):Math.max(k-px,0);var v=(sd==='long'?intr-p:p-intr)*100*q;return v}
function op(){var t=$('op-type').value,sd=$('op-side').value,k=+$('op-strike').value,p=+$('op-prem').value,q=Math.max(1,Math.floor(+$('op-qty').value||1)),px=+$('op-px').value,o=$('op-out');
if(!(k>0&&p>=0&&px>=0)){o.innerHTML='<p class="calc-warn">Enter a strike, premium and stock price.</p>';return}
var v=pl(px,t,sd,k,p,q),be=t==='call'?k+p:k-p,cost=p*100*q,mx,ml;
if(sd==='long'){ml=cost;mx=t==='call'?'Unlimited':fmt((k-p)*100*q)}else{mx=cost;ml=t==='call'?'Unlimited':fmt((k-p)*100*q)}
o.innerHTML='<div><dt>Profit / loss</dt><dd class="'+(v>=0?'pos':'neg')+'">'+fmt(v)+'</dd></div><div><dt>Breakeven</dt><dd>'+fmt(be).replace('-','')+'</dd></div><div><dt>'+(sd==='long'?'Premium paid':'Premium received')+'</dt><dd>'+fmt(cost)+'</dd></div><div><dt>Max profit</dt><dd>'+(typeof mx==='string'?mx:fmt(mx))+'</dd></div><div><dt>Max loss</dt><dd>'+(typeof ml==='string'?ml:fmt(ml))+'</dd></div>';
var tb=document.querySelector('#op-table tbody'),rows='';for(var i=-5;i<=5;i++){var s=Math.max(0,k*(1+i*0.05)),r=pl(s,t,sd,k,p,q);rows+='<tr><td>'+fmt(s).replace('-','')+'</td><td class="'+(r>=0?'pos':'neg')+'">'+fmt(r)+'</td></tr>'}tb.innerHTML=rows}
oi.forEach(function(i){$(i).addEventListener('input',op)});op()}
})();
