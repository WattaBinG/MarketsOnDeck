const assert=require('node:assert/strict');
const t=require('../site/assets/trust.js');
assert.equal(t.etDate(new Date('2026-10-07T03:59:00Z')),'2026-10-06');
assert.equal(t.etDate(new Date('2026-10-07T04:00:00Z')),'2026-10-07');
assert.equal(t.staleDate('2026-09-30',new Date('2026-10-07T05:00:00Z')),true);
assert.equal(t.staleDate(null),true);
assert.equal(t.olderStockClose('2026-10-06T20:07:26Z',new Date('2026-10-07T05:00:00Z')),false);
assert.equal(t.olderStockClose('2026-10-01T20:00:00Z',new Date('2026-10-07T05:00:00Z')),true);
assert.equal(t.olderStockClose('2026-10-02T20:00:00Z',new Date('2026-10-05T13:00:00Z')),false);
assert.deepEqual(t.period([{date:'2026-01-01',realizedGain:.1},{date:'2026-01-01',realizedGain:.2}], '2026-01-01','2026-01-01'),{net:.3,count:2,winRate:'100.00% (2W / 0L)'});
console.log('Trust dates, rollover, stock-close/weekend handling, unknown dates and decimal totals pass');

assert.equal(t.datePart('2026-02-30'),null);
