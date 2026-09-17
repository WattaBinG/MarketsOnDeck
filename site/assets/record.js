// MarketsOnDeck — The Record: sortable/filterable trade log + cumulative P&L chart.
// No frameworks, no build step — same discipline as the rest of the site.
document.addEventListener('DOMContentLoaded', function () {
  var tbody = document.getElementById('recordTbody');
  if (!tbody) return;

  var state = { trades: [], summary: null, sortKey: 'date', sortDir: 'desc', range: 'ytd', positions: [] };

  fetch('/assets/trades.json', { cache: 'no-store' })
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (data) {
      if (!data || !data.trades) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-muted" style="text-align:center; padding:32px;">Trade data unavailable right now.</td></tr>';
        return;
      }
      state.trades = data.trades;
      state.summary = data.summary;
      renderChart(data.trades);
      wireControls();
      wireRangeTabs();
      applyUrlFilter();
      renderSummary();
      render();
    })
    .catch(function () {
      tbody.innerHTML = '<tr><td colspan="7" class="text-muted" style="text-align:center; padding:32px;">Trade data unavailable right now.</td></tr>';
    });

  // Open positions (unrealized) — separate feed from the realized trade log,
  // refreshed by the same Record Refresh routine. Optional section: pages
  // without a #positionsTbody (none currently) just skip this silently.
  var positionsTbody = document.getElementById('positionsTbody');
  if (positionsTbody) {
    fetch('/assets/positions.json', { cache: 'no-store' })
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) {
        if (!data || !data.positions) {
          positionsTbody.innerHTML = '<tr><td colspan="7" class="text-muted" style="text-align:center; padding:32px;">Position data unavailable right now.</td></tr>';
          return;
        }
        state.positions = data.positions;
        setText('statPositionsAsOf', data.asOfLabel || '—');
        var accountEl = document.getElementById('recordAccount');
        if (accountEl) accountEl.addEventListener('input', renderPositions);
        renderPositions();
      })
      .catch(function () {
        positionsTbody.innerHTML = '<tr><td colspan="7" class="text-muted" style="text-align:center; padding:32px;">Position data unavailable right now.</td></tr>';
      });
  }

  function renderPositions() {
    var accountEl = document.getElementById('recordAccount');
    var account = accountEl ? accountEl.value : 'all';
    var rows = state.positions.filter(function (p) { return account === 'all' || p.account === account; });

    var totalUnrealized = rows.reduce(function (sum, p) { return sum + p.unrealizedGain; }, 0);
    setText('statUnrealizedPnl', money(totalUnrealized), totalUnrealized >= 0 ? 'gain' : 'loss');
    setText('statPositionCount', String(rows.length));
    renderTodayTotal();

    if (!rows.length) {
      positionsTbody.innerHTML = '<tr><td colspan="7" class="text-muted" style="text-align:center; padding:32px;">No open positions match this filter.</td></tr>';
      return;
    }

    positionsTbody.innerHTML = rows.map(function (p) {
      var dir = p.unrealizedGain > 0 ? 'gain' : (p.unrealizedGain < 0 ? 'loss' : '');
      var symbolCell = escapeHtml(p.symbol);
      if (p.assetType === 'option') {
        symbolCell += ' <span class="text-muted" style="font-size:12px;">$' + p.strike + (p.optionType === 'put' ? 'P' : 'C') + ' ' + shortDate(p.expiration) + '</span>';
      }
      return '<tr>' +
        '<td><strong>' + symbolCell + '</strong></td>' +
        '<td>' + escapeHtml(p.account) + '</td>' +
        '<td><span class="badge-type">' + typeLabel(p.assetType) + '</span></td>' +
        '<td class="num">' + trimQty(p.quantity) + '</td>' +
        '<td class="num">$' + p.avgCost.toFixed(2) + '</td>' +
        '<td class="num">$' + p.currentPrice.toFixed(2) + '</td>' +
        '<td class="num ' + dir + '">' + money(p.unrealizedGain) + '</td>' +
        '</tr>';
    }).join('');
  }

  function shortDate(iso) {
    if (!iso) return '';
    var parts = iso.split('-');
    var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return months[parseInt(parts[1], 10) - 1] + ' ' + parseInt(parts[2], 10);
  }

  // Lets a link like /record/index.html?account=Trading or ?range=week land
  // pre-filtered — used by the homepage scoreboard cards and the range tabs
  // so "click to see all the trades" takes you to the right filtered view.
  function applyUrlFilter() {
    var params = new URLSearchParams(window.location.search);
    var account = params.get('account');
    if (account) {
      var select = document.getElementById('recordAccount');
      if (select) {
        var hasOption = Array.prototype.some.call(select.options, function (opt) { return opt.value === account; });
        if (hasOption) select.value = account;
      }
    }
    var range = params.get('range');
    if (range && (range === 'day' || range === 'week' || range === 'month' || range === 'ytd')) {
      setRange(range);
    }
  }

  // Range cutoffs are computed from the newest trade date in the dataset
  // (not the browser's local "today"), so the tabs stay correct even if
  // trades.json hasn't refreshed since midnight.
  function rangeCutoffDate(range) {
    if (!state.trades.length) return null;
    var newest = state.trades.reduce(function (max, t) { return t.date > max ? t.date : max; }, state.trades[0].date);
    if (range === 'day') return newest; // 1D — just the most recent trading day in the dataset
    var d = new Date(newest + 'T12:00:00Z');
    if (range === 'week') d.setUTCDate(d.getUTCDate() - 7);
    else if (range === 'month') d.setUTCDate(d.getUTCDate() - 30);
    else return null; // ytd — no cutoff beyond what's already in the dataset
    return d.toISOString().slice(0, 10);
  }

  function setRange(range) {
    state.range = range;
    document.querySelectorAll('.range-tab').forEach(function (btn) {
      btn.classList.toggle('active', btn.getAttribute('data-range') === range);
    });
  }

  function wireRangeTabs() {
    document.querySelectorAll('.range-tab').forEach(function (btn) {
      btn.addEventListener('click', function () {
        setRange(btn.getAttribute('data-range'));
        renderSummary();
        render();
        renderTodayTotal();
      });
    });
  }

  // "Today, Total" — only meaningful on the 1D tab. Robinhood's own headline
  // "Today" figure on the account screen is realized-today + the day's mark-
  // to-market move on whatever's still open, not realized-only — this stat
  // reconstructs that so the two match, instead of leaving Keith looking at
  // a much smaller "Net Realized" number on a day where most of the move is
  // still sitting in open positions (confirmed 2026-09-17: on a day with $0
  // realized so far, Robinhood's app showed +$424.79 "Today", 100% from
  // unrealized moves on positions still held).
  function renderTodayTotal() {
    var card = document.getElementById('statTodayTotalCard');
    if (!card) return;
    if (state.range !== 'day' || !state.positions.length) { card.hidden = true; return; }
    card.hidden = false;

    var account = document.getElementById('recordAccount').value;
    var cutoff = rangeCutoffDate('day');
    var todayRealized = state.trades
      .filter(function (t) { return (account === 'all' || t.account === account) && t.date === cutoff; })
      .reduce(function (sum, t) { return sum + t.realizedGain; }, 0);

    var todayUnrealized = state.positions
      .filter(function (p) { return account === 'all' || p.account === account; })
      .reduce(function (sum, p) {
        var prior = (typeof p.priorClose === 'number') ? p.priorClose : p.currentPrice;
        return sum + (p.currentPrice - prior) * p.quantity;
      }, 0);

    var total = todayRealized + todayUnrealized;
    setText('statTodayTotal', money(total), total >= 0 ? 'gain' : 'loss');
  }

  // Recomputes the stat row from whatever's currently in scope: the active
  // range tab plus the account filter (type/outcome/search stay table-only —
  // mixing "win rate for options only" into the headline stat would be more
  // confusing than useful). Real numbers, computed live from trades.json,
  // not baked in once a day.
  function renderSummary() {
    var account = document.getElementById('recordAccount').value;
    var cutoff = rangeCutoffDate(state.range);
    var scoped = state.trades.filter(function (t) {
      if (account !== 'all' && t.account !== account) return false;
      if (cutoff && t.date < cutoff) return false;
      return true;
    });

    var totalGain = scoped.reduce(function (sum, t) { return sum + t.realizedGain; }, 0);
    var wins = scoped.filter(function (t) { return t.realizedGain > 0; }).length;
    var losses = scoped.filter(function (t) { return t.realizedGain < 0; }).length;
    var winRate = (wins + losses) ? (100 * wins / (wins + losses)) : 0;
    var biggestWin = scoped.reduce(function (m, t) { return (!m || t.realizedGain > m.realizedGain) ? t : m; }, null);
    var biggestLoss = scoped.reduce(function (m, t) { return (!m || t.realizedGain < m.realizedGain) ? t : m; }, null);

    setText('statTotalPnl', money(totalGain), totalGain >= 0 ? 'gain' : 'loss');
    setText('statWinRate', winRate.toFixed(1) + '%');
    setText('statTotalTrades', String(scoped.length));
    if (biggestWin) setText('statBiggestWin', money(biggestWin.realizedGain) + ' ' + biggestWin.symbol);
    if (biggestLoss) setText('statBiggestLoss', money(biggestLoss.realizedGain) + ' ' + biggestLoss.symbol);
    state.scopedBiggestWin = biggestWin;
    state.scopedBiggestLoss = biggestLoss;
  }

  function setText(id, text, extraClass) {
    var el = document.getElementById(id);
    if (!el) return;
    el.textContent = text;
    el.classList.remove('gain', 'loss');
    if (extraClass) el.classList.add(extraClass);
  }

  function wireControls() {
    ['recordSearch', 'recordType', 'recordOutcome'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener('input', render);
    });
    var accountEl = document.getElementById('recordAccount');
    if (accountEl) accountEl.addEventListener('input', function () { renderSummary(); render(); });
    document.querySelectorAll('#recordTable thead th[data-sort]').forEach(function (th) {
      th.addEventListener('click', function () {
        var key = th.getAttribute('data-sort');
        if (state.sortKey === key) {
          state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc';
        } else {
          state.sortKey = key;
          state.sortDir = 'desc';
        }
        document.querySelectorAll('#recordTable thead th').forEach(function (h) { h.classList.remove('sort-active'); });
        th.classList.add('sort-active');
        var arrow = th.querySelector('.sort-arrow');
        if (arrow) arrow.innerHTML = state.sortDir === 'asc' ? '&#9650;' : '&#9660;';
        render();
      });
    });

    var winCard = document.getElementById('statBiggestWinCard');
    var lossCard = document.getElementById('statBiggestLossCard');
    if (winCard) wireJumpCard(winCard, function () { return toJumpTarget(state.scopedBiggestWin); });
    if (lossCard) wireJumpCard(lossCard, function () { return toJumpTarget(state.scopedBiggestLoss); });
  }

  function toJumpTarget(trade) {
    if (!trade) return null;
    return { symbol: trade.symbol, date: trade.date, gain: trade.realizedGain };
  }

  function wireJumpCard(card, getTarget) {
    function activate() {
      var t = getTarget();
      if (t) jumpToTrade(t);
    }
    card.addEventListener('click', activate);
    card.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); activate(); }
    });
  }

  // Resets filters/search so the target trade is guaranteed visible, sorts by
  // date so the jump is deterministic, then scrolls to and briefly highlights
  // the matching row (matched on symbol+date+gain, which is unique enough for
  // this dataset's actual size — no stable row id exists to key off instead).
  function jumpToTrade(target) {
    document.getElementById('recordSearch').value = '';
    document.getElementById('recordAccount').value = 'all';
    document.getElementById('recordType').value = 'all';
    document.getElementById('recordOutcome').value = 'all';
    setRange('ytd');
    state.sortKey = 'date';
    state.sortDir = 'desc';
    document.querySelectorAll('#recordTable thead th').forEach(function (h) { h.classList.remove('sort-active'); });
    var dateTh = document.querySelector('#recordTable thead th[data-sort="date"]');
    if (dateTh) {
      dateTh.classList.add('sort-active');
      var arrow = dateTh.querySelector('.sort-arrow');
      if (arrow) arrow.innerHTML = '&#9660;';
    }
    renderSummary();
    render();

    var row = document.querySelector(
      '#recordTbody tr[data-symbol="' + cssEscape(target.symbol) + '"][data-date="' + target.date + '"][data-gain="' + target.gain + '"]'
    );
    if (!row) return;
    row.scrollIntoView({ behavior: 'smooth', block: 'center' });
    row.classList.add('row-flash');
    setTimeout(function () { row.classList.remove('row-flash'); }, 2200);
  }

  function cssEscape(s) {
    return String(s).replace(/["\\]/g, '\\$&');
  }

  function render() {
    var search = (document.getElementById('recordSearch').value || '').trim().toUpperCase();
    var account = document.getElementById('recordAccount').value;
    var type = document.getElementById('recordType').value;
    var outcome = document.getElementById('recordOutcome').value;

    var cutoff = rangeCutoffDate(state.range);
    var rows = state.trades.filter(function (t) {
      if (search && t.symbol.toUpperCase().indexOf(search) === -1) return false;
      if (account !== 'all' && t.account !== account) return false;
      if (type !== 'all' && t.assetType !== type) return false;
      if (outcome === 'win' && t.realizedGain <= 0) return false;
      if (outcome === 'loss' && t.realizedGain >= 0) return false;
      if (cutoff && t.date < cutoff) return false;
      return true;
    });

    rows.sort(function (a, b) {
      var av = a[state.sortKey], bv = b[state.sortKey];
      if (typeof av === 'string') { av = av.toLowerCase(); bv = (bv || '').toLowerCase(); }
      if (av < bv) return state.sortDir === 'asc' ? -1 : 1;
      if (av > bv) return state.sortDir === 'asc' ? 1 : -1;
      return 0;
    });

    document.getElementById('recordCount').textContent = rows.length + ' of ' + state.trades.length + ' trades';

    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-muted" style="text-align:center; padding:32px;">No trades match those filters.</td></tr>';
      return;
    }

    tbody.innerHTML = rows.map(function (t) {
      var dir = t.realizedGain > 0 ? 'gain' : (t.realizedGain < 0 ? 'loss' : '');
      return '<tr data-symbol="' + escapeHtml(t.symbol) + '" data-date="' + t.date + '" data-gain="' + t.realizedGain + '">' +
        '<td class="num">' + t.date + '</td>' +
        '<td><strong>' + escapeHtml(t.symbol) + '</strong></td>' +
        '<td>' + escapeHtml(t.account) + '</td>' +
        '<td><span class="badge-type">' + typeLabel(t.assetType) + '</span></td>' +
        '<td class="num">' + trimQty(t.quantity) + '</td>' +
        '<td class="num">' + (t.price != null ? '$' + t.price.toFixed(2) : '&mdash;') + '</td>' +
        '<td class="num ' + dir + '">' + money(t.realizedGain) + '</td>' +
        '</tr>';
    }).join('');
  }

  function renderChart(trades) {
    var el = document.getElementById('recordChart');
    if (!el) return;
    var asc = trades.slice().sort(function (a, b) { return a.timestamp < b.timestamp ? -1 : 1; });
    var points = [];
    var running = 0;
    asc.forEach(function (t) {
      running += t.realizedGain;
      points.push({ date: t.date, value: running });
    });
    if (!points.length) return;

    var w = 900, h = 260, pad = 36;
    var values = points.map(function (p) { return p.value; });
    var minV = Math.min(0, Math.min.apply(null, values));
    var maxV = Math.max(0, Math.max.apply(null, values));
    var range = (maxV - minV) || 1;

    function x(i) { return pad + (i / (points.length - 1 || 1)) * (w - pad * 2); }
    function y(v) { return h - pad - ((v - minV) / range) * (h - pad * 2); }

    var path = points.map(function (p, i) { return (i === 0 ? 'M' : 'L') + x(i).toFixed(1) + ',' + y(p.value).toFixed(1); }).join(' ');
    var zeroY = y(0).toFixed(1);
    var last = points[points.length - 1].value;
    var lineColor = last >= 0 ? 'var(--gain)' : 'var(--loss)';

    el.innerHTML =
      '<svg viewBox="0 0 ' + w + ' ' + h + '" width="100%" style="max-width:900px; display:block;" preserveAspectRatio="xMinYMid meet">' +
      '<line x1="' + pad + '" y1="' + zeroY + '" x2="' + (w - pad) + '" y2="' + zeroY + '" stroke="var(--border)" stroke-width="1" stroke-dasharray="4 4"/>' +
      '<path d="' + path + '" fill="none" stroke="' + lineColor + '" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>' +
      '<text x="' + pad + '" y="16" font-family="IBM Plex Mono, monospace" font-size="11" fill="var(--text-muted)">' + points[0].date + '</text>' +
      '<text x="' + (w - pad) + '" y="16" font-family="IBM Plex Mono, monospace" font-size="11" fill="var(--text-muted)" text-anchor="end">' + points[points.length - 1].date + '</text>' +
      '</svg>';
  }

  function typeLabel(t) {
    return { equity: 'Stock', option: 'Option', crypto: 'Crypto', other: 'Other' }[t] || t;
  }

  function trimQty(q) {
    if (q % 1 === 0) return String(q);
    return q.toFixed(4).replace(/0+$/, '').replace(/\.$/, '');
  }

  function money(n) {
    var sign = n > 0 ? '+' : (n < 0 ? '-' : '');
    return sign + '$' + Math.abs(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
});
