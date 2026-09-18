import assert from 'node:assert/strict';
import { normalizeSnapshot } from '../src/worker.mjs';

const spy = normalizeSnapshot({ symbol: 'SPY', price: '762.65', pre_close: '754.17' }, 'SPY');
assert.equal(spy.priorClose, 754.17);
assert.equal(spy.change, 8.48);
assert.equal(spy.changePercent, 1.1244);

const loss = normalizeSnapshot({ symbol: 'SOFI', price: '16.73', pre_close: '16.84' }, 'SOFI');
assert.equal(loss.change, -0.11);
assert.equal(loss.changePercent, -0.6532);
assert.equal(loss.held, true);

assert.throws(() => normalizeSnapshot({ symbol: 'SPY', price: '1', pre_close: '0' }, 'SPY'));
assert.throws(() => normalizeSnapshot(undefined, 'SPY'));
console.log('worker normalization tests passed');
