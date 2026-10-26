# TASK-READINESS-BIGMODEL-AUDIT-REVIEW

## Verdict and scope

**REJECT `896a4834a745712be59c0f93a6adc98328b4adc1`: two P2 audit-integrity findings require repair.** No confirmed P0/P1 finding. Passing ordinary tests do not override the independent corruption counterexamples below.

- Reviewer: `/root/bigmodel_audit_review`, independent new conversation.
- Base: `ea7e74fcab2c5cdc8dfceeef063dd4a4091b1716`.
- Fixed author: `896a4834a745712be59c0f93a6adc98328b4adc1`.
- Review worktree: `/Users/hua/Documents/yia-worktrees/readiness-bigmodel-audit-review`; branch `codex/task-readiness-bigmodel-audit-review`.
- Review source baseline: `b32b0c647ffb944dac85ca0912a1fc38a0f546ab`, whose only additions to the author are Root's review task/prompt. Product/test files remain byte-for-byte equal to the fixed author.
- Only this report is written by the reviewer. No implementation/test/Schema repair, dependency, configuration, credential, provider/model call, owner data, main or Root GUI service/browser change. Reported 2026-10-27.

## Findings

### P2-01 — malformed consent identity and input hash pass SQL, readers, claim and Backup/Restore

Locations: `src/youtube_intel/migrations/042_add_zhipu_cloud_execution_audit.sql:3` and `:7`; `state.py:4602` (`_validate_zhipu_execution`), `:4632` (`verify_cloud_audit_database`), and `:10839` (`get_cloud_execution_authorization`).

SQLite permits NULL in a non-INTEGER `TEXT PRIMARY KEY` without explicit `NOT NULL`; the length CHECK evaluates NULL rather than false. TEXT affinity also does not turn BLOB values into text, while the current length/GLOB predicates admit an ASCII BLOB. The new per-execution and full-database validators inspect pair/binding/ordering but do not validate these raw scalar types. The getter then applies `str(...)`, disguising malformed authority as a different string.

Three independent isolated probes, using the existing `_workspace` and `_zhipu_request` builders from `tests/unit/test_backup_restore.py`, created a genuine matching public-source reservation and inserted all nine new consent columns directly, with no guards removed. All other fields used the valid exact pair, USER_CONFIRMATION, existing disclosure/cost literals and `format_utc_datetime(NOW)`:

| Single malformed field | Observed reader result | Observed authority result |
|---|---|---|
| `authorization_id=None` | `authorization_id == "None"` | claim allowed; strict database verifier passed; after a finite offline HTTP429 failure, real backup creation and restore staging passed |
| `authorization_id=b"blob-identity-sixteen"` | `authorization_id == "b'blob-identity-sixteen'"` | SQL stored typeof=blob; claim allowed and strict database verifier passed |
| `verified_input_hash=b"a"*64` | coerced `"b'aaaa…'"`, length67 rather than a64-hex input identity | claim allowed; strict verifier, real backup creation and restore staging passed |

These are offline storage/claim counterexamples, not real provider dispatch or evidence of a fee/qualification bypass. They establish that an invalid audit identity/input hash can be treated as authoritative and accepted from a backup, contrary to the new strict audit contract.

Required minimal repair: enforce a non-null textual identity and textual64-lowercase-hex input hash in the new042 authority, and validate raw values in the new provider's reader/reverse verification before any coercion or claim reliance. Add SQL rejection plus raw-corruption/rehash-and-stage refusal coverage. Keep historical025–041 unchanged; no generic old-schema rewrite is requested.

### P2-02 — invalid audit UTC times are accepted into backups but break ordinary reads

Locations: new042 `authorized_at` and failure `received_at` length predicates; `state.py:4602`, `:4632`, and `:10331` (`_validate_cloud_response_failure_row`).

Length and lexical ordering do not prove a valid UTC timestamp. Independently reproduced on the fixed author:

1. Insert a consent with a valid textual identity/hash and `authorized_at="0"*20`. Its SQL guard accepts it, count-one claim succeeds, and a finite offline429 failure can be persisted. `verify_cloud_audit_database`, real `create_backup` and `stage_restore` all pass. `get_cloud_execution_authorization` then raises `ValueError: year 0 is out of range`.
2. Start with a valid consent and claim; on the isolated corruption connection, move the matching PENDING checkpoint to REJECTED_OUTPUT/ADMITTED and insert a finite429 new failure with `received_at="9999-99-99T99:99:99Z"`. No schema guard is removed. Strict database verification and real backup/stage again pass, but `get_distillation_resource_usage` raises `ValueError: month must be in 1..12`.

The archive therefore passes the new strict audit boundary despite producing an unreadable authorization/activity record after restore. Required repair: validate actual UTC date/time values and ordering in the new consent/failure verification paths, with safe rejection of malformed values before trusting or restoring them; cover both timestamps. Do not extend this repair into historical audit migration changes.

### Explicitly checked non-finding

The new failure table's nullable-looking `execution_id TEXT PRIMARY KEY` does **not** reproduce the same NULL authorization hole: direct insertion with execution_id NULL is rejected by its binding trigger (`cloud response failure requires one claimed authorized execution`). This is not reported as another defect.

## Independent checks

Python commands used `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=/Users/hua/Documents/yia-worktrees/readiness-bigmodel-audit-review/src` and `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`. Only isolated pytest/TmpDirectory SQLite/DATA and offline fixture receipts were used.

| Check | Actual result |
|---|---|
| In-memory compile of every changed Python file, before tests | **42 PASS** |
| Forty packaged historical SQL migrations001–041 (no029), each compared to base bytes | **40 identical** |
| `pytest -p no:cacheprovider tests/unit/test_backup_restore.py tests/integration/test_state_store.py tests/integration/test_task016c_phase_h2c_lineage_schema.py tests/integration/test_task018_domain_persistence.py tests/integration/test_task021_source_policy_filtering.py tests/integration/test_task023_topic_timeline.py tests/integration/test_task023a_source_run_persistence.py tests/integration/test_task025a_saved_intelligence.py -q --tb=short` | **256 PASS**,107.38s; one expected duplicate-path ZIP fixture warning |
| Ruff no-cache on every changed Python file | PASS |
| `mypy --strict --cache-dir=/tmp/intelligence-bigmodel-review-mypy-20261027 src/youtube_intel` | **122 source files PASS** |
| Fixed-author diff check and product/test equality to reviewer baseline | PASS |
| Independent direct SQL/scalar/backup probes above | **Finding reproduced**; normal passing tests do not cover these cases |

The256-test group includes all five complete expectation-repair files, eight old34–41 archive cases,42 audit and corruption guards, rollback and existing state/lineage contracts. The all-row/all-DATA fixture comparisons were inspected: old tables and their original migration history are retained across normal restore/startup migration, new audit tables remain empty, and each physical DATA file is compared. This is fixture evidence, not a formal-user-data or Root GUI assertion.

Author's two-run history was independently checked, not relabeled as a single green run: original43-file run **1458 PASS / 5 FAIL**, exit1/source_unchanged true, log SHA256 `2206546d1046861559dcd86633f9d5ccb2384d681a5f2cac76272d9f1ae95f80`; five complete repaired files **109 PASS**, exit0/source_unchanged_during_run true, log SHA256 `1a894331f0445ad07bdaabec0231493d12a2987d208ffba1e9f74f4a675ec6ec`. Actual log bytes match those hashes. Overlapping counts are not added.

The test diff preserves041 history and appends042, expands the relevant suffix to27, adds the two expected tables and advances the future-version rejection to43. Other changes are necessary current-version expectations or new tests; no skipped/deleted/weakened safety assertions were found.

## Five-axis assessment and limits

The overall approach is appropriately bounded: two additive tables, finite metadata routing, original lifecycle reuse, no production eligibility/spend grant, explicit41 compatibility and version-aware strict039/042 schema checks. The three replaced provider-union guards preserve old branches and add only the exact new pair. INSERT-count-one and consent-before-claim guards, reciprocal failure/result exclusions and exact schema comparison improve safety. SQL values are parameterized; interpolated table names come from application-owned finite constants. No new endpoint, SDK, account or credential behavior is introduced. Repeated audit lookups are bounded by execution/database size and follow current repository patterns; no separate blocking performance issue was confirmed.

However, the two reproduced malformed-scalar acceptance paths prevent approval of this strict storage/restore slice. Parent was notified promptly; repairs belong to the original author. No moving repair is reviewed by this report.

Read AGENTS/collaboration/PRD/System Design/V1 Product Spec/reuse/task/migration proposal and author handoff. Used code-review-and-quality and security-and-hardening; graph-first discovery followed by current source/diff because the indexed root predates new042. Jev was not exposed, so the existing strong/default independent review continued. DIRECT reuse is standard-library SQLite/JSON/hash, existing immutable authority, claim/admission/usage and strict restore; no copied third-party code or dependency/license action.

Real BigModel transport/configuration/credential/account/price/quota/quality, actual cloud model use, whole-feature full regression, Root real GUI, formal Backup/Restore and main adoption remain outside this review. No model is qualified or user path declared usable here. **Do not integrate896a4834 until the findings have fixed-source regression and independent re-review.**

## 2026-10-27 fixed scalar repair delta review

Reviewed fixed author `2bf9cf21725494309d7d9222759dc835a4dc2996` against896a4834. Root placed that repair on the same review branch at `c069b677d6aa551dec16e3615451502ba82f0360`; source/test equality to2bf was verified. The original rejection and evidence above are retained.

**Verdict: REJECT2bf pending one remaining P2-01 claim boundary.** P2-02 and the original direct SQL/reader/reserved-claim/restore scalar cases are repaired, but the other existing claim API still accepts a malformed new consent.

### Confirmed repair coverage

- New042 authorization identity is explicitly NOT NULL and textual; input hash must be textual64-lowercase-hex. Both audit timestamps require the application's fixed27-character UTC/calendar roundtrip. Only the new provider gets raw-value validation; old providers retain their existing behavior.
- Independently replayed direct SQL NULL ID, BLOB ID, BLOB hash, zero authorization timestamp and overflow calendar cases: all rejected and each entire SQL dump remained unchanged.
- Independently corrupted NULL/BLOB IDs, BLOB hash and zero authorization time in isolated copies: authorization reader, **reserved** claim and strict database verifier all rejected; SQL remained unchanged after these refusals. The NULL copy necessarily has a weakened table and is additionally rejected by exact schema verification. BLOB/time copies preserve identical schema and trigger SQL, so semantic row validation is actually exercised.
- The complete Backup file exercises all five rehashed malformed-archive variants with unchanged live SQL/DATA, invalid failure UTC read refusal, legal microsecond/time progression and an actual2028 leap-day positive. The checksum test explicitly refuses the old unpublished042 checksum rather than silently rewriting it.
- All40 historical SQL files001–041 remain byte-identical. New042 SHA256 is `7bddf62ec3fa49a94657b930fd7315a2089642ab7a9b82f2cb76064e1c824d73`; changing an unreleased candidate's042 is not advertised as compatibility for prior experimental42 databases.

### Remaining P2-01 — direct NOT_CHECKED claim omits the new validator

Location: `state.py:10899`, `claim_distillation_execution`. The repair adds `_validate_zhipu_execution` before `claim_reserved_distillation_execution`, but not this sibling existing claim method.

Independent fixed-source reproduction in a fresh temporary repository:

1. Add the existing public source/video fixture and call `begin_distillation_execution` for the exact new pair, yielding a legitimate PENDING/NOT_CHECKED/count0 checkpoint.
2. Persist a valid new consent through `authorize_cloud_execution`.
3. On the isolated corruption copy, set only its `verified_input_hash` to `b"a"*64` using the same CHECK/immutability-bypass technique; restore every trigger and CHECK setting, asserting the complete sqlite_master SQL is identical. This is the same malformed-row threat model used by the accepted repair tests.
4. Call `claim_distillation_execution(**request, now=NOW)`.

Actual result: **return True, invocation_count1, budget_state DISPATCH_CLAIMED**. No provider/model was called. A subsequent validated read can reject the bad row, but the existing method has already crossed its durable permission-to-dispatch boundary. The reserved sibling correctly refuses this same damaged consent.

Minimal completion: apply the same new-provider raw authority validation to this direct claim boundary, or explicitly refuse the unsupported new-provider direct route. Preserve old-provider behavior. Add a NOT_CHECKED direct-claim counterexample proving count0/all rows unchanged, plus the relevant valid-path control. This is the remaining original scalar/claim finding, not a request for a new lifecycle or provider permission.

### Independent fixed-source verification

| Check | Result |
|---|---|
| Compile the three changed Python files before tests |3PASS |
| `pytest -p no:cacheprovider tests/unit/test_backup_restore.py tests/integration/test_state_store.py tests/integration/test_task022_personalized_distillation.py tests/unit/test_moonshot_distillation_adapter.py tests/unit/test_openai_distillation_adapter.py -q --tb=short` | **379PASS**,165.39s; one expected duplicate-ZIP fixture warning |
| Strict mypy all source |122files PASS |
| Ruff no-cache on the three changed Python files |PASS |
|40 historical SQL bytes and product/test equality to2bf |PASS |
| Independent raw-value and direct-claim probes |Original entry points refuse; remaining direct claim counterexample above succeeds |

Author's378PASS/1FAIL five-file run and later111PASS complete Backup rerun remain separate historical evidence; the precise exception-expectation repair adds a direct-SQL refusal/count0 assertion instead of weakening it. This independent379-pass run is on the final2bf source, not a relabeling of that earlier run.

One independent probe initially lacked its temporary fixture parent directory and stopped before creating a repository; it was corrected by creating that parent, without implementation changes. No additional toolchain/dependency or business change was made. Root was promptly informed of the remaining direct-claim result. Only this report is appended; the reviewer does not fix implementation, inspect a moving repair or touch Root GUI/owner/model/credential state. **Await a new fixed commit before final approval.**
