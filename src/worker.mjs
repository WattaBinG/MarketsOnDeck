const TICKER_PATH = '/api/ticker';
const CACHE_SECONDS = 15 * 60;

const ETF_SYMBOLS = ['SPY', 'QQQ', 'DIA', 'IWM'];
const STOCK_SYMBOLS = ['NVDA', 'LULU', 'SPCX', 'QUBT', 'INTC', 'TSLA', 'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'AMD', 'SOFI', 'KLAC', 'SPCH', 'COIN', 'PLTR'];
const PINNED = ['SPY', 'QQQ', 'DIA'];
const HELD = new Set(['SPCX', 'QUBT', 'SOFI', 'KLAC', 'SPCH']);

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname !== TICKER_PATH) return env.ASSETS.fetch(request);
    if (request.method !== 'GET') return new Response('Method not allowed', { status: 405 });

    const cache = caches.default;
    const cacheKey = new Request(new URL(TICKER_PATH, url.origin), { method: 'GET' });
    const cached = await cache.match(cacheKey);
    if (cached) return cached;

    try {
      const response = await buildTickerResponse(env);
      ctx.waitUntil(cache.put(cacheKey, response.clone()));
      return response;
    } catch (error) {
      const fallback = await env.ASSETS.fetch(new Request(new URL('/assets/ticker.json', url.origin)));
      const body = await fallback.text();
      return new Response(body, {
        status: fallback.ok ? 200 : 503,
        headers: {
          'content-type': 'application/json; charset=utf-8',
          'cache-control': 'no-store',
          'x-marketsondeck-source': 'static-fallback',
          'x-marketsondeck-error': safeError(error)
        }
      });
    }
  },

  async scheduled(controller, env, ctx) {
    // Warm a fresh snapshot. User requests still self-refresh after 15 minutes,
    // so a missed cron does not leave the ticker stale indefinitely.
    ctx.waitUntil(buildTickerResponse(env).then((response) => {
      const cacheKey = new Request(new URL(TICKER_PATH, env.PUBLIC_ORIGIN || 'https://marketsondeck.wattabing.workers.dev'));
      return caches.default.put(cacheKey, response);
    }));
  }
};

export async function buildTickerResponse(env) {
  requireSecret(env, 'WEBULL_APP_KEY');
  requireSecret(env, 'WEBULL_APP_SECRET');

  const groups = await Promise.all([
    fetchSnapshots(env, ETF_SYMBOLS, 'US_ETF'),
    fetchSnapshots(env, STOCK_SYMBOLS, 'US_STOCK')
  ]);
  const rows = groups.flat();
  const bySymbol = new Map(rows.map((row) => [row.symbol, row]));
  const ordered = ETF_SYMBOLS.concat(STOCK_SYMBOLS);
  const items = ordered.map((symbol) => normalizeSnapshot(bySymbol.get(symbol), symbol));
  const newestTrade = Math.max(...rows.map((row) => Number(row.last_trade_time || 0)));
  const asOf = newestTrade > 0 ? new Date(newestTrade).toISOString() : new Date().toISOString();

  const payload = {
    schemaVersion: 2,
    asOf,
    asOfLabel: formatAsOfLabel(asOf),
    source: 'Webull OpenAPI snapshot',
    methodology: 'Change is current snapshot price minus Webull pre_close (the immediately preceding regular-session official close). Extended-hours prices, when supplied, remain measured from that same close.',
    pinned: PINNED,
    items
  };

  return Response.json(payload, {
    headers: {
      'cache-control': `public, max-age=60, s-maxage=${CACHE_SECONDS}, stale-while-revalidate=60`,
      'x-marketsondeck-source': 'webull-openapi'
    }
  });
}

async function fetchSnapshots(env, symbols, category) {
  const path = '/openapi/market-data/stock/snapshot';
  const params = {
    category,
    extend_hour_required: 'true',
    overnight_required: 'false',
    symbols: symbols.join(',')
  };
  const headers = await webullHeaders(env, path, params);
  const url = new URL(`https://${env.WEBULL_API_HOST || 'api.webull.com'}${path}`);
  Object.entries(params).forEach(([key, value]) => url.searchParams.set(key, value));

  const response = await fetch(url, { headers });
  if (!response.ok) throw new Error(`Webull ${category} snapshot returned ${response.status}`);
  const data = await response.json();
  if (!Array.isArray(data)) throw new Error(`Webull ${category} snapshot was not an array`);
  return data;
}

export function normalizeSnapshot(row, expectedSymbol) {
  if (!row || row.symbol !== expectedSymbol) throw new Error(`Missing Webull snapshot for ${expectedSymbol}`);
  const price = finiteNumber(row.price, `${expectedSymbol} price`);
  const priorClose = finiteNumber(row.pre_close, `${expectedSymbol} pre_close`);
  if (priorClose <= 0) throw new Error(`Invalid ${expectedSymbol} pre_close`);
  const change = price - priorClose;
  return {
    symbol: expectedSymbol,
    price: round(price, 4),
    priorClose: round(priorClose, 4),
    change: round(change, 4),
    changePercent: round((change / priorClose) * 100, 4),
    ...(HELD.has(expectedSymbol) ? { held: true } : {})
  };
}

async function webullHeaders(env, path, params) {
  const host = env.WEBULL_API_HOST || 'api.webull.com';
  const timestamp = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
  const nonce = crypto.randomUUID().replaceAll('-', '');
  const signing = {
    host,
    ...params,
    'x-app-key': env.WEBULL_APP_KEY,
    'x-signature-algorithm': 'HMAC-SHA1',
    'x-signature-nonce': nonce,
    'x-signature-version': '1.0',
    'x-timestamp': timestamp
  };
  const str1 = Object.keys(signing).sort().map((key) => `${key}=${signing[key]}`).join('&');
  const encoded = rfc3986(`${path}&${str1}`);
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(`${env.WEBULL_APP_SECRET}&`),
    { name: 'HMAC', hash: 'SHA-1' },
    false,
    ['sign']
  );
  const bytes = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(encoded));
  const signature = btoa(String.fromCharCode(...new Uint8Array(bytes)));
  return {
    'x-app-key': env.WEBULL_APP_KEY,
    'x-timestamp': timestamp,
    'x-signature': signature,
    'x-signature-algorithm': 'HMAC-SHA1',
    'x-signature-version': '1.0',
    'x-signature-nonce': nonce,
    'x-version': 'v2',
    ...(env.WEBULL_ACCESS_TOKEN ? { 'x-access-token': env.WEBULL_ACCESS_TOKEN } : {})
  };
}

function formatAsOfLabel(iso) {
  return `Updated ${new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York', hour: 'numeric', minute: '2-digit', timeZoneName: 'short'
  }).format(new Date(iso))}`;
}
function finiteNumber(value, label) {
  const number = Number(value);
  if (!Number.isFinite(number)) throw new Error(`Invalid ${label}`);
  return number;
}
function round(value, digits) {
  const scale = 10 ** digits;
  return Math.round((value + Number.EPSILON) * scale) / scale;
}
function rfc3986(value) {
  return encodeURIComponent(value).replace(/[!'()*]/g, (character) => `%${character.charCodeAt(0).toString(16).toUpperCase()}`);
}
function requireSecret(env, name) {
  if (!env[name]) throw new Error(`${name} is not configured`);
}
function safeError(error) {
  return String(error && error.message || error).replace(/[^a-zA-Z0-9 ._:-]/g, '').slice(0, 160);
}
