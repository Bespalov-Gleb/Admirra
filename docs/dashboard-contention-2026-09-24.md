# Dashboard/detector lock contention — 24 September 2026

## Incident and evidence

At 13:31 and 13:46 UTC (16:31/16:46 MSK), both APIs exhibited ~10 s
`LockNotAvailable` waits on `clients`. Stack: campaign-highlights →
consumer_freshness.verify → data_requirements.requirements → SELECT FOR UPDATE.
Dashboard summary also waited while writing `last_dashboard_snapshot`.
The synchronous SQL wait in an async handler stalled unrelated requests.

The four safe-read ingress locations retained a 2 s read timeout and the
shared upstream evicted a server after one failure for 10 s. `/auth/me` timed
out against both servers, followed by `no live upstreams` and dashboard 502s.
The two incident bursts had 32 final 5xx. These errors predated the frontend
container restart at 13:47:06 UTC; they were not explained by that deployment.
Canary-named alerts currently cover the balanced production API pool, not only
API2. Their rolling window is 600 s; recovery does not prove the bug is fixed.

FUN KIDS manual jobs were successful: one waited 1.4 s then worked 8.2 s;
another waited 31.9 s then worked 9.8 s. Queue waiting, actual provider sync,
and delayed dashboard/status delivery are separate latency components.

## Change scope

- Detector summary and cross-project reads use PostgreSQL repeatable-read,
  read-only snapshots. Source/coverage readers omit row locks only in this
  explicitly marked connection. Marker and isolation reset after rollback.
- Campaign highlights finish external attribution IO first, then reauthorize
  and read evidence plus metrics in a single snapshot, in a threadpool.
- Default durable consumer paths still lock sources. No freshness guards,
  revision checks, access checks, worker fences or alerts are disabled.
- Optional dashboard visit memory uses a short `FOR UPDATE SKIP LOCKED`
  transaction in a threadpool. Busy projects skip that sample; actual summary
  values are not replaced with zero and no sync is enqueued by the skip.
- Safe-read timeout 2→5 s, bounded next-upstream budget 4→12 s, two attempts
  maximum. Shared pool needs 3 failures within 5 s rather than 1 within 10 s.
  Equal weights retained. General API/mutations/SSE keep retries OFF.

No schema migration, DB/Redis restart, worker/scheduler rollout or shared-cache
activation. This does not change provider latency or queue scheduling policy.

## Verification and artifacts

- Full isolated regression: 1641 passed, 1 skipped, 1 deselected,
  13 subtests passed (934.50 s). Synthetic PostgreSQL/Redis, no production creds.
- Targeted contention tests additionally cover a locked project/integration,
  an uncommitted settings change, MVCC during coverage replacement, connection
  reuse, preservation of durable source locks, skipped/normal visit writes,
  and concurrent detector summary/visit requests.
- Source change: `97924a4`; final packaging change: `60965ca`.
- Initial immutable-image test found missing `ops.render_launch_runtime` in
  the test/ops packaging; final packaging includes it. No running API was
  changed by the failed test. Prepared `97924a4` configs were never activated.
- Final image: `sha256:a43f4ac289996731f4430ceb8c37a6b43dd9003afde134925b672b703faf3d62`.

## Rolling deployment procedure

Use `ops/deploy_dashboard_lockfix.py`: prepare captures exact running env,
mounts/networks/ports, immutable image and private rollback configs. Only
APP_RELEASE differs in the environment. It refuses source image drift.

Release root on each node: `/etc/admirra/releases/dashboard-locks-60965ca`.
Ingress rollback and stage files are in the same root on server1.
`ops/roll_dashboard_ingress.py` validates configuration before a graceful
reload, preserves weights and refuses unrelated configuration changes.

1. Prepare both APIs and ingress, validate the actual immutable image.
2. Drain API2 from ingress; confirm old connections/SSE have drained.
3. Activate and verify API2 locally, including bounded owner-account GETs.
4. Drain API1 (all new requests go to healthy API2); confirm connections drain.
5. Activate and verify API1; restore equal weights.
6. Probe both replicas and public ingress, inspect new 5xx/lock errors and
   existing Prometheus/runtime monitors. No paid AI, reports or payments tested.

If acceptance fails, keep the affected API out of upstream, use the retained
`previous.json` via the deployment helper, verify readiness, then restore
ingress. Never run legacy automation or downgrade/restore the database.

## Production acceptance

Completed **14:35:25 UTC / 17:35 MSK**: equal weights restored after rolling
activation. API2 started 14:33:10 UTC, API1 14:34:42 UTC. Both run release
`60965ca` with the exact same immutable image above.

- Final image without source bind mounts: **57 passed**, 27 warnings (51.84 s).
- API2 local bounded parallel GET probe: **16/16 HTTP200**, max 1435.7 ms.
- Subsequent cross-replica probe: API1 **16/16**, max 1861.0 ms; API2 **16/16**,
  max 1106.6 ms. FUN KIDS and БВК Новый / ВК, current-week summary, detector
  status/highlights, cross-project detector and auth; 2 concurrent requests.
- Public `https://admirra.ru`: **16/16 HTTP200**, max 904.5 ms after balance restore.
  This is a bounded acceptance sample, not a load-test/SLO guarantee.
- At 14:35:57 UTC, both API readiness/host/runtime monitors healthy;
  final-5xx/fallback counters in the last 10 min = 0, Prometheus alerts empty.
  No new LockNotAvailable/ERROR/tracebacks in the new API containers.
- Both APIs: restart count 0, OOM false. Worker/scheduler roles remain healthy
  and were not restarted. Frontend, DB, Redis, schema and business env unchanged.

First API2 attempt automatically rolled back before admission: Docker returned
the same mounts in a different list order and the strict comparison rejected it.
Ops helper `480cb1b` now compares mount dictionaries sorted by destination and
prints only boolean invariant checks (no credentials). All five checks passed
on both final API activations. Traffic continued through API1 during this step.

**Actual current configs:**

- API1: `/etc/admirra/releases/dashboard-locks-60965ca/active.json`, service `backend`,
  Compose project `admirra`. Rollback `previous.json` in that directory.
- API2: `/etc/admirra/releases/dashboard-locks-60965ca-r2/active.json`, service `api`,
  Compose project `admirra-api2`. Rollback `previous.json` in that directory.
- Ingress stages/rollback: server1 `/etc/admirra/releases/dashboard-locks-60965ca/`.
- Ops scripts on both hosts: `/opt/admirra-dashboard-locks/ops/`.

The `97924a4` prepared configs were never active. API2's first `60965ca`
directory is a superseded attempt; use **60965ca-r2** for its current config.
Do not run the former cutover API configs to restart the current release.

Remaining separate issues: queue scheduling latency and legacy live-Metrika
calls are not removed by this patch. Longer observation and owner-browser
verification are still needed; an empty alert list is not a guarantee against
all future incidents. The isolated test database/Redis were removed after tests.
