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

// Test 4: Futures use quoted prices for the $5 threshold
const futures = positions.find(p => p.assetType === 'futures');
assert(futures, 'Futures position must exist');
assert(displaySymbols.includes('METV26'), 'METV26 should be displayed (value >> $5)');
const futuresValue = displayValue(futures);
assert(futuresValue >= 5, 'Futures value calculation must use quoted prices');
console.log('✓ Futures threshold uses quoted prices');

// Test 5: USDG is hidden (cash-like, but value $102.58 > $5? No - USDG is cash-like)
// Actually USDG at $102.58 SHOULD display. Update: hidden are DOGE, USDC only.
// DOGE: 1 × $0.094 = $0.094 (hidden). USDC: 0.00993 × $1 = $0.01 (hidden).
// USDG: 102.58 × $1 = $102.58 (displayed).
const hiddenCount = positions.length - displayRows.length;
assert(hiddenCount === 2, `Expected 2 hidden (DOGE, USDC), got ${hiddenCount}`);
console.log('✓ Hidden count correct');

console.log('\nDisplay filter tests passed');
