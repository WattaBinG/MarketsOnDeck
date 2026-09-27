# Wire and crypto dispatch clock

This separate Cloudflare Worker fires the existing GitHub Actions workflows every
15 minutes, including weekends. The website is still deployed by those workflows;
this Worker does not replace their Python feeds or publish market data itself.
Cron is UTC. The workflow inputs label the scheduled cycle; GitHub does not
automatically deduplicate dispatches with the same input. The workflows serialize
publication, but a repeated fetch can still change content. HTTP 204 means
GitHub accepted a dispatch, not that the refresh or website deployment
completed. Check both Actions run histories and the site's `asOf` fields for actual freshness.

Deployment is intentionally separate from the website's `wrangler.jsonc`:

1. Create a fine-grained GitHub token restricted to `WattaBinG/MarketsOnDeck`,
   with Actions read/write. Store it as the `GITHUB_DISPATCH_TOKEN` secret on
   the dispatcher Worker. Never commit it or echo it in logs.
2. Deploy from this directory with `npx wrangler deploy`, using a Cloudflare
   API token with Workers deployment permissions. Set the secret securely with
   `npx wrangler secret put GITHUB_DISPATCH_TOKEN` in this directory; this
   creates and deploys a new Worker version immediately.
3. Confirm a manual scheduled-handler test and a real cron cycle dispatch
   exactly the expected two workflows. Inspect run status and site `asOf`.
4. Only after a successful cron cycle, remove GitHub's `schedule` event from
   the two workflow files so they do not fire twice. Keep `workflow_dispatch`.
   During the brief transition, the two clocks may dispatch a redundant run;
   concurrent runs serialize; inspect any duplicate and do not assume a no-op.

The dispatcher logs each accepted workflow and cycle, throws on non-204 status
so the Cron Past Events table records failure, and does not log the token. A
GitHub dispatch request is not proof of a completed workflow. Watch failures in
both Cloudflare Cron Past Events and GitHub Actions.
