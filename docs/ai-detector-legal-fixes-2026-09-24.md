# Detector → AI, OpenRouter comments, public documents

## Scope / status

Deployed as a narrow legacy-runtime hotfix on 24.09.2026 (23.09 22:31 UTC),
before the remaining DevOps load test and production cutover. Worker topology,
schema and automation were not switched. Existing unrelated working-tree edits
are preserved. The production overlay is NOT the whole pending DevOps candidate.

### Detector → chat

- Dashboard detector sidebar, KPI alert popover, campaign alert and project-card
  preview open `/ai`, not the legacy `/ai-analysis`.
- A fresh chat receives the project ID/name, explicit selected dates, metric,
  deviation and detector hypothesis. The question asks the agent to verify facts
  using its authorized tools; a hypothesis is not declared a proven cause.
- Same-tab intent expires after five minutes, is account-bound, and is consumed
  once. The URL contains only a random nonce, not project data or a prompt.
- Wait for the model catalog before sending. If unavailable, retain a draft and
  explain the failure. Refresh/back/reopening the consumed URL cannot auto-charge.
- Existing chat request IDs, quota checks and backend authorization remain in use.

### Comments

- Dashboard comments and short comments accompanying report deliveries now use
  `ai/comment_llm.py`: non-streaming OpenRouter `/chat/completions`.
- Required: `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL` (the existing private AI
  gateway). Optional: `AI_COMMENT_MODEL`; otherwise `OPENROUTER_DEFAULT_MODEL`.
- Independent of `AI_ASSISTANT_PROVIDER`: no silent fallback to another vendor.
- Preserve snapshot/freshness checks, prompt v2, JSON/number validation and safe
  fallback. Network calls release their HTTP client and do not automatically retry.
- Dashboard audit rows use the actual returned model and `usage.cost` in USD.
  Missing cost is NULL, not a stale Byesu estimate; RUB is unknown, not fabricated.
- Full legacy reports, legacy chat and detector LLM retain their old configuration;
  do not remove `OPENAI_*` credentials as part of this change.
- Worker credential allowlist includes the necessary OpenRouter settings. Prepared
  worker/scheduler env files must be refreshed before those candidate roles start.
- Contract reference: [OpenRouter API](https://openrouter.ai/docs/api_reference/overview).

### Documents

- Public canonical URLs remain `/admirra/agreement.html`,
  `/admirra/user-agreement.html`, `/admirra/personal-data.html`.
- New responsive layout uses current landing colors and local Gilroy fonts.
  Static documents do not enter Vue's authentication guard.
- Entire legal article text is unchanged, checked by SHA-256 regression tests.
- Authentication footer placeholders now link to the actual documents.
- `/admirra/index.html` contains only a fallback redirect; Nginx redirects it and
  `/admirra/` to `/`. Legacy static page navigation now points to the new landing.
- Root and `/landing-new/` document aliases redirect to the canonical documents;
  `/terms` and `/offerta` point to their respective existing documents.
- The current production landing already links to these canonical document URLs.
  `landing/index.html` is a separate, uncommitted owner draft: only its document
  links were corrected locally; the draft is NOT included in this commit.
- No separate privacy-policy text exists in the repository. Do not label consent
  or a user agreement as a privacy policy; request the actual approved policy.

## Verification

- 90 backend tests passed in isolated PostgreSQL/Redis containers on server 2,
  with no external network/provider calls or production credentials.
- 11 Node tests passed (handoff, request identity, legal content/navigation).
- Vite production build passed; Nginx configuration test passed in a separate
  container with networking disabled.
- Isolated browser check: a detector question auto-sends once with project/dates
  and a request ID; reload and reopening its URL do not resend it.
- Legal page visual checks at 1440px and 390px: no horizontal overflow.
- Existing SPA legacy scripts report `Swiper is not defined` / `classList` errors
  in the isolated browser; the new handoff passed despite these. Legal pages do
  not load those scripts. This change does not refactor global legacy SPA assets.
- Before deployment no paid generation was performed. Production smoke results
  after deployment are recorded below.
- Read-only production configuration/catalog check: the OpenRouter key is present,
  base host is the private gateway `10.78.0.3`, and the effective default model
  `anthropic/claude-sonnet-5` exists and supports JSON response format/reasoning.

## Deployment acceptance

1. Ship backend changes and frontend build plus updated public HTML/CSS; an
   assets-only frontend overlay will NOT update legal documents.
2. Apply the document redirect locations to the active frontend Nginx config,
   preserving production proxy/DevOps overlays; run `nginx -t` before reload.
3. Confirm the OpenRouter key/base/model on every process that generates comments,
   including the future workers. Refresh scoped env through the existing tool,
   not a blanket compose rebuild or a full secret dump.
4. On a test project click detector “Спросить AI”: correct project and dates,
   a new chat, one automatically sent message. Refresh must not repeat the call.
5. Generate one fresh dashboard comment, confirm model/usage/cost in its audit row;
   check the delivery comment path on a test report without customer distribution.
6. Signed-out and signed-in browsers: footer links open public modern documents,
   old landing aliases lead to `/`, not signup; check desktop and mobile.

The load test and full production cutover remain separate, not completed here.

## Production release / acceptance

- Feature commit: `2b6f9ad`. Frontend source was copied from the last deployed
  signup release and cleanly rebuilt: baseline app HTML SHA-256 matched production
  `ab0c87aa1d3b381e94aecc0095f8a5282c72aef00f089ccf6ddbb07893515aa4`.
  Only the seven scoped source files and nine public document assets changed.
  Owner drafts and pending DevOps frontend changes were not shipped.
- Backend: only the feature diff applied to the running `report_generator.py`
  (baseline SHA-256 `53b729c8348377477a2c161cb67df9088bd3292b92f0672f5c7d2a6e2be2eecb`)
  plus new `ai/comment_llm.py`. No pending snapshot/worker imports were introduced.
- Overlay context: `/opt/admirra-ai-legal-release` on API1. Both images were built
  from pinned, locally tagged production images, retaining old frontend chunks.
- Additional image-level regression: **26 passed**, 2 candidate-only tests
  deselected (snapshot signature and future worker env); network disabled,
  synthetic secrets, read-only filesystem. Nginx configuration test passed.
- Read-only release preflight: schema `cc3d4e5f6a7b`; queued/running sync, sending
  reports, recent AI and payment intents all zero. Backup service success,
  completed 23.09 22:11 UTC. No schema migration was run.
- Rollback configs: `/etc/admirra/releases/ai-legal-20260923T223158Z/`.
  `backend-previous.json` and `frontend-previous.json` preserve old images/env/mounts.
  New frontend Nginx is a versioned bind mount in this directory; `/root/Admirra/nginx.conf`
  was NOT overwritten. Restore backend/ready then frontend with scoped Compose
  `up -d --no-deps --no-build --pull never`; do not use blanket compose up.
- Active backend: `sha256:875ab667e2c62e95b703654f9ea6419118668d14a4b16cf5b19c4f356d153264`.
- Active frontend: `sha256:c66a5778d2cebb2d834ae5521e37c049618292f8162818cbb6a6b66e147a43be`.
- Environment, ports and all other mounts match their previous runtime. Automation
  and admin frontend container IDs unchanged; both updated services have 0 restarts.
  Automatic report-comment generation runs in backend's legacy report scheduler,
  not in automation's SQL/Sheets weekly export job.
- Public signed-out browser: all three documents have new titles/layout and remain
  on their document URLs. Old landing reaches `/`; root document aliases are 301.
- Approved test account: actual dashboard detector button opened `/ai`, posted
  exactly one request with the project ID, period and request ID. Live SSE returned
  HTTP 200, 14 tool start/end events and a 2,627-character final answer, no error.
  Browser reload did not generate a second chat request. One normal test chat was
  created; its normal account quota applies.
- Fresh dashboard comment for 14–20 September: HTTP 200, 963 characters, 21.954 s.
  OpenRouter `anthropic/claude-sonnet-5`: first attempt failed text validation,
  second passed. Audit costs $0.016304 + $0.015580 = **$0.031884**; tokens
  5,272/576 then 5,380/482. The post-validator was not disabled for the smoke.
  No reports or messages were distributed to customers.
- Future cutover rollback manifest now reflects these images. The older immutable
  DevOps candidate `a5635d5` does not contain this feature: rebuild the candidate
  from current reviewed source and refresh scoped OpenRouter worker env before
  the final multi-host load test/cutover. Do not roll this hotfix back inadvertently.
