# Detector → AI, OpenRouter comments, public documents

## Scope / status

Implemented locally before the remaining load test and production cutover.
No production application, worker environment or routing changes were deployed.
Existing unrelated working-tree edits are preserved.

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
- No paid OpenRouter generation was performed. Production smoke generation must
  follow application deployment, not precede it with an untracked code change.
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
