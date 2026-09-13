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

  initTicker();
  initCrypto();
  initHomeStats();
});

// Homepage hero stat row — reads /assets/trades.json's summary block (the
// same data source The Record page browses in full) so the headline numbers
// never drift out of sync with what a visitor finds when they click through.
function initHomeStats() {
  var pnlEl = document.getElementById('homeStatPnl');
  if (!pnlEl) return;

  fetch('/assets/trades.json', { cache: 'no-store' })
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (data) {
      if (!data || !data.summary) return;
      var s = data.summary;
      var sign = s.totalRealizedGain >= 0 ? '+' : '-';
      pnlEl.textContent = sign + '$' + Math.abs(s.totalRealizedGain).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      pnlEl.classList.add(s.totalRealizedGain >= 0 ? 'gain' : 'loss');
      document.getElementById('homeStatWinRate').textContent = s.winRate.toFixed(1) + '%';
      document.getElementById('homeStatTrades').textContent = String(s.totalTrades);
    })
    .catch(function () {});
}

// Rolling ticker strip — reads /assets/ticker.json (refreshed by a scheduled
// job a few times a day) and renders a duplicated, seamlessly-looping row.
function initTicker() {
  var strip = document.getElementById('tickerStrip');
  if (!strip) return;
  var track = strip.querySelector('.ticker-track');
  if (!track) return;

  fetch('/assets/ticker.json', { cache: 'no-store' })
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (data) {
      if (!data || !data.items || !data.items.length) { strip.hidden = true; return; }
      var asOfHtml = '<div class="ticker-asof">' + escapeHtml(data.asOfLabel || 'Updated') + '</div>';
      var itemsHtml = data.items.map(renderTickerItem).join('');
      // duplicate the row once so the CSS animation (-50%) loops seamlessly
      track.innerHTML = asOfHtml + itemsHtml + asOfHtml + itemsHtml;
    })
    .catch(function () { strip.hidden = true; });
}

// Static crypto corner box — reads /assets/crypto.json (refreshed every 30
// minutes, 7 days a week, separate from the stock ticker's market-hours-only
// schedule since crypto never closes). Deliberately does not scroll.
function initCrypto() {
  var box = document.getElementById('tickerCrypto');
  if (!box) return;

  fetch('/assets/crypto.json', { cache: 'no-store' })
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (data) {
      if (!data || !data.items || !data.items.length) { box.hidden = true; return; }
      box.innerHTML = data.items.map(renderTickerItem).join('');
    })
    .catch(function () { box.hidden = true; });
}

function renderTickerItem(item) {
  var dir = item.change > 0 ? 'gain' : (item.change < 0 ? 'loss' : '');
  var sign = item.change > 0 ? '+' : '';
  var price = typeof item.price === 'number' ? item.price.toFixed(2) : item.price;
  var pct = typeof item.changePercent === 'number' ? item.changePercent.toFixed(2) : item.changePercent;
  return '<div class="ticker-item">' +
    '<span class="ticker-symbol">' + escapeHtml(item.symbol) + '</span>' +
    '<span class="ticker-price num">' + price + '</span>' +
    '<span class="ticker-change num ' + dir + '">' + sign + pct + '%</span>' +
    '</div>';
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, function (c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
  });
}
