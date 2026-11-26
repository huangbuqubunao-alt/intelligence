# TASK-READINESS-CLOUD-PREVIEW-REVIEW

## Verdict

**APPROVE — bounded engineering slice only.** No confirmed P0/P1/P2 finding in the reviewed change. This is not model qualification, approval of paid execution, a complete ordinary-user path, or main adoption.

- Independent reviewer: `/root/cloud_preview_review`.
- Author: `bcb2df474a687395b3aa26732241502bc6c094af`.
- Diff base: `eb02af9f12de2565f51e4afb3eeeeb8b81f8d5d2`.
- Review worktree: `/Users/developer/Documents/yia-worktrees/readiness-cloud-preview-review`.
- Review source baseline: `fd422e2ed1c4bd0eb397dbd33eda9b79c14f2b3a`; its only additions to the author commit are Root's review task and public-source planning documents. Product/test files match the fixed author commit byte-for-byte (`git diff --quiet ... -- src frontend/src frontend/m13-cloud-consent.e2e.mjs tests`).
- Only this handoff is committed by the reviewer. No business code, tests, dependencies, Schema, credential, owner data, production configuration or main change.

## Review basis and findings

Read repository collaboration/role rules, current status, PRD, System Design, Product Constitution and V1 Product Spec cloud/data/cost requirements, reuse register, original implementation task, review task/prompt and author handoff. Used the code-review-and-quality skill. Graph-first discovery located the current service/repository/transport boundaries; explicit current-source AST reads were used because graph offsets can be stale. Jev was not exposed; the strong/default independent review was retained. No subagent was spawned.

### Correctness and persistence

The preview derives the same canonical Evidence set, trusted projection and reservation identity without inserting a checkpoint or consent. Pure fixed transport request building happens without credential resolution or HTTP. Preview with missing credential/qualification reports blockers instead of acquiring permission. Its prospective execution identifier is not evidence that a task was created.

Confirmation binds the opaque ticket to video/execution, expiration and the full recomputed command/input. Source, policy, language, model/profile identity and legal/canonical Evidence are checked again. The existing SQLite `BEGIN IMMEDIATE` excludes competing database writers during validation and insertion. The new helper checks for any prior execution before checking budget, then inserts the existing reservation shape, matching immutable consent and count-one dispatch claim in one transaction. Original provider-specific SQL triggers still enforce the consent-before-claim ordering. Injection at each of the three write boundaries rolls back all SQL rows. Actual transport dispatch is after commit and uses the original admission/accounting code.

Concurrent duplicate confirmation cannot make a second claim/consent. Existing or restarted executions are not adopted/replayed. A crash after durable claim remains a possible invocation, not a successful result. Known HTTP429 and unknown transport outcomes keep their existing distinct terminal/closed behavior. Historical PENDING records are not deleted or removed from Backup checks. The original local path and NO_NEW/admission tests remain green.

### Security, architecture and performance

Finite existing provider/model routes and canonical input remain server-owned; no arbitrary endpoint, credential, private upload, model substitution or new eligibility is accepted. SQL values remain parameterized; dynamic audit table names come only from the existing finite resolver. No HTTP is executed under the transaction. The finite cloud preflight checks credential presence only; no secret is returned to the API.

Production cloud spending is deliberately denied when there is no implemented spending policy; local Ollama allowance is preserved. No concrete free-price, account quota or monetary cap is invented by this slice. The atomic helper is a small extension of existing state/consent/claim contracts, rather than a second execution system. The preview cache is bounded to 128 entries, protected by a lock and pruned on subsequent previews; expired tickets cannot confirm. The dense local formatting is consistent with the surrounding scoped implementation and does not obscure a correctness issue warranting a blocking finding.

### Frontend and tests

The frontend change sends `review_hash` as an opaque ticket rather than reusing the verified semantic input hash. The two identities are intentionally distinct in the new unit/browser fixtures. The changed old API assertions reflect a deliberate side-effect-free 200 response and add missing-key/no-checkpoint assertions; they do not remove or weaken a safety check. No test is skipped, deleted or hidden. Existing e2e fixture assertion was updated, not treated as a real API/model result.

The frontend still gates the preview entry on its old cloud availability and does not yet present the new full outgoing-request/readiness DTO. That is an explicitly deferred next UI slice, not a claim made by this implementation. Root must finish it before claiming the user-facing cloud path usable.

## Independent verification on the fixed source

All Python checks used `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=/Users/developer/Documents/yia-worktrees/readiness-cloud-preview-review/src` and `/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`. Only isolated temporary databases/DATA and injected offline transports were used. No real provider/model operation, credential resolution, owner database, external upload or fee occurred.

| Check | Independent result |
|---|---|
| In-memory `compile` of four production files plus related integration test, before tests | **5 PASS** |
| `pytest tests/integration/test_task022_personalized_distillation.py -k 'cloud_preview or confirmation_refusal or api_confirmation_gates or production_budget_denies or cloud_review_and_confirmation or partial_write' -q --tb=short` | **26 PASS**, 17.25s |
| Entire `tests/integration/test_task022_personalized_distillation.py -q --tb=short` | **162 PASS**, 101.08s; includes the 26 above, not an additional disjoint set |
| `pytest tests/unit/test_moonshot_distillation_adapter.py tests/unit/test_openai_distillation_adapter.py tests/unit/test_backup_restore.py tests/integration/test_local_content_adversarial.py -q --tb=short` | **160 PASS**, 50.08s; one expected duplicate-path ZIP fixture warning |
| App Vitest file | **148 PASS**, 10.33s total; existing React `act` warnings |
| Correct `App.model-readiness.test.tsx` Vitest file, separately | **12 PASS**, 1.17s total |
| TypeScript `npm run typecheck` | PASS |
| `npm run build` | PASS; 52 modules, Vite546ms |
| `ruff check --no-cache` on four production files and related backend test | PASS |
| `mypy --strict --cache-dir=/tmp/intelligence-preview-review-mypy-20261026 src/youtube_intel` | **121 source files PASS** |
| `node --check frontend/m13-cloud-consent.e2e.mjs` | PASS; browser script not launched |
| Fixed author diff check and product/test equality check | PASS |

Frontend verification reused the already installed root worktree's dependency tree through an ignored `frontend/node_modules` symlink; no installation, lockfile or toolchain change. The first frontend command named a nonexistent `modelReadiness.test.ts` alongside the App file; Vitest consequently ran only App148. This was noticed, the correct `App.model-readiness.test.tsx` file was then run separately for12, and counts are reported separately rather than incorrectly claiming the first command ran160.

An additional independent inline probe imported existing fixture builders into an isolated temporary repository, without modifying any test. After129 previews it verified cache size128 and first-ticket eviction, wrong-video and wrong-execution rejection, and rejection at exactly five minutes. Every SQLite row remained identical, and sentinel credential/HTTP resolvers were never called. Existing focused tests separately compare every SQL table and all physical fixture DATA bytes, unchanged Backup readiness with/without preserved legacy PENDING, current-gate refusals, partial-write rollback and duplicate confirmation across services/restart.

## Supplemental boundary assessment and remaining work

- Author handoff wording correction: `CloudDistillationPreDispatchError` directly inherits `Exception`, not `RuntimeError`. The implementation explicitly catches that exact class and maps it to a zero-write refusal, so the inheritance-description error is documentary, not an uncaught-error defect. Original author evidence was not rewritten.
- `now` passed to persistence is captured before acquiring the writer lock, but expiration is checked using a fresh clock inside `validate_current`; an expired ticket cannot pass because its audit timestamp was captured earlier.
- Current canonical identities include the finite provider's prompt/profile version; source replacement/restart loses ephemeral tickets. The fixed current request builders have no user-editable runtime output-budget/profile. If a later task introduces dynamic wire controls, it must bind the exact request/profile, not rely on this review as approval for mutable wire settings.
- An injected budget with no preview status is explicitly `BUDGET_UNVERIFIED`; `can_confirm` permits attempting a fresh authoritative confirmation, not promising spending admission. The only current production budget advertises `CLOUD_SPENDING_POLICY_REQUIRED` and blocks. A future actual monetary reservation must participate safely in transaction/rollback semantics; the present `check` protocol is not reviewed as a transactional spending implementation.
- The fresh zero-write refusal guarantee is proven for this actual production budget and offline test budgets. A future arbitrary side-effectful external budget implementation is not covered merely because SQL rollback exists.
- Real monetary policy/free-provider eligibility, refreshed price/provider UI, keyless UI access and readiness display, first-run setup, legacy zero-call PENDING cancellation, actual provider quality, real macOS GUI/complete BackupRestore path, final full backend/frontend regression and main/served revision verification remain Root's subsequent gates. Historical6003/1026 are not rebranded as fresh whole-feature runs here.
- Qualification stays unchanged. Configuration, HTTP reachability and offline injected success are not proof of a usable or qualified cloud model. No adoption or release is authorized by this report.

Reuse: DIRECT existing canonical Evidence/projection, pure request builders, standard-library SQLite/JSON/secrets/time/locking, existing immutable SQL guards, original dispatch/admission/usage and Backup checks. No third-party code was copied and no new license/dependency action occurred. No confirmed finding requires an implementation repair within this bounded slice; Root retains acceptance/integration authority.
