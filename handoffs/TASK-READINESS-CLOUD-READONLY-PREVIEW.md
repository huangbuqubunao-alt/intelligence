# TASK-READINESS-CLOUD-READONLY-PREVIEW — implementation handoff

## Metadata and scope

- Role: Implementer; sole writer `cloud_preview_writer`; recommendation: **IN_REVIEW**, not accepted or merged.
- Base: `eb02af9f12de2565f51e4afb3eeeeb8b81f8d5d2`.
- Worktree: `/Users/developer/Documents/yia-worktrees/readiness-cloud-readonly-preview`.
- Branch: `codex/task-readiness-cloud-readonly-preview`; head is the commit containing this handoff.
- Source scope: `distillation.py`, `local_api.py`, `runtime_composition.py`, one atomic helper in `state.py`; related backend tests. Root additionally authorized minimal frontend ticket compatibility: `App.tsx`, one bilingual sentence in `uiLanguage.tsx`, its unit assertion, and the existing mocked consent browser fixture assertion.
- No Schema, dependency/lockfile, production configuration or model-qualification change. No actual provider HTTP/model invocation, credential value/.env/Keychain/owner-database access, main change, external action, fee or private upload.

## Implemented contract

`POST /api/v1/videos/{video_id}/cloud-intelligence/review` now returns **200**, not 201. Existing request remains `{command_id?: string}`. It selects only the existing backend tuple and trusted eligible source/canonical Evidence. LOCAL/BILIBILI remain unsupported. It neither reserves nor resolves credentials, checks/consumes budget, creates consent/checkpoints/ledger/Source Runs, nor dispatches. A review is an in-memory ticket, maximum 128 entries per service, five-minute expiry; closing/leaving/restarting has no persistent action. Expired entries are pruned on the next review. Restart or credential-driven service replacement requires a fresh review.

Response is `{review: {execution_id, source_id, video_id, provider, model, verified_input_hash, review_hash, expires_at, output_language, evidence_ids, outgoing_data, outgoing_request, cost_status, disclosure_version, readiness}}`:

- `execution_id` is the prospective canonical reservation identity, **not a persisted task**.
- `verified_input_hash` remains the real VerifiedDistillationInput semantic hash; `review_hash` is a separate opaque 256-bit ticket. `expires_at` is an ISO datetime.
- `outgoing_data` is the current verified semantic projection; `outgoing_request` is the exact fixed adapter's pure request projection (no credential), or null when unsupported/offline test-only. It includes the fixed output bound. No new personal-content logs.
- `cost_status=UNKNOWN`, `disclosure_version=m12-cloud-intelligence-v1`; no free-price or account-quota authority is invented.
- `readiness={can_confirm, blockers, budget_state}`. Blockers include `MODEL_UNQUALIFIED`, `CREDENTIAL_REQUIRED`, `MODEL_UNAVAILABLE`, `EXECUTION_ALREADY_EXISTS`, `INPUT_NOT_SUPPORTED`, and production `CLOUD_SPENDING_POLICY_REQUIRED`. An injected budget without a read-only status is `BUDGET_UNVERIFIED`; affirmative confirmation always checks its current authority. Preview does not pretend that an unperformed account/budget check succeeded.

Confirm request stays `{execution_id, review_hash, authorize:true}`; frontend now sends **review.review_hash**, not verified_input_hash. Missing consent still refuses. Missing backend key/qualification refuses. Stale/forged/expired/restarted/wrong-video/wrong-execution tickets refuse. Server recomputes the entire command/verified input, current language, source/manual readiness, canonical/legal Evidence, policy/preferences and tuple/profile identity. The fixed pure wire builder also validates provider-specific constraints before persistence. Normal production transport authorization, availability, actual credential preflight and budget remain required.

`ProductionDistillationBudget.check` now rejects all non-Ollama routes with `CLOUD_SPENDING_POLICY_REQUIRED`, preserving current local allowance. No production path gains spending admission in this slice. API budget refusal returns 409 `CLOUD_BUDGET_REFUSED` with safe `reason_code`; other live-review refusals return 409 `CLOUD_CONFIRMATION_REFUSED`, unsupported wire input `CLOUD_INPUT_NOT_SUPPORTED`.

## Atomicity and original dispatch boundary

`PersonalizedDistillationService.confirm_cloud_preview` → `SQLiteStateRepository.confirm_and_claim_cloud_execution`:

1. Begin existing SQLite immediate transaction; reject any existing execution before running the injected budget again. Never adopt historical reservations.
2. Recompute/revalidate current authority while the writer lock excludes source/policy writes. No network is performed inside this transaction; fixed cloud preflight only resolves presence of its configured credential.
3. Insert existing `PENDING/RESERVED_NOT_DISPATCHED/count0` shape, insert the existing immutable `USER_CONFIRMATION` consent through its original matching-row trigger, then conditionally update to `DISPATCH_CLAIMED/count1` in the **same transaction**. Any error rolls back all three; no new Schema.
4. Commit, then call the original `_dispatch_and_admit(command, verified_input, decision)`. Output admission, provenance, actual identity, resource accounting, known-error and unknown-result handling are unchanged. The claim still means a call **may follow**, never that a model succeeded.

A concurrent duplicate or a fresh ticket after restart cannot make another invocation or insert a second consent. A crash after commit remains claimed/uncertain and cannot be replayed. A gate refusal before commit leaves no new checkpoint/auth/budget row. If credentials disappear after the committed claim, the original known-pre-dispatch accounting behavior remains: consent/history are retained, not silently deleted; unknown results remain closed. Legacy unconfirmed PENDING rows are neither modified nor omitted from Backup and still need a later bounded cancellation lifecycle.

## Verification

All Python commands use `PYTHONDONTWRITEBYTECODE=1`, explicit `PYTHONPATH` to this worktree's `src`, and `/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python` (the shared editable default is not trusted).

| Check | Result |
|---|---|
| TDD original no-key preview + production budget reproduction | RED: `CLOUD_INTELLIGENCE_UNAVAILABLE`; budget was `allowed=True/RUNTIME_BUDGET_ADMITTED`; then GREEN |
| New confirmation refusal tests before method existed | RED missing confirmation method; then GREEN with real repository snapshots |
| Final focused `pytest tests/integration/test_task022_personalized_distillation.py -k 'cloud_preview or confirmation_refusal or api_confirmation_gates or production_budget_denies or cloud_review_and_confirmation or partial_write' -q --tb=short` | **26 passed**, 17.35s |
| Broader affected regression: task022 + local timed/text/settings + local-content adversarial + Backup + Moonshot/OpenAI adapters | **500 passed**, 419.53s; one expected duplicate-ZIP fixture warning. This run began before the last pure wire-builder/identity-guard hardening; final changed paths were rechecked by the 26-test selection above. |
| Frontend App + model readiness Vitest files | **160 passed**, 10.28s; existing React act warnings remain |
| Frontend TypeScript + Vite production build | PASS; 52 modules, 545ms |
| Strict mypy all `src/youtube_intel` | **121 source files PASS** |
| Ruff no-cache four production files and related backend test | PASS |
| In-memory compile of four production files and backend test | **5 PASS**, no bytecode writes |
| Existing mocked browser consent fixture | `node --check` PASS; distinct input hash/ticket assertion updated; browser fixture not launched |
| `git diff --check` / scoped diff review | PASS; no removed assertions, test skips, configuration/dependency churn, or unrelated changes |

Final focused tests cover repeated no-key/unqualified previews with **all-table SQLite dumps and physical referenced/unrelated DATA bytes unchanged**, dismiss/restart, no credential/budget/HTTP access; unchanged Backup readiness with and without preserved legacy PENDING; forged/expired/restarted review, changed language/policy/Evidence/model/source/link; missing API key/qualification/provider availability and default production budget; rollback after reservation/consent/claim insertion; two-service concurrent duplicate confirmation, known HTTP 429/unknown/success and restart replay prevention. The positive execution test uses an explicit **one-call offline test budget** and injected wire only; it is not provider/model qualification.

Resolved development failures: the first budget test omitted required output_language (fixture corrected before proving the real allowed-true bug); atomic consent initially hit the existing unclaimed-row trigger (fixed by inserting consent before claim within one transaction); the new React fixture lacked available Summary (fixture corrected); the pure wire builder's pre-dispatch exception is RuntimeError-derived, so it is explicitly mapped to a safe zero-write rejection. A wire-layer exception is correctly treated as unknown; the known-failure race fixture instead uses a real typed HTTP 429 error. No test assertion was weakened to conceal these failures.

## Reuse and limits

- DIRECT: existing canonical `_reserved_command`, `_canonical_reservation_evidence`, `_manual_content_ready`, `_eligible`, `_legal_evidence`, VerifiedDistillationInput, fixed adapter request builders, SQLite immediate transactions/constraints/immutable-consent triggers, original dispatch/admission/ledger and Backup checks. Internal source retained from the assigned base/NOTICE.
- DIRECT: Python standard-library json/secrets/threading/datetime/SQLite. No copied third-party code or new dependency; existing frontend libraries reused via an ignored symlink to the existing root worktree node_modules, with no installation.
- Graph-first lookup used indexed root graph; current source AST/file reads used after graph returned no index for the new worktree. Jev unavailable in exposed tools; safe/default workflow retained.
- DEFER: durable preview or new cancellation Schema, actual monetary/account policy, free provider, new tuple/profile qualification, full three-path UI/onboarding, refreshed hardcoded price disclosure, and owner-data acceptance.
- The broader UI still gates entry by its existing credential availability and does not yet render the new full readiness/outgoing DTO. Only safe confirmation-ticket compatibility and truthful no-task copy are included here. Root owns the next UI slice.
- Full 6003/1026 suite and real normal-user provider/BackupRestore acceptance remain the final whole-feature gate. No live account/API was available or used; no real model-path usability is claimed.

## Review / integration

Independent reviewer and Root acceptance pending. Implementer does not mark DONE or integrate. Commit clean and STOP after reporting the SHA.
