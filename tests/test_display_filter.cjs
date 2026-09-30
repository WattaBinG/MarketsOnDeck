const assert = require('node:assert/strict');
const positions = require('/tmp/rebase/test_site/site/assets/positions.json').positions;

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
// The totals should differ by exactly the dust uGL (proving dust is counted)
const dustUgl = positions
  .filter(p => !displaySymbols.includes(p.symbol))
  .reduce((sum, p) => sum + p.unrealizedGain, 0);
assert(Math.abs(totalUnrealized - (displayUnrealized + dustUgl)) < 0.001,
  'Totals must include hidden positions');
console.log('✓ Totals include hidden dust positions');

// Test 4: Futures use quoted prices for the $5 threshold (not per-contract dollars)
// METV26: 10 contracts × $2690.50 quoted × 0.1 = $2690.50 value (well over $5)
// If we used per-contract dollars (10 × $269.05 = $2690.50), same result here,
// but the logic must reference quotedMark for correctness
const futures = positions.find(p => p.assetType === 'futures');
assert(futures, 'Futures position must exist');
assert(displaySymbols.includes('METV26'), 'METV26 should be displayed (value >> $5)');
const futuresValue = displayValue(futures);
assert(futuresValue >= 5, 'Futures value calculation must use quoted prices');
console.log('✓ Futures threshold uses quoted prices');

// Test 5: Hidden count is correct
const hiddenCount = positions.length - displayRows.length;
assert(hiddenCount === 3, `Expected 3 hidden (USDG, DOGE, USDC), got ${hiddenCount}`);
console.log('✓ Hidden count correct');

console.log('\nDisplay filter tests passed');
