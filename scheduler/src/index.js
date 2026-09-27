const API = "https://api.github.com/repos/WattaBinG/MarketsOnDeck/actions/workflows";
const WORKFLOWS = ["refresh-wire.yml", "refresh-crypto.yml"];
const WATCH_WORKFLOW = "refresh-watch-today.yml";

export async function dispatchCycle(controller, env, fetcher = fetch) {
  if (!env.GITHUB_DISPATCH_TOKEN) throw new Error("Missing GITHUB_DISPATCH_TOKEN");
  const cycle = new Date(controller.scheduledTime).toISOString();
  const dueWorkflows = controller.cron === "0 23 * * 0-4" ? [WATCH_WORKFLOW] : WORKFLOWS;
  const results = await Promise.allSettled(dueWorkflows.map(async (workflow) => {
    const response = await fetcher(`${API}/${workflow}/dispatches`, {
      method: "POST",
      headers: {
        "Accept": "application/vnd.github+json",
        "Authorization": `Bearer ${env.GITHUB_DISPATCH_TOKEN}`,
        "Content-Type": "application/json",
        "User-Agent": "MarketsOnDeck-refresh-dispatcher",
        "X-GitHub-Api-Version": "2022-11-28"
      },
      body: JSON.stringify({ref: "main", inputs: {cycle}})
    });
    if (response.status !== 204) {
      throw new Error(`${workflow} dispatch rejected: HTTP ${response.status}`);
    }
    console.log(JSON.stringify({workflow, cycle, status: "accepted"}));
  }));
  const failures = results.filter((result) => result.status === "rejected");
  if (failures.length) {
    throw new Error(failures.map(({reason}) => String(reason)).join("; "));
  }
}

export default {
  async scheduled(controller, env) {
    await dispatchCycle(controller, env);
  }
};
