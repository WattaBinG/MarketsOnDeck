const assert = require('node:assert/strict');
const j = require('../site/assets/journal-format.js');
const d = require('../site/assets/trades.json');
// Locate a schema-v2 row by id (trades[0] is a legacy Jan 2 row and the book order changes).
const row = d.trades.find(t => t.id === 'SPCX-close-1');
assert.ok(row, 'SPCX-close-1 must exist');
assert.match(j.identity(row), /SPCX \$155.00 call · 2026-10-02/);
assert.match(j.closePrices(row), /Entry \$4.25\/share · \$425.00\/contract/);
assert.match(j.closePrices(row), /Exit \$0.94\/share · \$94.00\/contract/);
assert.equal(j.quantity(row), '2 contracts');
assert.match(j.identity({symbol:'META',assetType:'option'}), /details unavailable/);
assert.match(j.closePrices({assetType:'option',price:2280}), /Unavailable/);
assert.equal(j.closePrices({assetType:'equity',price:17.1}), '$17.10');
assert.equal(j.premium({priceUnit:'USD_per_contract',multiplier:100},60.5), '$0.605/share · $60.50/contract');
console.log('Journal formatter tests passed');
