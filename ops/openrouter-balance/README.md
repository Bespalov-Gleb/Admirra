# OpenRouter balance → Notifications

Single instance on API-1; Python stdlib + systemd timer. No DB, Redis, Celery,
LLM calls, or application deployment. Uses existing Notifications bot token and
group from registration-notifier, NOT the technical Alertmanager bot. Never
changes registration processing.

## Policy

- GET account credits every 15 minutes (96/day), timeout 20s, no immediate retries.
- Remaining = `total_credits - total_usage`, exact decimal arithmetic.
- Warning ≤ $20, critical ≤ $5. Warning once per transition; critical every 12h.
- On recovery above $20, one recovery notice. A refill still below $20 remains
  a low-balance condition. Initial successful check sends one activation notice.
- Three consecutive API failures (~30–45 minutes): balance UNKNOWN, notify once,
  then at most every 12h. One notice when checks recover. Never treat errors as $0.
- State survives restarts; lock prevents overlap. Persist attempt before sending;
  unconfirmed Telegram outcomes retry after 12h. This trades delayed delivery for
  avoiding 15-minute duplicate spam; Telegram has no exactly-once send key.
- Forecast alerts are a future extension after sufficient spending history;
  this version deliberately uses fixed dollar thresholds, not lifetime-credit %.

## Credentials

Official references:
- https://openrouter.ai/docs/api/api-reference/credits/get-remaining-credits
- https://openrouter.ai/docs/guides/overview/auth/management-api-keys

Create a **Management API key** at https://openrouter.ai/settings/management-keys
in the SAME OpenRouter account/organization funding AdMirra. Prefer an expiration
and set a rotation reminder. This is a powerful administrative key, not a scoped
read-only key; monitor code uses only GET /credits, gateway exposes no key writes.
Never put it into application OPENROUTER_API_KEY, .env, git, logs, or chat.

Protected key file `/etc/admirra/openrouter-balance/management-key` (root, 0600).
systemd LoadCredential hands it to a sandboxed dynamic user, egress only private
gateway 10.78.0.3. Existing Telegram token is read via separate LoadCredential.

## Install / activate

1. Run `python3 -m unittest discover -s ops/openrouter-balance -p 'test_*.py'`.
2. Gateway: add exact GET `/api/v1/credits` block from `ops/ai-gateway/openrouter.conf`
   to active `/etc/nginx/conf.d/admirra-openrouter.conf`, API-1 only. Save old config,
   `nginx -t`, reload. Preserve all other live routes. Verify unauthenticated GET is
   401 and POST rejected. Do NOT open public listener or generic admin proxy.
3. Copy this directory to a root-owned release directory on API-1 and run
   `python3 install.py`. Existing installations are refused. Timer stays disabled.
4. Owner runs (hidden input, never command argument or shell history):

   ```sh
   ssh -t root@91.221.68.90 'python3 /opt/admirra-openrouter-balance/set-key.py'
   ```

   Paste key at hidden prompt. It is verified against GET /credits BEFORE storing.
   On success service starts once and timer is enabled. Same command rotates keys.
5. Check Telegram activation/low balance notice, then:

   ```sh
   systemctl status admirra-openrouter-balance.timer
   journalctl -u admirra-openrouter-balance.service -n 10 --no-pager
   ```

   `balance_check_ok` confirms retrieval, NOT Telegram delivery. Inspect
   `/var/lib/admirra-openrouter-balance/state.json`: `balance_notice.sent=true`
   confirms acknowledged Telegram message. Never print credential files.

## Operations / rollback

- Configuration: `/etc/admirra/openrouter-balance/config.json` (root0600); update
  positive warning/critical thresholds, next invocation reads new values.
- `systemctl disable --now admirra-openrouter-balance.timer` then stop service
  disables monitoring without touching the application or Notifications bot.
- Do not delete state on normal updates: it prevents duplicate notifications.
- Rollback gateway only if active file still matches deployed revision; restore
  saved config then `nginx -t && systemctl reload nginx`.
- Health alerts here use the same Telegram transport as balance notices. A broken
  bot/gateway cannot alert through itself: existing independent infrastructure
  alerts and manual timer/journal checks remain necessary. This is not HA.
