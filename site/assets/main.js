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

document.addEventListener('DOMContentLoaded', function () {
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
  initShareBars();
  initScrollableTables();
  initHomeStats();
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

// Pinned bar — the standing set (SPY/QQQ/DIA from ticker.json's "pinned"
// list, plus BTC/ETH/SOL from crypto.json, which trades 24/7 on its own
// refresh schedule). Always visible on every screen size — CSS makes this
// row horizontally swipe-scrollable on narrow viewports instead of hiding
// it, which is what caused it to go missing on mobile before.
function initPinned() {
  var bar = document.getElementById('tickerPinned');
  if (!bar) return;

  Promise.all([
    fetch('/assets/ticker.json', { cache: 'no-store' }).then(function (res) { return res.ok ? res.json() : null; }).catch(function () { return null; }),
    fetch('/assets/crypto.json', { cache: 'no-store' }).then(function (res) { return res.ok ? res.json() : null; }).catch(function () { return null; })
  ]).then(function (results) {
    var tickerData = results[0], cryptoData = results[1];
    var pinnedSymbols = (tickerData && tickerData.pinned) || [];
    var pinnedItems = (tickerData && tickerData.items || []).filter(function (item) {
      return pinnedSymbols.indexOf(item.symbol) !== -1;
    });
    var cryptoItems = (cryptoData && cryptoData.items) || [];
    var allItems = pinnedItems.concat(cryptoItems);
    if (!allItems.length) { bar.hidden = true; return; }
    bar.innerHTML = allItems.map(renderTickerItem).join('');
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

  fetch('/assets/ticker.json', { cache: 'no-store' })
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (data) {
      if (!data || !data.items || !data.items.length) { strip.hidden = true; return; }
      var pinnedSymbols = data.pinned || [];
      var scrollItems = data.items.filter(function (item) { return pinnedSymbols.indexOf(item.symbol) === -1; });
      if (!scrollItems.length) { strip.hidden = true; return; }
      var asOfHtml = '<div class="ticker-asof">' + escapeHtml(data.asOfLabel || 'Updated') + '</div>';
      var itemsHtml = scrollItems.map(renderTickerItem).join('');
      // duplicate the row once so the CSS animation (-50%) loops seamlessly
      track.innerHTML = asOfHtml + itemsHtml + asOfHtml + itemsHtml;
    })
    .catch(function () { strip.hidden = true; });
}

var TICKER_CRYPTO_SYMBOLS = ['BTC', 'ETH', 'SOL'];

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
  var price = typeof item.price === 'number' ? item.price.toFixed(2) : item.price;
  var pct = typeof item.changePercent === 'number' ? item.changePercent.toFixed(2) : item.changePercent;
  var symbolClass = 'ticker-symbol' + (item.held ? ' ticker-held' : '');
  return '<a class="ticker-item" href="' + tickerQuoteUrl(item.symbol) + '" target="_blank" rel="noopener">' +
    '<span class="' + symbolClass + '">' + escapeHtml(item.symbol) + '</span>' +
    '<span class="ticker-price num">' + price + '</span>' +
    '<span class="ticker-change num ' + dir + '">' + sign + pct + '%</span>' +
    '</a>';
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, function (c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
  });
}
