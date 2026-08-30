// The Tape — shared Supabase client for all /tape/ pages.
// Publishable key only (safe for the browser — RLS enforces what it can actually do).
window.MarketsOnDeckTape = (function () {
  var SUPABASE_URL = 'https://akagletqrbljvwbagrkt.supabase.co';
  var SUPABASE_PUBLISHABLE_KEY = 'sb_publishable_vBlSpav2017BjgnlIf1sMw_iwsFXX_F';
  var client = null;

  function getClient() {
    if (!client) {
      client = window.supabase.createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY);
    }
    return client;
  }

  return { getClient: getClient };
})();
