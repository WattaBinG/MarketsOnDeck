// Shared by realized rows, open positions and Tape's verified-fill card.
(function (root) {
  'use strict';
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
  function dollars(n) { return '$' + n.toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:4}); }
  function identity(t) {
    if (t.assetType !== 'option') return t.symbol;
    if (!t.underlying || !t.expiration || !Number.isFinite(t.strike) || !/^(call|put)$/.test(t.optionType || '')) return t.symbol + ' option · contract details unavailable';
    return t.underlying + ' $' + t.strike.toFixed(2) + ' ' + t.optionType + ' · ' + t.expiration;
  }
  function quantity(t) {
    var n = t.assetType === 'option' && t.contracts != null ? t.contracts : t.quantity;
    return n + (t.assetType === 'option' ? n === 1 ? ' contract' : ' contracts' : t.assetType === 'equity' ? n === 1 ? ' share' : ' shares' : '');
  }
  function premium(t, value) {
    if (!Number.isFinite(value)) return 'Unavailable';
    if (t.priceUnit === 'USD_per_share' && Number.isFinite(t.multiplier)) return dollars(value) + '/share · ' + dollars(value * t.multiplier) + '/contract';
    if (t.priceUnit === 'USD_per_contract' && Number.isFinite(t.multiplier)) return dollars(value / t.multiplier) + '/share · ' + dollars(value) + '/contract';
    return 'Price unit unavailable';
  }
  function closePrices(t) {
    if (t.assetType !== 'option') return t.price == null ? 'Unavailable' : dollars(t.price);
    return 'Entry ' + premium(t, t.entryPremium) + '<br>Exit ' + premium(t, t.exitPremium);
  }
  var api = {esc:esc, identity:identity, quantity:quantity, premium:premium, closePrices:closePrices};
  root.JournalFormat = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
