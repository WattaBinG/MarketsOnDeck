# Market data methodology

The ticker has one basis for every US stock and ETF:

- `price`: the latest Webull OpenAPI snapshot price returned for the symbol.
- `priorClose`: Webull's `pre_close`, defined here as the immediately preceding regular-session official close.
- `change`: `price - priorClose`.
- `changePercent`: `(price - priorClose) / priorClose * 100`.

The site calculates both change fields itself. It does not display Webull's supplied change fields and does not back-solve a prior close from a rounded percentage. This prevents displayed prices and percentages from using different bases.

During premarket or after-hours trading, the latest extended-hours price may be shown, but its change remains measured from the prior regular-session close. `asOf` comes from the newest `last_trade_time` in the response. The site label renders that timestamp in Eastern Time.

## Refresh and failure behavior

The Worker endpoint `/api/ticker` fetches Webull snapshots and caches a successful response for 15 minutes. A Cloudflare Cron Trigger also runs every 15 minutes. If Webull is unavailable or credentials are missing, the endpoint serves the checked-in `/assets/ticker.json` snapshot and marks the response with `x-marketsondeck-source: static-fallback` rather than inventing or partially updating values.

Cloudflare Cron Triggers run on UTC and can be delayed. The request path therefore refreshes its own expired cache instead of assuming every scheduled run fired exactly on time.

## Required deployment configuration

Store these as Cloudflare Worker secrets. Never commit them:

- `WEBULL_APP_KEY`
- `WEBULL_APP_SECRET`
- `WEBULL_ACCESS_TOKEN` only if the Webull OpenAPI application requires 2FA token authentication

`WEBULL_API_HOST` defaults to `api.webull.com` in `wrangler.jsonc` and can be pointed at Webull's sandbox during setup.

Webull requires a separate OpenAPI market-data subscription for US stocks and ETFs. A normal Webull app or brokerage login does not grant this API entitlement. Before production deployment, confirm that the subscription and data license permit public website display/redistribution.

No brokerage account, holdings, orders, or trading endpoint is read or changed by this implementation. It calls only Webull's market-data snapshot endpoint.
