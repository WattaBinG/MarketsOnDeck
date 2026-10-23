const assert = require('node:assert/strict');
const path = require('node:path');
// Repo-relative: works in any clean checkout, not just /tmp/rebase
const positions = require(path.join(__dirname, '..', 'site', 'assets', 'positions.json')).positions;

// Replicate the display-filter logic from record.js renderPositions()
function displayValue(p) {
  var value = Math.abs(p.quantity * p.currentPrice);
  if (p.assetType === 'futures' && p.quotedMark) {
    value = Math.abs(p.quantity * p.quotedMark * (p.multiplier || 1));
  }
  return value;
}

function getDisplayRows(rows) {
  return rows.filter(function (p) { return displayValue(p) >= 5; });
}

// Test 1: Dust positions (DOGE, USDC) are hidden from display
const displayRows = getDisplayRows(positions);
const displaySymbols = displayRows.map(p => p.symbol);
assert(!displaySymbols.includes('DOGE'), 'DOGE should be hidden (under $5)');
assert(!displaySymbols.includes('USDC'), 'USDC should be hidden (under $5)');
console.log('✓ Dust positions hidden from display');

// Test 2: Dust positions are still in the data (not deleted)
const allSymbols = positions.map(p => p.symbol);
assert(allSymbols.includes('DOGE'), 'DOGE must be retained in positions.json');
assert(allSymbols.includes('USDC'), 'USDC must be retained in positions.json');
console.log('✓ Dust positions retained in data');

// Test 3: Totals use ALL positions (including hidden dust)
const totalUnrealized = positions.reduce((sum, p) => sum + p.unrealizedGain, 0);
const displayUnrealized = displayRows.reduce((sum, p) => sum + p.unrealizedGain, 0);
const dustUgl = positions
  .filter(p => !displaySymbols.includes(p.symbol))
  .reduce((sum, p) => sum + p.unrealizedGain, 0);
assert(Math.abs(totalUnrealized - (displayUnrealized + dustUgl)) < 0.001,
  'Totals must include hidden positions');
console.log('✓ Totals include hidden dust positions');

// Test 4: Futures use quoted prices for the $5 threshold. Synthetic open
// futures fixture (the real book now holds a CLOSED METV26, quantity 0).
const openFutures = { symbol: 'FUT', assetType: 'futures', quantity: 30, currentPrice: null,
  quotedMark: 2400, multiplier: 0.1 };
assert(displayValue(openFutures) >= 5, 'Open futures value must use quoted prices');
assert(getDisplayRows([openFutures]).length === 1, 'Open futures must be displayed');
assert(Math.abs(openFutures.quantity * (openFutures.currentPrice || 0)) < 5,
  'Fixture must only pass via the quoted mark');
const closedFutures = positions.find(p => p.assetType === 'futures');
assert(closedFutures && closedFutures.quantity === 0, 'Book must carry the closed METV26 row');
assert(!displaySymbols.includes('METV26'), 'Closed METV26 (qty 0) is hidden from display');
console.log('✓ Futures threshold uses quoted prices');

// Test 5: Hidden positions in the Oct 22 book = DOGE and USDC dust plus the
// closed METV26 row (quantity 0). Option positions now carry marks and show.
const hiddenRows = positions.filter(p => displayValue(p) < 5);
const hiddenIds = hiddenRows.map(p => p.contractId || p.symbol).sort();
assert.deepEqual(hiddenIds, ['DOGE', 'METV26', 'USDC'], 'Hidden set: ' + hiddenIds.join(','));
const hiddenCount = positions.length - displayRows.length;
assert(hiddenCount === 3, `Expected 3 hidden (2 dust + closed METV26), got ${hiddenCount}`);
console.log('✓ Hidden count correct');

console.log('\nDisplay filter tests passed');
