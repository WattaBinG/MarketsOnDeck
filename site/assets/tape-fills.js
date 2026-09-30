document.addEventListener('DOMContentLoaded', function () {
  var card = document.getElementById('metaVerifiedFills');
  if (!card) return;
  fetch('/assets/trades.json', {cache:'no-store'}).then(function (r) { return r.ok ? r.json() : null; }).then(function (data) {
    if (!data) return;
    var rows = data.trades.filter(function (t) { return t.assetType === 'option' && t.underlying === 'META' && t.expiration === '2026-10-02' && t.strike === 742.5 && t.optionType === 'put' && t.date === '2026-09-28' && t.account === 'Trading'; });
    if (rows.length !== 3) return;
    card.innerHTML = '<h3>Verified option closes</h3><p>' + JournalFormat.esc(JournalFormat.identity(rows[0])) + ' · Trading</p>' + rows.map(function (t) {
      return '<p><strong>' + JournalFormat.esc(JournalFormat.quantity(t)) + ' · sell to close</strong><br>' + JournalFormat.closePrices(t) + '<br>Reported realized profit: $' + t.realizedGain.toFixed(2) + '</p>';
    }).join('') + '<small class="text-muted">From the same verified fills as The Record. Premium totals exclude separately shown regulatory fees. Entry allocation reconciles opening fills with reported realized profit; it is not a broker lot report.</small>';
    card.hidden = false;
  }).catch(function () {});
});
