// MarketsOnDeck — The Record: sortable/filterable trade log + cumulative P&L chart.
// No frameworks, no build step — same discipline as the rest of the site.
document.addEventListener('DOMContentLoaded', function () {
  var tbody = document.getElementById('recordTbody');
  if (!tbody) return;

  var state = { trades: [], sortKey: 'date', sortDir: 'desc' };

  fetch('/assets/trades.json', { cache: 'no-store' })
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (data) {
      if (!data || !data.trades) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-muted" style="text-align:center; padding:32px;">Trade data unavailable right now.</td></tr>';
        return;
      }
      state.trades = data.trades;
      renderSummary(data.summary);
      renderChart(data.trades);
      wireControls();
      render();
    })
    .catch(function () {
      tbody.innerHTML = '<tr><td colspan="7" class="text-muted" style="text-align:center; padding:32px;">Trade data unavailable right now.</td></tr>';
    });

  function renderSummary(s) {
    if (!s) return;
    setText('statTotalPnl', money(s.totalRealizedGain), s.totalRealizedGain >= 0 ? 'gain' : 'loss');
    setText('statWinRate', s.winRate.toFixed(1) + '%');
    setText('statTotalTrades', String(s.totalTrades));
    setText('statBiggestWin', money(s.biggestWin.gain) + ' ' + s.biggestWin.symbol);
    setText('statBiggestLoss', money(s.biggestLoss.gain) + ' ' + s.biggestLoss.symbol);
  }

  function setText(id, text, extraClass) {
    var el = document.getElementById(id);
    if (!el) return;
    el.textContent = text;
    if (extraClass) el.classList.add(extraClass);
  }

  function wireControls() {
    ['recordSearch', 'recordAccount', 'recordType', 'recordOutcome'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener('input', render);
    });
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
        th.querySelector('.sort-arrow').innerHTML = state.sortDir === 'asc' ? '&#9650;' : '&#9660;';
        render();
      });
    });
  }

  function render() {
    var search = (document.getElementById('recordSearch').value || '').trim().toUpperCase();
    var account = document.getElementById('recordAccount').value;
    var type = document.getElementById('recordType').value;
    var outcome = document.getElementById('recordOutcome').value;

    var rows = state.trades.filter(function (t) {
      if (search && t.symbol.toUpperCase().indexOf(search) === -1) return false;
      if (account !== 'all' && t.account !== account) return false;
      if (type !== 'all' && t.assetType !== type) return false;
      if (outcome === 'win' && t.realizedGain <= 0) return false;
      if (outcome === 'loss' && t.realizedGain >= 0) return false;
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
      return '<tr>' +
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
