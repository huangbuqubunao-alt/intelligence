# TASK-READINESS-BIGMODEL-AUDIT — implementation handoff

> 2026-10-27: independent review rejected original candidate896a483 for two confirmed scalar P2 findings. The bounded repair below supersedes its scalar contract; original history/results are retained. Repaired candidate requires independent delta review and Root acceptance.

## Metadata / current state

- Implementer: `/root/bigmodel_audit_writer`, sole writer; no subagent.
- Base: `ea7e74fcab2c5cdc8dfceeef063dd4a4091b1716`.
- Worktree: `/Users/developer/Documents/yia-worktrees/readiness-bigmodel-audit`.
- Branch: `codex/task-readiness-bigmodel-audit`.
- Status: **IN_REVIEW; implementation checks closed, independent review/Root acceptance pending. No main integration.**
- Scope: new042 audit migration, finite audit identity descriptor, state/read/cancellation/long-conflict/BackupRestore compatibility and database doctor latest-version check; necessary related tests. No frontend, local API, provider transport, runtime composition, credentials, production configuration, dependency/lockfile, actual HTTP/model, owner data or main change.

## What changes

Adds only the exact audit tuple `zhipu_bigmodel` / `glm-4.7-flash`; registry membership grants neither quality nor fee/dispatch authority. The existing transport and production-qualification allowlists are unchanged. Production cloud spending remains denied without its later explicit policy; no free entitlement or actual bill is asserted.

Schema41→42 appends two immutable tables. Forty historical migration files001–041 (there is no029) remain byte-identical to the base; hashes are in `.var/bigmodel-audit-checks/old-migration-protection.json`. No old table or row is rewritten by042, no third legacy unidentified-response table is added.

| Table | Fields / contract |
|---|---|
| `distillation_zhipu_cloud_authorizations` | authorization_id PK; execution_id UNIQUE/FK RESTRICT; exact provider/model; verified_input_hash; USER_CONFIRMATION/OWNER_QUALIFICATION; existing disclosure_version; cost_status UNKNOWN; authorized_at. Matches unclaimed PENDING/count0 source/video, with both providers YOUTUBE; UPDATE/DELETE forbidden. |
| `distillation_zhipu_cloud_response_failures` | execution_id PK/FK RESTRICT; exact actual_provider and NULL model; REJECTED_OUTPUT; finite outcome/HTTP status; unknown tokens/cost; optional nonnegative duration; received_at. Requires exact new consent and claimed execution, no competing old/new result receipts; UPDATE/DELETE forbidden. |

The14 resulting042 triggers are:

- Four new consent guards: `distillation_zhipu_cloud_authorization_bound`, immutable_update, immutable_delete, and `distillation_zhipu_cloud_dispatch_requires_authorization`.
- Three replaced finite provider-union guards, preserving every original branch and adding just the exact new pair: `distillation_no_new_http_status_bound`, `distillation_resource_usage_http_status_bound`, `distillation_cloud_failure_outcome_finite`.
- Three new failure guards: `distillation_zhipu_cloud_response_failure_bound`, immutable_update, immutable_delete.
- `local_text_input_proofs_zhipu_cloud_denied` supplements039 without editing its SQL.
- `distillation_zhipu_failure_excludes_usage` and `distillation_zhipu_failure_excludes_no_new` implement the planned reciprocal noncompetition constraint.
- `distillation_zhipu_cloud_insert_requires_zero_invocation` additionally prevents direct SQL from inserting count1 and bypassing the consent-on-UPDATE guard. This necessary new-provider-only completion of the dispatch constraint was reported to Root; it is not a new lifecycle or permission.

`cloud_audit.py` owns the finite tuple, table names and cloud-denial inventory. State permits no legacy unidentified table for this route and routes known HTTP/identity/malformed/202 failures through the dedicated finite failure table. The shared existing claim/admission/usage and NO_NEW persistence are reused. New per-execution readers reject missing consent, accounting conflicts or inconsistent usage; full database checks verify schema, all new consent/execution/failure forward and reverse links. Normal direct repository success/NO_NEW fixtures are explicitly offline, not real model output.

Backup latest version is42 while both allowlists explicitly retain41 and34–40. New strict schema checks apply only to42; old versions cannot smuggle the new audit tables. The expected042 guards are parsed against minimal owning-table stubs, not by replaying legacy ALTER/table-rebuild migrations.039 still compares all its table objects, adding the exact supplemental guard only for42. New table objects/extra triggers/indexes and the replaced finite guards are checked exactly. Startup also verifies the new audit authority. The037 cancellation contract remains Ollama-only; the new failure table is added to local/long conflict inventories only when present, so old archives remain readable. The Moonshot-specific completed-cloud/local-wait Backup exception is unchanged.

## Verification so far

All Python uses existing root `.venv/bin/python`, `PYTHONDONTWRITEBYTECODE=1`, and explicit `PYTHONPATH=/Users/developer/Documents/yia-worktrees/readiness-bigmodel-audit/src`; no default editable checkout is trusted. All DB/DATA are isolated fixtures, no real provider, keychain or owner state.

| Check | Actual result |
|---|---|
| Meaningful initial RED | New pair could claim without consent (`DID NOT RAISE IntegrityError`); authorizing it failed as unsupported. Then new SQL claim gate and finite routing made both positive/refusal paths pass. |
| Old34–41 Backup/Restore→continuous startup migration, all old domain rows and each DATA byte retained; new audit tables empty | Eight parameter cases passed (part of first10PASS / later144PASS). |
| Backup + state + lineage complete files | **144 PASS**,55.97s; one expected duplicate-ZIP fixture warning. |
| task022 + local_text_input_proof + local_content_adversarial + long_input_wait_lifecycle complete files | **264 PASS**,245.77s. |
| Additional offline new-provider repository NO_NEW and admitted-card persistence, real Evidence identity preserved, restart/at-most-once | **2 PASS**,1.71s; no transport/model operation. |
| New rollback/direct count1 insertion/unsupported paid-model guard selection | **2 PASS** before the corrected stage fixture was rerun separately. |
| Rehashed42 ZIP with missing consent-dispatch guard, valid archive permissions and actual modified SQLite bytes | **1 PASS**,1.48s; stage rejected; all live SQL and physical DATA identical. |
| Changed Python syntax compile | **42 files PASS** |
| Ruff on changed Python | PASS |
| Strict mypy all source | **122 source files PASS** |
| `git diff --check` | PASS |
| Fixed43-file affected group | **1458 PASS / 5 FAIL**,1295.45s; one expected duplicate-ZIP warning, source unchanged across run. Five failures were current-schema test expectations, not declared green. |
| Five complete files after minimum expectation repairs | **109 PASS**,50.69s; only those five test hashes changed, all product and other test bytes remain identical to the43-file run. |

Earlier new23-case checks covered429/503/202/identity missing or wrong/malformed, immutable consent/failure, concurrent claim, unknown execution, five corruption refusals and before-claim rollback. Counts above overlap and must not be added as disjoint totals. Final source was frozen before the43-file run; command, before/after source hashes and result are recorded by `.var/bigmodel-audit-checks/run_final_affected.py` in the same directory. It covers35 necessary current-version test files plus8 adapter/adversarial/long-contract files. The final43 result is preserved in `final-result.json` (exit1, source_unchanged true, log SHA256 `2206546d1046861559dcd86633f9d5ccb2384d681a5f2cac76272d9f1ae95f80`). The repair command/log/results and full before/after hashes are in `repairs-*`; exit0, unchanged during run, log SHA256 `1a894331f0445ad07bdaabec0231493d12a2987d208ffba1e9f74f4a675ec6ec`. This is coverage from the43-file run plus five complete repaired files, **not** a claim of a single fresh all-green43-file run. No implementation changed after the43-file run. Full whole-feature regression remains Root's later gate.

## Test updates and resolved development failures

Current schema assertions change41→42, latest migration name/checksum target changes to042, expected migration history **preserves041 then appends042**, table inventory adds exactly two, and future-version refusal uses43. Historical migration lookups and41 fixtures remain41; old supported-archive parameterization is extended to41. No test, assertion or safety case is deleted/skipped or weakened. The broad assertion update initially also changed historical041 names inside full-history expectations. Diff review repaired three before the43-file run; the run then correctly exposed four additional full-history arrays still missing041 and using a26-entry suffix, plus one multiline current-version tuple still41. All five actual failures were inspected: `test_task018_domain_persistence.py::test_fresh_database_applies_m006_with_exact_domain_schema`, `test_task021_source_policy_filtering.py::test_fresh_database_reaches_current_schema_and_preserves_m013`, `test_task023_topic_timeline.py::test_topic_contract_remains_available_with_m013_weekly_foundation`, `test_task023a_source_run_persistence.py::test_m013_fresh_database_preserves_empty_source_runs_and_weeklies`, and `test_task025a_saved_intelligence.py::test_fresh_m014_creates_empty_saved_state`. The four arrays now retain041, append042 and require the full27-entry suffix; the version tuple is42. Their five complete files then passed109 tests. Original failures/log/hash manifests are retained; assertions were strengthened to the complete additive history rather than removed or loosened.

Other resolved evidence:

- New readers initially queried a nonexistent legacy `None` table; routing now explicitly permits absent legacy table and uses the new finite failure ledger.
- The exact schema reference initially replayed all old SQL directly and hit `error in trigger preference_source_target_must_exist: no such table main.source_subscriptions`; replaced with minimal parse-only owning-table stubs. Historical SQL, checksums and strict comparison were not weakened.
- New consent read validation initially received only selected_provider/model; the full checkpoint projection is now read, fixing the new-reader IndexError rather than dropping validation.
- An intended orphan-corruption fixture was correctly rejected by the provider CHECK before corruption; it now explicitly disables FK only on its isolated corruption connection and changes execution_id after removing the immutable guard. Production guards are unchanged.
- The rehashed archive fixture first lost original ZipInfo regular-file attributes and was rejected before schema validation. It then still contained old DB bytes because a test SQLite context manager did not close/checkpoint WAL. The fixture now preserves original ZipInfo, explicitly closes the isolated connection and asserts SQLite bytes really changed before hashing. The production archive/schema checks were never relaxed; the final stage rejection is now the intended strict-guard refusal.

## Risks / remaining gates

New schema is forward-only: a failed042 transaction rolls back all new objects/history/userversion, proved by a dedicated test. No destructive downgrade is supplied. Older programs must not open42 as their own compatible version; rollback pairs the older program with its compatible saved backup through the normal restore flow. This task never migrates formal owner data.

Actual BigModel adapter, provider-specific credentials/settings, model profile/capacity/quality, free entitlement/rate limits, spending admission, real public-sample GUI and whole-feature backend/frontend regression remain future tasks. User registration is pending. Neither source-level audit support nor offline admitted fixtures grant qualification or prove a usable cloud path. Independent review and Root acceptance are pending; no merge/push/deploy or main adoption.

Reuse DIRECT: existing standard-library SQLite/JSON/hash/transactions, immutable consent/claim/NO_NEW/admission/usage, strict Backup/Restore and legacy version contracts. No third-party code copied, new dependency or license action. Exact audit mapping is a small descriptor, not a provider framework or duplicated lifecycle.

## Review / integration

Implementation recommendation: **IN_REVIEW**. Final compile42 changed Python files, Ruff, strict mypy122 and diff checks pass (2026-10-27), and the five full-file expectation repairs have closed the actual failures without product changes. Reviewer must independently inspect the042 SQL, exact schema/row authority, old-version compatibility, no privilege/fee expansion and necessary test-version updates. Root alone accepts/integrates. The implementation commit is the commit containing this handoff; its exact SHA is reported to Root after clean STOP. No further implementation writes after that report.

## 2026-10-27 scalar P2 delta repair (base896a483)

Review proved NULL/BLOB authorization IDs and BLOB64-byte hashes could pass original SQL checks, become coerced strings and authorize a claim. Invalid UTC/calendar strings could pass verification/Backup yet later fail datetime parsing. Those identity/hash and UTC findings are fixed only for the new provider; no025–041 change or old-provider semantic rewrite.

- Both new primary keys explicitly NOT NULL. The failure execution_id NULL was already rejected by its binding trigger, so this is consistency hardening, not a demonstrated failure-ledger bypass. IDs/execution IDs/hashes now require TEXT; hashes remain64 lowercase hex. Integer duration is enforced as its existing reader already required. Other enum strings already have non-null exact literal constraints.
- Both audit times require the exact27-character UTC formatter shape, six fractional digits and a valid calendar/clock. Standard SQLite `strftime` with `+0 seconds` verifies the calendar roundtrip and rejects NULL parsing, normalized overflow dates and24-hour overflow. No custom SQL function or new dependency.
- New-provider consent readers, claim API and reverse verification share raw identity/hash checks and Python parse/formatter roundtrip. They refuse malformed scalars with StateStoreError, and the getter uses already-validated ID/hash without coercion. Shared old-provider handling is unchanged. Failure received_at must match atomic completion time and follow consent. Consent cannot precede execution creation; legitimate authorization after reservation/before claim remains legal, then must fit the claimed execution interval. Microseconds and actual leap-day positives are tested.

Unreleased042 SHA256 changes from `118ac8cb16c6bf7fb87449f4d46ce807311658f12207c319c9e5a33123baadfb` (896 candidate) to `7bddf62ec3fa49a94657b930fd7315a2089642ab7a9b82f2cb76064e1c824d73`. This is **not** an in-place conversion or compatibility claim for retained experimental42 databases. An isolated lineage-corruption test carrying that exact prior checksum proves initialization refuses without rewriting rows. No retained experimental DB was opened/re-signed/reset/upgraded. Fresh isolated fixtures only; all40 old SQL files remain identical.

| Repair evidence | Result |
|---|---|
| Initial NULL direct-insert/getter tests |2RED: `DID NOT RAISE IntegrityError` / `DID NOT RAISE StateStoreError`, then GREEN |
| Nine added BLOB-ID/hash and invalid/noncanonical UTC SQL refusals |9RED before fix, then GREEN |
| Initial repaired SQL/null/known429 selection |12PASS |
| Raw corruption preserving identical schema/guards, reader+claim+verifier refusal; valid formatter/time progression |11PASS |
| SQL calendar/type boundaries, five rehashed malformed42 archives and prior-checksum refusal |15PASS |
| Five complete relevant files: Backup, State, task022, Moonshot/OpenAI adapters |378PASS/1FAIL,176.26s;397 source/test hashes unchanged. Sole failure expected a later SQLite exception instead of the new earlier finite-audit StateStoreError. |
| Complete Backup file after precise expectation update and added direct SQL refusal/count0 assertion |111PASS,48.66s;397 hashes unchanged; only this test file differs from the five-file run, all product/other test bytes identical. |
| Final compile3 changed Python files / Ruff / strict mypy122 / diff |PASS |

The raw-damage helper bypasses CHECK/immutability only on isolated copies, then restores identical schema/guard SQL; readers and semantic verification must independently refuse invalid values. NULL requires a separately weakened test table because NOT NULL cannot be bypassed by the CHECK pragma. Rehashed ZIP cases cover NULL ID, BLOB ID, BLOB hash, invalid authorization UTC and invalid failure UTC: original ZipInfo retained, WAL explicitly flushed, actual changed bytes asserted and manifest recomputed. Every stage refuses and all live SQL rows/DATA bytes remain unchanged. No test is skipped, assertion removed or exception broadened.

Full repair evidence: `.var/bigmodel-scalar-repair/command.json`, `affected.log`, `source-before/after.json`, `result.json`, `backup-final-*`. Five-file log SHA256 `2a0efbee74ea90a2bcb1889eb1713a864f44eee5a1440d10213a9a52188db1bd`. Counts overlap, not disjoint totals; this is not a claim of one all-green five-file rerun or the full whole-feature suite. Earlier8961458PASS/5FAIL+109PASS history above remains unchanged.

Scope is042/state/two related test files/this handoff. No transport, qualification, spending permission, credentials, owner data, dependency/config or main change. Fix commit is reported separately after clean STOP; independent delta review pending.
