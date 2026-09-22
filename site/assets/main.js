// MarketsOnDeck — shared site JS. No frameworks, no build step.

// Theme toggle — light by default, dark is an explicit opt-in choice
// remembered in localStorage. Never driven by OS prefers-color-scheme.
// Runs immediately (not on DOMContentLoaded) so the dark preference applies
// before first paint and there's no flash of the wrong theme.
(function () {
  var STORAGE_KEY = 'mod-theme';
  try {
    if (localStorage.getItem(STORAGE_KEY) === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  } catch (e) {}
})();


// What to Watch Today: strike through events whose ET time has passed.
// Runs on the client clock against the box's data-watch-date, so the static
// nightly build needs no intraday regeneration. Future-dated boxes (evening
// build for tomorrow) show nothing passed; stale boxes are left untouched.
function markPassedWatchEvents() {
  var box = document.querySelector('.watch-box[data-watch-date]');
  if (!box) return;
  var et;
  try { et = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' })); }
  catch (e) { return; }
  var pad = function (n) { return String(n).padStart(2, '0'); };
  var today = et.getFullYear() + '-' + pad(et.getMonth() + 1) + '-' + pad(et.getDate());
  if (box.getAttribute('data-watch-date') !== today) return;
  var nowMin = et.getHours() * 60 + et.getMinutes();
  box.querySelectorAll('.watch-list li').forEach(function (li) {
    var span = li.querySelector('.watch-time');
    var m = span && span.textContent.trim().match(/^(\d{1,2}):(\d{2})\s*(AM|PM)/i);
    if (!m) return;
    var h = (+m[1]) % 12 + (/pm/i.test(m[3]) ? 12 : 0);
    if (h * 60 + (+m[2]) <= nowMin) li.classList.add('watch-passed');
  });
}
document.addEventListener('DOMContentLoaded', function () {
  markPassedWatchEvents();
  var navToggleBtn = document.getElementById('navToggle');
  var nav = document.getElementById('primaryNav');
  if (navToggleBtn && nav) {
    navToggleBtn.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      navToggleBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  var themeBtn = document.getElementById('themeToggle');
  if (themeBtn) {
    themeBtn.addEventListener('click', function () {
      var root = document.documentElement;
      var isDark = root.getAttribute('data-theme') === 'dark';
      if (isDark) {
        root.removeAttribute('data-theme');
      } else {
        root.setAttribute('data-theme', 'dark');
      }
      try { localStorage.setItem('mod-theme', isDark ? 'light' : 'dark'); } catch (e) {}
    });
  }

  initPinned();
  initTicker();
  initSentiment();
  initAiStrip();
  initShareBars();
  initScrollableTables();
  initHomeStats();
  initRecordBand();
  initOverviewCurve();
  initWireEnhance();
});

// Overview page's YTD/Month/Week stat row — computed live client-side from
// trades.json (the same source The Record itself reads), instead of numbers
// baked into the HTML once a day. Keeps the two pages' math identical by
// construction instead of duplicating a second copy of the summary logic.
function initHomeStats() {
  var row = document.getElementById('homeStats');
  if (!row) return;
  var tabs = document.getElementById('homeRangeTabs');
  var range = 'ytd';
  var trades = [];

  function cutoffDate(r) {
    if (!trades.length) return null;
    var newest = trades.reduce(function (max, t) { return t.date > max ? t.date : max; }, trades[0].date);
    if (r === 'day') return newest;
    var d = new Date(newest + 'T12:00:00Z');
    if (r === 'week') d.setUTCDate(d.getUTCDate() - 7);
    else if (r === 'month') d.setUTCDate(d.getUTCDate() - 30);
    else return null;
    return d.toISOString().slice(0, 10);
  }

  function render() {
    var cutoff = cutoffDate(range);
    var scoped = cutoff ? trades.filter(function (t) { return t.date >= cutoff; }) : trades;
    var totalGain = scoped.reduce(function (sum, t) { return sum + t.realizedGain; }, 0);
    var wins = scoped.filter(function (t) { return t.realizedGain > 0; }).length;
    var losses = scoped.filter(function (t) { return t.realizedGain < 0; }).length;
    var winRate = (wins + losses) ? (100 * wins / (wins + losses)) : 0;

    var pnlEl = document.getElementById('homeStatPnl');
    var sign = totalGain > 0 ? '+' : (totalGain < 0 ? '-' : '');
    pnlEl.textContent = sign + '$' + Math.abs(totalGain).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    pnlEl.classList.remove('gain', 'loss');
    pnlEl.classList.add(totalGain >= 0 ? 'gain' : 'loss');
    document.getElementById('homeStatWinRate').textContent = winRate.toFixed(1) + '%';
    document.getElementById('homeStatTrades').textContent = String(scoped.length);
    row.setAttribute('href', range === 'ytd' ? '/record/index.html' : '/record/index.html?range=' + range);
  }

  if (tabs) {
    tabs.querySelectorAll('.range-tab').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        range = btn.getAttribute('data-range');
        tabs.querySelectorAll('.range-tab').forEach(function (b) { b.classList.toggle('active', b === btn); });
        render();
      });
    });
  }

  fetch('/assets/trades.json', { cache: 'no-store' })
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (data) {
      if (!data || !data.trades) return;
      trades = data.trades;
      render();
    })
    .catch(function () {});
}

// Data tables (record table, episode stat tables) sit in a .table-scroll
// wrapper with overflow-x:auto but no visual cue that there's more to see —
// on a phone that meant the most important column (Realized P&L) was
// invisible off-screen with no hint it existed. Add a fade edge + a
// "swipe to see more" hint, but only when the table actually overflows.
function initScrollableTables() {
  document.querySelectorAll('.table-scroll').forEach(function (wrapper) {
    var table = wrapper.querySelector('table');
    if (!table) return;
    var check = function () {
      var overflowing = table.scrollWidth > wrapper.clientWidth + 1;
      wrapper.classList.toggle('has-overflow', overflowing);
      if (overflowing && !wrapper.previousElementSibling?.classList.contains('table-scroll-hint')) {
        var hint = document.createElement('div');
        hint.className = 'table-scroll-hint';
        hint.textContent = 'Swipe to see more →';
        wrapper.parentNode.insertBefore(hint, wrapper);
      } else if (!overflowing && wrapper.previousElementSibling?.classList.contains('table-scroll-hint')) {
        wrapper.previousElementSibling.remove();
      }
    };
    check();
    window.addEventListener('resize', check);
  });
}

// Share bar — populates the X/Facebook/LinkedIn intent links with the
// current page URL and a data-title attribute (so each page only needs to
// declare a title, not hand-encode share URLs), and wires the Copy Link
// button to the clipboard.
function initShareBars() {
  var bars = document.querySelectorAll('.share-bar');
  if (!bars.length) return;
  var url = encodeURIComponent(location.href);
  bars.forEach(function (bar) {
    var title = encodeURIComponent(bar.getAttribute('data-title') || document.title);
    var xLink = bar.querySelector('.share-x');
    var fbLink = bar.querySelector('.share-fb');
    var liLink = bar.querySelector('.share-li');
    if (xLink) xLink.href = 'https://twitter.com/intent/tweet?text=' + title + '&url=' + url;
    if (fbLink) fbLink.href = 'https://www.facebook.com/sharer/sharer.php?u=' + url;
    if (liLink) liLink.href = 'https://www.linkedin.com/sharing/share-offsite/?url=' + url;
    var copyBtn = bar.querySelector('.share-copy');
    if (copyBtn) {
      var defaultLabel = copyBtn.textContent;
      copyBtn.addEventListener('click', function () {
        var reset = function () {
          copyBtn.textContent = defaultLabel;
          copyBtn.classList.remove('copied');
        };
        var showCopied = function () {
          copyBtn.textContent = 'Copied!';
          copyBtn.classList.add('copied');
          setTimeout(reset, 1800);
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(location.href).then(showCopied, function () {});
        } else {
          try {
            var tmp = document.createElement('textarea');
            tmp.value = location.href;
            tmp.style.position = 'fixed';
            tmp.style.opacity = '0';
            document.body.appendChild(tmp);
            tmp.select();
            document.execCommand('copy');
            document.body.removeChild(tmp);
            showCopied();
          } catch (e) {}
        }
      });
    }
  });
}

// Note: the homepage hero stats and "Most Recent Closed Trades" cards used to
// be filled in by client-side JS reading trades.json. Moved to static HTML,
// baked in once daily by the Record Refresh routine (see the
// RECORD_STATS_START/RECENT_TRADES_START markers in index.html) instead —
// that removes the blank "—" flash on first paint and means link-preview
// bots and crawlers (which don't run JS) actually see the real numbers too.

// Fetches JSON with a couple of retries before giving up — mobile networks
// (cell tower handoffs, backgrounded-tab reconnects) throw a lot of one-off
// fetch failures that have nothing to do with the data actually being gone,
// and the ticker/pinned bar used to hide itself permanently on the very
// first blip. Retries a couple times with a short backoff before returning
// null, which is the only thing that should actually hide the bar.
function fetchJsonRetry(url, attempts) {
  attempts = attempts || 3;
  return fetch(url, { cache: 'no-store' })
    .then(function (res) { return res.ok ? res.json() : Promise.reject(new Error('bad status')); })
    .catch(function (err) {
      if (attempts <= 1) return null;
      return new Promise(function (resolve) { setTimeout(resolve, 1200); })
        .then(function () { return fetchJsonRetry(url, attempts - 1); });
    });
}

// Pinned bar — the standing set (SPY/QQQ/DIA from ticker.json's "pinned"
// list, plus BTC/ETH/SOL from crypto.json, which trades 24/7 on its own
// refresh schedule). Always visible on every screen size — CSS makes this
// row horizontally swipe-scrollable on narrow viewports instead of hiding
// it, which is what caused it to go missing on mobile before.
function initPinned() {
  var bar = document.getElementById('tickerPinned');
  if (!bar) return;

  Promise.all([
    fetchJsonRetry('/assets/ticker.json'),
    fetchJsonRetry('/assets/crypto.json')
  ]).then(function (results) {
    var tickerData = results[0], cryptoData = results[1];
    var pinnedSymbols = (tickerData && tickerData.pinned) || [];
    var pinnedItems = (tickerData && tickerData.items || []).filter(function (item) {
      return pinnedSymbols.indexOf(item.symbol) !== -1;
    });
    var cryptoItems = (cryptoData && cryptoData.items) || [];
    var allItems = pinnedItems.concat(cryptoItems);
    if (!allItems.length) { bar.hidden = true; return; }
    bar.hidden = false;
    var stockAsOfChip = (tickerData && tickerData.asOfLabel)
      ? '<span class="ticker-asof ticker-asof-pinned" title="Stock and ETF prices as of this time. Changes are versus the prior regular-session close. Periodic snapshots, not a live feed.">Stocks as of ' + escapeHtml(tickerData.asOfLabel) + '</span>'
      : '';
    var cryptoAsOfChip = (cryptoData && cryptoData.asOf)
      ? '<span class="ticker-asof ticker-asof-pinned" title="Crypto snapshot timestamp from its separate refresh job. Periodic snapshot, not a live feed.">Crypto as of ' + escapeHtml(timeAgoLabel(cryptoData.asOf)) + '</span>'
      : '<span class="ticker-asof ticker-asof-pinned">Crypto as-of unavailable</span>';
    bar.innerHTML = allItems.map(renderTickerItem).join('') + stockAsOfChip + cryptoAsOfChip;
  }).catch(function () { bar.hidden = true; });
}

// Rolling ticker strip — reads /assets/ticker.json (refreshed by a scheduled
// job) and renders a duplicated, seamlessly-looping row of today's top
// movers plus Keith's own held positions (flagged item.held, shown with a
// small dot). Excludes whatever's already in the pinned bar, so nothing
// shows up twice.
function initTicker() {
  var strip = document.getElementById('tickerStrip');
  if (!strip) return;
  var track = strip.querySelector('.ticker-track');
  if (!track) return;

  fetchJsonRetry('/assets/ticker.json')
    .then(function (data) {
      if (!data || !data.items || !data.items.length) { strip.hidden = true; return; }
      var pinnedSymbols = data.pinned || [];
      var scrollItems = data.items.filter(function (item) { return pinnedSymbols.indexOf(item.symbol) === -1; });
      if (!scrollItems.length) { strip.hidden = true; return; }
      strip.hidden = false;
      var asOfHtml = '<div class="ticker-asof" title="Change and % are versus the prior regular-session close. Periodic snapshots, not a live feed.">' + escapeHtml(data.asOfLabel || 'Updated') + '</div>';
      var itemsHtml = scrollItems.map(renderTickerItem).join('');
      // duplicate the row once so the CSS animation (-50%) loops seamlessly
      track.innerHTML = asOfHtml + itemsHtml + asOfHtml + itemsHtml;
    })
    .catch(function () { strip.hidden = true; });
}

var TICKER_CRYPTO_SYMBOLS = ['BTC', 'ETH', 'SOL'];

// Market Pulse dial (Keith 2026-09-22, fear-and-greed style, design delegated).
// Computed in the browser from the SAME benchmark snapshots the ticker strip
// shows - no external feed, no licensed data, always as honest as the strip's
// own as-of label. CNN's Fear & Greed endpoint blocks datacenter reads (418,
// probed today) and Stooq's CSV is dead, which is why this is self-sourced.
// Weighted daily moves across SPY/QQQ/DIA/IWM/USO + BTC/ETH/SOL, mapped to
// 0-100. Components with no price yet are dropped and the weights
// renormalized; fewer than three priced components hides the dial.
var SENTIMENT_WEIGHTS = { SPY: 0.25, QQQ: 0.20, DIA: 0.15, IWM: 0.10, USO: 0.05, BTC: 0.10, ETH: 0.10, SOL: 0.05 };

function sentimentZone(score) {
  if (score < 20) return ['Extreme Fear', '#c0392b'];
  if (score < 40) return ['Fear', '#e67e22'];
  if (score < 60) return ['Neutral', '#b8a00b'];
  if (score < 80) return ['Greed', '#6a9a23'];
  return ['Extreme Greed', '#1e8e3e'];
}

function initSentiment() {
  var card = document.getElementById('sentimentCard');
  if (!card) return;
  Promise.all([
    fetchJsonRetry('/assets/ticker.json'),
    fetchJsonRetry('/assets/crypto.json')
  ]).then(function (results) {
    var ticker = results[0] || {}, crypto = results[1] || {};
    var bySym = {};
    (ticker.items || []).forEach(function (i) { bySym[i.symbol] = i; });
    (crypto.items || []).forEach(function (i) { bySym[i.symbol] = i; });
    var num = 0, den = 0, used = 0;
    Object.keys(SENTIMENT_WEIGHTS).forEach(function (sym) {
      var it = bySym[sym];
      if (it && typeof it.changePercent === 'number') {
        num += SENTIMENT_WEIGHTS[sym] * it.changePercent;
        den += SENTIMENT_WEIGHTS[sym];
        used++;
      }
    });
    if (used < 3 || !den) { card.hidden = true; return; }
    var weighted = num / den;  // weighted average daily move, %
    var score = Math.max(0, Math.min(100, Math.round(50 + weighted * 20)));
    var zone = sentimentZone(score);
    // semicircular dial: arc red->green, needle at score
    var angle = -90 + (score / 100) * 180;  // -90 = far left, +90 = far right
    var rad = angle * Math.PI / 180;
    var nx = 60 + 46 * Math.sin(rad), ny = 62 - 46 * Math.cos(rad);
    document.getElementById('sentimentDial').innerHTML =
      '<svg viewBox="0 0 120 68" width="100%" aria-hidden="true">' +
      '<defs><linearGradient id="sgGrad" x1="0" y1="0" x2="1" y2="0">' +
      '<stop offset="0%" stop-color="#c0392b"/><stop offset="50%" stop-color="#b8a00b"/><stop offset="100%" stop-color="#1e8e3e"/>' +
      '</linearGradient></defs>' +
      '<path d="M 10 62 A 50 50 0 0 1 110 62" fill="none" stroke="url(#sgGrad)" stroke-width="9" stroke-linecap="round" opacity="0.85"/>' +
      '<line x1="60" y1="62" x2="' + nx.toFixed(1) + '" y2="' + ny.toFixed(1) + '" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>' +
      '<circle cx="60" cy="62" r="4" fill="currentColor"/></svg>';
    var scoreEl = document.getElementById('sentimentScore');
    scoreEl.textContent = score;
    scoreEl.style.color = zone[1];
    var labEl = document.getElementById('sentimentLabel');
    labEl.textContent = zone[0];
    labEl.style.color = zone[1];
    var asof = ticker.asOfLabel ? 'Stocks as of ' + ticker.asOfLabel : '';
    document.getElementById('sentimentNote').textContent =
      'Built from the daily moves of the strip\u2019s own benchmarks, weighted. ' +
      (asof ? asof + ' \u00b7 ' : '') + 'Snapshot, not a live feed.';
    card.hidden = false;
  }).catch(function () { card.hidden = true; });
}

// Top AI Tools strip - ranked by Apple's public US Top Free Apps chart
// (scripts/build_ai_strip.py, hourly in the wire workflow). Keith's config
// (data/ai-tools.json) picks the tracked tools and holds a referralUrl slot
// per tool; the site shows whatever the chart is actually doing, and a tool
// that drops off the chart drops off the strip. Outbound links only.
function initAiStrip() {
  var strip = document.getElementById('aiStrip');
  if (!strip) return;
  fetchJsonRetry('/assets/ai-tools.json')
    .then(function (data) {
      var items = (data && data.items) || [];
      if (!items.length) { strip.hidden = true; return; }
      var list = document.getElementById('aiStripList');
      var src = document.getElementById('aiStripSource');
      list.innerHTML = items.map(function (t) {
        return '<li><a class="ai-tool" href="' + encodeURI(t.url) + '" target="_blank" rel="noopener">' +
          '<span class="ai-tool-rank num">' + t.rank + '</span>' +
          '<span class="ai-tool-name">' + escapeHtml(t.name) + '</span></a></li>';
      }).join('');
      src.textContent = 'Ranked by the Apple App Store US Top Free chart' +
        (data.asOfLabel ? ' \u00b7 as of ' + data.asOfLabel : '') + ' \u00b7 snapshots, not a live feed';
      strip.hidden = false;
    })
    .catch(function () { strip.hidden = true; });
}

// Every ticker item (pinned bar and scrolling strip both) links out to a real
// quote page — Yahoo Finance's own symbol format needs "-USD" for crypto
// (BTC -> BTC-USD) but plain tickers work as-is for stocks/ETFs.
function tickerQuoteUrl(symbol) {
  var yahooSymbol = TICKER_CRYPTO_SYMBOLS.indexOf(symbol) !== -1 ? symbol + '-USD' : symbol;
  return 'https://finance.yahoo.com/quote/' + encodeURIComponent(yahooSymbol);
}

function renderTickerItem(item) {
  var dir = item.change > 0 ? 'gain' : (item.change < 0 ? 'loss' : '');
  var sign = item.change > 0 ? '+' : '';
  var price = typeof item.price === 'number' ? item.price.toFixed(2) : (item.price || '--');
  var pct = typeof item.changePercent === 'number' ? item.changePercent.toFixed(2) + '%' : '--';
  var symbolClass = 'ticker-symbol' + (item.held ? ' ticker-held' : '');
  return '<a class="ticker-item" href="' + tickerQuoteUrl(item.symbol) + '" target="_blank" rel="noopener">' +
    '<span class="' + symbolClass + '">' + escapeHtml(item.symbol) + '</span>' +
    '<span class="ticker-price num">' + price + '</span>' +
    '<span class="ticker-change num ' + dir + '">' + (pct === '--' ? pct : sign + pct) + '</span>' +
    '</a>';
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, function (c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
  });
}

// ---- First-release pass (2026-09-18) ----

// "2h ago"-style label from an ISO timestamp, for Wire freshness stamps.
function timeAgoLabel(iso) {
  var t = Date.parse(iso);
  if (isNaN(t)) return '';
  var diffMin = Math.floor((Date.now() - t) / 60000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return diffMin + 'm ago';
  var h = Math.floor(diffMin / 60);
  if (h < 24) return h + 'h ago';
  return Math.floor(h / 24) + 'd ago';
}

// Cumulative realized P&L series, oldest first — the same math The Record's
// chart uses, shared here so the homepage band and the Overview curve can
// never disagree with The Record.
function buildEquitySeries(trades) {
  var asc = trades.slice().sort(function (a, b) { return a.timestamp < b.timestamp ? -1 : 1; });
  var running = 0;
  return asc.map(function (t) { running += t.realizedGain; return { date: t.date, value: running }; });
}

// Compact self-contained SVG equity curve (no library). Zero line dashed;
// line and area tint follow the ending value, green above zero / red below.
function renderEquityCurve(el, trades, opts) {
  if (!el) return;
  opts = opts || {};
  var points = buildEquitySeries(trades);
  if (!points.length) return;
  var w = 640, h = opts.height || 150, padX = 8, padTop = 10, padBottom = 18;
  var values = points.map(function (p) { return p.value; });
  var minV = Math.min(0, Math.min.apply(null, values));
  var maxV = Math.max(0, Math.max.apply(null, values));
  var range = (maxV - minV) || 1;
  function x(i) { return padX + (i / (points.length - 1 || 1)) * (w - padX * 2); }
  function y(v) { return h - padBottom - ((v - minV) / range) * (h - padTop - padBottom); }
  var path = points.map(function (p, i) { return (i ? 'L' : 'M') + x(i).toFixed(1) + ',' + y(p.value).toFixed(1); }).join(' ');
  var zeroY = y(0).toFixed(1);
  var area = path + ' L' + x(points.length - 1).toFixed(1) + ',' + zeroY + ' L' + x(0).toFixed(1) + ',' + zeroY + ' Z';
  var last = points[points.length - 1].value;
  var color = last >= 0 ? 'var(--gain)' : 'var(--loss)';
  el.innerHTML =
    '<svg viewBox="0 0 ' + w + ' ' + h + '" width="100%" style="display:block; height:auto;">' +
    '<line x1="' + padX + '" y1="' + zeroY + '" x2="' + (w - padX) + '" y2="' + zeroY + '" stroke="var(--border-strong)" stroke-width="1" stroke-dasharray="4 4"/>' +
    '<path d="' + area + '" fill="' + color + '" opacity="0.12" stroke="none"/>' +
    '<path d="' + path + '" fill="none" stroke="' + color + '" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>' +
    '<text x="' + padX + '" y="' + (h - 4) + '" font-family="IBM Plex Mono, monospace" font-size="10" fill="var(--text-muted)">' + points[0].date + '</text>' +
    '<text x="' + (w - padX) + '" y="' + (h - 4) + '" font-family="IBM Plex Mono, monospace" font-size="10" fill="var(--text-muted)" text-anchor="end">' + points[points.length - 1].date + '</text>' +
    '</svg>';
}

// Homepage record band: the public scoreboard (net realized, win rate, trade
// count, S&P 500 over the same span) plus the equity curve, all computed
// live from trades.json. Stays hidden if the data can't load — the band is
// an enhancement, never a broken promise.
function initRecordBand() {
  var band = document.getElementById('recordBand');
  if (!band) return;
  fetchJsonRetry('/assets/trades.json').then(function (data) {
    if (!data || !data.trades || !data.trades.length) return;
    var trades = data.trades;
    var totalGain = 0, wins = 0, losses = 0;
    trades.forEach(function (t) {
      totalGain += t.realizedGain;
      if (t.realizedGain > 0) wins++;
      else if (t.realizedGain < 0) losses++;
    });
    var winRate = (wins + losses) ? (100 * wins / (wins + losses)) : 0;
    var pnlEl = document.getElementById('rbPnl');
    pnlEl.textContent = (totalGain >= 0 ? '+' : '-') + '$' + Math.abs(totalGain).toLocaleString(undefined, { maximumFractionDigits: 0 });
    pnlEl.classList.add(totalGain >= 0 ? 'gain' : 'loss');
    document.getElementById('rbWinRate').textContent = winRate.toFixed(1) + '%';
    document.getElementById('rbTrades').textContent = String(trades.length);
    var spy = (data.summary && data.summary.benchmark && typeof data.summary.benchmark.spyYtdPercent === 'number')
      ? data.summary.benchmark.spyYtdPercent : null;
    var spyEl = document.getElementById('rbSpy');
    if (spy !== null) {
      spyEl.textContent = (spy >= 0 ? '+' : '') + spy.toFixed(1) + '%';
      spyEl.classList.add(spy >= 0 ? 'gain' : 'loss');
    } else if (spyEl.parentNode) {
      spyEl.parentNode.style.display = 'none';
    }
    var asOf = document.getElementById('recordBandAsOf');
    if (asOf && data.summary && data.summary.asOf) asOf.textContent = 'Journal through ' + data.summary.asOf;
    renderEquityCurve(document.getElementById('recordBandChart'), trades, { height: 150 });
    band.hidden = false;
  }).catch(function () {});
}

// Overview page equity curve card — same renderer, larger canvas.
function initOverviewCurve() {
  var el = document.getElementById('overviewEquityCurve');
  if (!el) return;
  fetchJsonRetry('/assets/trades.json').then(function (data) {
    if (!data || !data.trades || !data.trades.length) return;
    renderEquityCurve(el, data.trades, { height: 220 });
  }).catch(function () {});
}

// The Wire, tightened: category filter buttons built from the tags actually
// on the page, per-headline freshness stamps and an "Updated" label matched
// from wire.json by URL (so the static, routine-managed list markup stays
// byte-for-byte compatible with the hourly Wire Refresh routine — this only
// enhances it in the browser).
function initWireEnhance() {
  var list = document.querySelector('.wire-list');
  var filters = document.getElementById('wireFilters');
  if (list && filters) {
    var cats = [];
    list.querySelectorAll('.wire-tag').forEach(function (tag) {
      var c = tag.textContent.trim();
      if (c && cats.indexOf(c) === -1) cats.push(c);
    });
    var buttons = [];
    function makeBtn(label) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'wire-filter-btn' + (label === 'All' ? ' active' : '');
      b.textContent = label;
      b.addEventListener('click', function () {
        buttons.forEach(function (x) { x.classList.toggle('active', x === b); });
        list.querySelectorAll('li').forEach(function (li) {
          var tag = li.querySelector('.wire-tag');
          li.style.display = (label === 'All' || (tag && tag.textContent.trim() === label)) ? '' : 'none';
        });
        swapTopStory(label);
      });
      filters.appendChild(b);
      buttons.push(b);
    }
    makeBtn('All');
    cats.forEach(makeBtn);
  }

  var wireData = null;
  var topA = document.querySelector('.wire-top[href]');

  // Per Keith (2026-09-22): each filter tab is its own front page. Swapping
  // tabs swaps the top story to that category's lead (the wire's scoring
  // already ordered the items), not just the list below. The lead's own
  // list entry hides so nothing shows twice.
  function swapTopStory(label) {
    if (!topA || !wireData) return;
    var lead, imgCat;
    if (label === 'All') {
      lead = wireData.topStory;
      imgCat = lead && lead.category;
    } else {
      lead = (wireData.topStory && wireData.topStory.category === label)
        ? wireData.topStory
        : (wireData.items || []).filter(function (it) { return it && it.category === label; })[0];
      imgCat = label;
    }
    if (!lead || !lead.url) return;
    topA.setAttribute('href', lead.url);
    var img = topA.querySelector('.wire-top-image');
    if (img && imgCat) img.setAttribute('src', '/assets/images/wire-' + imgCat.toLowerCase() + '.jpg');
    var lab = topA.querySelector('.wire-top-label');
    if (lab) lab.textContent = label === 'All' ? 'Top Story' : 'Top in ' + label;
    var head = topA.querySelector('.wire-top-headline');
    if (head) head.textContent = lead.headline || '';
    var src = topA.querySelector('.wire-top-source');
    if (src) src.textContent = lead.source || '';
    var topTime = topA.querySelector('.wire-top-time');
    if (topTime) {
      var stamp = lead.firstSeen || lead.timestamp;
      if (stamp) { topTime.textContent = timeAgoLabel(stamp); topTime.title = String(stamp).replace('T', ' ').replace('Z', ' UTC'); }
    }
    list.querySelectorAll('li').forEach(function (li) {
      var a = li.querySelector('a[href]');
      if (a && a.href === lead.url) li.style.display = 'none';
    });
  }

  fetchJsonRetry('/assets/wire.json').then(function (data) {
    if (!data) return;
    wireData = data;
    var updated = document.getElementById('wireUpdated');
    if (updated && data.asOfLabel) updated.textContent = 'Updated ' + data.asOfLabel;
    if (!list) return;
    var byUrl = {};
    (data.items || []).forEach(function (it) { if (it && it.url) byUrl[it.url] = it; });
    if (data.topStory && data.topStory.url) byUrl[data.topStory.url] = data.topStory;
    list.querySelectorAll('li').forEach(function (li) {
      var a = li.querySelector('a[href]');
      if (!a) return;
      var it = byUrl[a.href];
      var stamp = it && (it.firstSeen || it.timestamp);
      if (stamp) {
        var s = document.createElement('span');
        s.className = 'wire-time';
        s.textContent = timeAgoLabel(stamp);
        s.title = String(stamp).replace('T', ' ').replace('Z', ' UTC');
        li.appendChild(s);
      }
    });
    // Top story gets the same first-seen stamp: it keeps the time it first
    // posted to the Wire, even after holding the lead for hours.
    var topA = document.querySelector('.wire-top[href]');
    var topIt = topA && byUrl[topA.href];
    var topStamp = topIt && (topIt.firstSeen || topIt.timestamp);
    if (topStamp && !topA.querySelector('.wire-time')) {
      var st = document.createElement('span');
      st.className = 'wire-time wire-top-time';
      st.textContent = timeAgoLabel(topStamp);
      st.title = String(topStamp).replace('T', ' ').replace('Z', ' UTC');
      topA.appendChild(st);
    }
  }).catch(function () {});
}
