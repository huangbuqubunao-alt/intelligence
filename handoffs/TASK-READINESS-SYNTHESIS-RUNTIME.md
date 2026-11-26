# TASK-READINESS-SYNTHESIS-RUNTIME implementation handoff

## Identity and scope

- Role: Implementer, `schema44_guard_resume`; 2026-11-04 Asia/Shanghai.
- Worktree: `/Users/developer/Documents/yia-worktrees/readiness-synthesis-runtime`.
- Branch: `codex/readiness-synthesis-runtime`.
- Exact base: `2c97703b40f79e22cbeb65bf54a243a26338f017`.
- Task: `/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/tasks/TASK-READINESS-SYNTHESIS-RUNTIME.md` and Root's bounded continuation instructions.
- Reuse DIRECT existing PersonalizedDistillationService, fixed official Moonshot HTTP/envelope parser, schema44 proof/reserve/claim/receipt/cancellation, trusted reader, Save/Topic/Evidence and Backup/Restore. ADAPT a finite transport subclass and minimal profile branches. No second execution engine, migration, dependency or default model switch.

## Changes

1. `synthesis_runtime.py`: finite `MoonshotSystemSynthesisTransport`, replaying typed prepared proof and sending the exact canonical body from `provider_wire`. The inherited fixed-host HTTP transport excludes only local endpoint/retry metadata, uses one request and zero retries, and retains the existing envelope/model/timeout/truncation safeguards.
2. `distillation.py`: synthesis review uses one `prepare` full Summary/source/preferences proof, its execution identity and exact wire. Preview remains physically read-only with no credential or budget calls. Confirmation recomputes current input, expiry and transport eligibility, preflights credentials, then uses the trusted injected `SynthesisBudget` with schema44 reserve/atomic consent+claim. Failed never-claimed reservation can be explicitly abandoned; a count1 attempt never resets to0. Duplicate confirmation is refused without dispatch.
3. Decode strictly with the origin-bound seven-field contract. Only the predeclared host operation maps a typed candidate to SYSTEM_INFERENCE; the old self-classified eight-field wire remains invalid. Existing candidate/Evidence validation still runs. Positive and NO_NEW retain authentic raw; invalid/failure terminals attach typed Completion with safe hash/metadata, without storing reasoning or invalid raw.
4. `intelligence_read.py`: current trusted reads now verify synthesis receipts/proof just as recorded-card reads already did. Save and Topic cannot mint trust from changed or missing new receipts/raw/proof; existing validations remain.
5. `local_api.py`: finite backend profiles endpoint and optional profile selection on existing review/confirm endpoints. HTTP cannot supply eligibility, fee policy/caps or endpoints. Existing requests default to legacy. The ordinary cancel endpoint now safely abandons only proof-bound new-family PENDING0, then uses existing immutable cancellation; content DTO exposes such pending reservations separately. Actual claim/cancel race remains serialized by SQLite.
6. `runtime_composition.py`: composes the new adapter with **unqualified eligibility, cloud_enabled=False, credential_available=False, no SynthesisBudget**. Existing `ProductionDistillationBudget` remains cloud-denying. QA launcher credential isolation and no-paid-dispatch switches are unchanged.
7. Frontend: backend-driven finite profile choice for manual cloud review, max_completion_tokens display, complete-Summary disclosure, matching profile on confirm, existing cancel button for proven unclaimed reservations, configured finite capability display and Chinese copy. No redesign.

## Actual verification

All Python commands used the existing `/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`, with `PYTHONPATH=src`; strict tests additionally used `MYPYPATH=src:tests`. Existing frontend node_modules were reused by ignored symlink, without package or lockfile edits.

| Check | Actual result |
|---|---|
| New complete `tests/unit/test_synthesis_runtime.py` | **27 PASS, 29.92s**, `.var/synthesis-runtime/new-runtime-tests.log` |
| Affected backend batch: task022, Moonshot adapter, trusted reader, Topic, saved Intelligence, cloud wait cancel, QA isolation, backup, synthesis persistence, guard literal regression | **512 PASS / 3 FAIL, 275.85s**, `.var/synthesis-runtime/affected-regressions.log`; all three failures were existing latest44 migration-tail omissions listed below |
| Exact three failed schema tests after precise migration-tail repair | **3 PASS, 1.50s**, `.var/synthesis-runtime/latest-migration-tests.log`; no repeat of the512 already-passing tests |
| Strict mypy `src/youtube_intel` plus new runtime test | **PASS, 131 source files** |
| Ruff `src/`, new test, three affected integration test files | **PASS** |
| Compileall source and new test | **PASS** |
| Frontend full `npm test -- --reporter=dot` | **42 files / 1112 PASS, 20.12s**; existing React act warnings retained |
| New finite-profile and unclaimed-cancel UI tests, complete App.cloud-preview file | **31 PASS, 2.10s** (original29 plus2 new); full suite not redundantly repeated after adding tests |
| TypeScript `npm run typecheck` | **PASS**, including final added test |
| Production `npm run build` | **PASS**, 53 modules; isolated build only, not served/deployed |
| Base-to-working diff whitespace check | **PASS** |

The normal API test substitutes **only the external model transport** plus explicitly test-only future qualification/bounded policy. It performs review→confirm→one exact wire→real checkpoint/usage/receipt→trusted current read→Save→Topic→Evidence→restart→populated Backup/Restore. It compares **all table rows, all physical DATA paths/sizes/SHA256** before/after restore and asserts APPLIED and no replay. This is synthetic-content engineering verification, not real model output, acoustic qualification or a real headed macOS GUI claim.

Other new cases cover positive/NO_NEW, old eight fields, wrong refs/model, HTTP429, truncation, timeout/postclaim pre-dispatch uncertainty, missing credential, expiry/language drift/unknown token, missing policy and unqualified direct service, unknown cost reservation retained, concurrent confirmation, restarted PENDING0 safe idempotent cancel, cancel/claim race and another legacy task still blocking Backup. A source-instruction case verifies the instruction stays untrusted data; the simulated NO_NEW response is **not** real-model injection qualification. Tamper cases restore exact original trigger DDL before rejecting changed/missing receipt/raw/proof.

## Failure evidence and precise corrections

- Initial first normal API test reached success but duplicate confirmation leaked `sqlite3.IntegrityError: UNIQUE constraint failed: system_synthesis_input_proofs.execution_id`. The service now maps reservation conflicts to StateStoreError/normal API refusal, without retry or second dispatch. Final27 cases include concurrent and repeated confirmation.
- Development test-construction errors were preserved in tool records: Topic command used unsupported fields (`command_id`/`kind` instead of `association_kind`), and restore test initially assumed a return value / `status` key. Actual contracts require no return and readiness.last_restore.state; corrected the test calls/assertions, without weakening product behavior. An intermediate test insertion placed restart lines in the wrong test; relocated them, retaining restart assertions.
- Initial strict checking identified optional-language narrowing, private re-export access and wire Protocol parameter-name mismatches; fixed actual annotations/imports/invocation names, without ignore/suppression.
- Backend512/3 failure keys: `test_fresh_database_reaches_current_schema_with_integrated_schema`, `test_topic_contract_remains_available_with_m013_weekly_foundation`, `test_fresh_m014_creates_empty_saved_state`. All asserted version44 but listed migrations only through043 and sliced28 entries. The separate test-only commit appends exact044 and uses29, preserving every old expected migration and all assertions. Targeted3/3 pass is recorded separately from the original512-pass batch.
- No skipped/deleted/weakened tests, changed scripts or hidden failures.

## Remaining blockers and non-claims

- **Normal injected engineering path works ≠ ordinary paid product is usable.** Real K3.1-pro remains UNQUALIFIED. Its actual quality acceptance and a user-configurable bounded budget/authorization policy are both still genuine blockers; this work did not implement a new budget system. ProductionDistillationBudget still refuses all cloud spending.
- No real cloud/model/Native Keychain access, credential write, paid action or new qualification receipt. No production configuration/data, original Antigravity worktree or formal owner data touched. No main merge/push/deployment.
- Full global backend regression and real headed macOS/core user acceptance remain for the final accepted source freeze. Frontend build is an isolated artifact, not a served revision claim.
- Root delta review pending. Suggested status **IN_REVIEW**; implementer clean STOP after the bounded commits. No final Goal/main-adoption success asserted.

## Root delta follow-up — 2026-11-04

Root's first independent review requested three local corrections, then reproduced a fourth P1 on a retained public-data fixture. These are resolved in one bounded follow-up, without new schema, policy authority, credentials or model calls:

- Complete-Summary disclosure now requires the new profile **and** the actual outgoing Summary message marker, after a review exists. Legacy English/Chinese reviews explicitly assert that the claim is absent.
- Both finite Moonshot routes link directly to `#Settings/models/moonshot` with the current Content return hash. Legacy bilingual and new-profile deep-link assertions cover the route. `CLOUD_EXECUTION_DISABLED` has separate clear English/Chinese copy; it is not called model unqualification.
- Each raw/missing-receipt/proof tamper case now creates a real Topic association before corruption, restores exact trigger DDL, refuses a new Topic association after corruption, and reads the existing Topic as DEGRADED with unavailable contribution. The fresh Topic remains empty; existing read_current/Save/Backup rejection assertions remain.
- Root's public-fixture startup failed in `initialize → verify_execution → _replay → _file` with `StateStoreError: Synthesis source file unavailable`: factory initialization preceded the trusted DATA binding. The minimal fix binds the factory's already-resolved configured DATA root before `initialize`; RuntimeOperations may bind the same root again, as the existing binding contract permits. No path is inferred from user source files.
- Two new regression cases use the actual runtime factory, which constructs fresh repositories itself, with no manual pre-initialize bind. Positive Save/Topic state and zero-call cancelled proof both survive factory restart; factory Backup/Restore followed by another actual factory startup preserves all table rows/DATA hashes, reports APPLIED and does not dispatch again. Fake credential stores and disabled environment fallback/cloud execution isolate the tests.

Actual follow-up checks:

| Check | Result |
|---|---|
| Complete new runtime test file (including Topic tamper and actual-factory cases) | **29 PASS, 34.98s**, `.var/synthesis-runtime/root-delta-runtime-tests.log` |
| Complete existing runtime-composition + QA-launch-isolation files | **44 PASS, 47.12s**, `.var/synthesis-runtime/root-delta-factory-regressions.log` |
| Complete cloud preview UI test file, final assertions | **32 PASS, 2.15s** |
| Strict source + new runtime test | **131 files PASS** |
| Ruff on changed Python files, compileall, delta diff check | **PASS** |
| Final TypeScript and isolated production build | **PASS**, 53 modules |

The original515-case affected batch was not repeated. The real production model qualification and configurable bounded spending-policy blockers remain unchanged. Root's follow-up acceptance is still pending.
