import fs from 'node:fs';
import assert from 'node:assert/strict';
const mod=await import('data:text/javascript;base64,'+Buffer.from(fs.readFileSync('scheduler/src/index.js')).toString('base64'));
const seen=[];
await mod.dispatchCycle({scheduledTime:Date.parse('2026-09-27T02:15:00Z')},{GITHUB_DISPATCH_TOKEN:'test-only'}, async (url,opts)=>{
 seen.push({url,method:opts.method,body:JSON.parse(opts.body),auth:opts.headers.Authorization});
 return {status:204};
});
assert.deepEqual(seen.map(x=>x.url.split('/').at(-2)).sort(),['refresh-crypto.yml','refresh-wire.yml']);
assert.ok(seen.every(x=>x.method==='POST'&&x.body.ref==='main'&&x.body.inputs.cycle==='2026-09-27T02:15:00.000Z'&&x.auth==='Bearer test-only'));
const watch=[];
await mod.dispatchCycle({scheduledTime:Date.parse('2026-09-27T23:00:00Z'),cron:'0 23 * * SUN-THU'},{GITHUB_DISPATCH_TOKEN:'test-only'},async(url)=>{watch.push(url);return {status:204};});
assert.deepEqual(watch.map(x=>x.split('/').at(-2)),['refresh-watch-today.yml']);
const earn=[];
await mod.dispatchCycle({scheduledTime:Date.parse('2026-10-09T11:00:00Z'),cron:'0 11 * * *'},{GITHUB_DISPATCH_TOKEN:'test-only'},async(url)=>{earn.push(url);return {status:204};});
assert.deepEqual(earn.map(x=>x.split('/').at(-2)),['refresh-earnings.yml']);
await assert.rejects(mod.dispatchCycle({scheduledTime:0},{GITHUB_DISPATCH_TOKEN:'test-only'},async()=>({status:403})),/HTTP 403/);
console.log('pass: two dispatches and 403 failure path');
