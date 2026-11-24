# Independent review R3: complete-source wait and usage closure

## Fixed review scope

- Role: independent Reviewer `/root/long_wait_independent_review`; reported 2026-10-21 Asia/Shanghai.
- Overall base: `4f7cc46ed1381782288a2f4915dce027b38c3b94`.
- Reviewed candidate: `b3546ff14627be51c27ce799e4de800ec1e9336d`.
- Worktree/branch: `/Users/developer/Documents/yia-worktrees/readiness-long-input-wait-review-r3`, `codex/review-readiness-long-input-wait-r3`; exact HEAD and clean state checked before work.
- Compared a2861e3→d7849b3 doctor/fixture repair and d7849b3→b3546ff family-closure repair, against the original full vertical already reviewed in R1/R2.
- Prior reports are preserved unchanged: [R1 REJECT, f9db3e4](/Users/developer/Documents/yia-worktrees/readiness-long-input-wait-review/handoffs/TASK-READINESS-LONG-INPUT-WAIT-INDEPENDENT-REVIEW.md), [R2 REJECT, c9e3ee2](/Users/developer/Documents/yia-worktrees/readiness-long-input-wait-review-r2/handoffs/TASK-READINESS-LONG-INPUT-WAIT-INDEPENDENT-REVIEW-R2.md).
- Applied code-review-and-quality, current root task/assignment and graph-first discovery after new-worktree fast/persistence=false indexing. Only this report is written. No business/test edits, real model/tokenizer/HTTP/cloud/owner access, integration or task-state changes.

## Verdict: APPROVE — engineering scope only

No unresolved P0/P1 found in this fixed candidate. Both independently reported authority gaps are closed:

- `state.py:11484` validates reserved-family resource reads with the shared `verify_execution` and cancellation validator on the existing connection before physical usage or NO_NEW projection. List now enumerates all retained checkpoint IDs (`state.py:11708`) and applies that same predicate/validator before returning its bounded ledger projection. Missing ledger and case-variant family work cannot disappear from the list.
- `long_distillation_persistence.py:1060` and `:1065` enumerate checkpoint/revision IDs and apply Python `is_long`/`is_long_revision` directly, including Unicode casefold. The Intelligence reader's associated-checkpoint test (`intelligence_read.py:172`) uses the same predicate, so a generic revision name cannot conceal a casefold long checkpoint. No Python long-family LIKE/GLOB approximation remains.
- Valid WAIT0 and logical cancellation retain the truthful raw WAITING_MODEL zero-invocation usage. Unimplemented claimed/result branches remain refused by direct/list/API and authoritative result readers. The public resource endpoint maps validation failure to409 RESOURCE_USAGE_UNAVAILABLE.
- The helper does not call a public usage getter; the call chain terminates in transaction/source validators, without recursive getter cycles. Existing getter `finally` blocks close connections on success/failure, and the Intelligence auxiliary connection is explicitly closed. Nonlong accounting retains the old path.

Doctor now accepts exactly schema41. Its regression explicitly refuses40/42. The migration-tail fixture now includes041; historical migration40 success remains pinned through40; reconstructed tracked-counter archives preserve their actual41 user_version. The positive counter1 and exact ownership/file-closure rejection assertions for0/2 are unchanged and now reach the intended validator. These are precise compatibility/fixture repairs, not relaxed validation.

## Independent checks

Interpreter: `/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`, R3 review cwd. Tests used `PYTHONPATH=src:tests:.`, mypy used `PYTHONPATH=src`. Import proof resolved R3's `src/youtube_intel/state.py`.

| Check | Actual result |
|---|---|
| `python -m compileall -q src tests scripts` | PASS |
| `python -m ruff check src tests scripts` | PASS |
| `python -m mypy --strict src` | PASS,117 source files |
| `git diff --check 4f7cc46...HEAD` | PASS |
| All114 long cases plus the exact six prior doctor/fixture failures | 120PASS,133.70s |
| Legacy/R14 resource/accounting/budget/Cloud/NO_NEW/API/Backup risk selection | 53PASS,283 deselected,31.16s |
| Independent genuine-v6 historical proof/database validation using R3 code and SQLite mode=ro/query_only | PASS,1 proof; frozen code hash differs from current code; main database bytes unchanged |

The114+6 command: `python -m pytest -q tests/integration/test_long_input_wait_lifecycle.py tests/integration/test_long_completion_storage_contract.py tests/integration/test_long_source_boundary_counters.py tests/integration/test_long_resource_usage_closure.py tests/integration/test_task016c_phase_h2c_lineage_schema.py::test_doctor_database_check_accepts_exactly_version_41 tests/integration/test_task025a_saved_intelligence.py::test_fresh_m014_creates_empty_saved_state tests/integration/test_tracked_content_retry.py::test_migration40_failure_rolls_back_and_success_preserves39_domain_rows tests/integration/test_tracked_content_retry.py::test_rehashed_restore_must_reject_counter_not_bound_to_real_events`.

The53-case selection: `python -m pytest -q tests/unit/test_local_fixed_runtime_profile.py tests/unit/test_local_model_capacity.py tests/unit/test_local_api.py tests/unit/test_backup_restore.py tests/integration/test_task022_personalized_distillation.py -k 'resource or usage or budget or no_new or known_response or consent or accounting or fixed_variant or v1_projection'`. Deselection is this independent delta-review's bounded risk selection, not a claim of rerunning the full suite.

The new18 cases cover uppercase, mixed ASCII case and Unicode long-s `ſ`: direct/list/API/database refusal with missing ledger, proof deletion isolating the database reverse scan, orphan reserved revisions and generic revisions associated with casefold long checkpoints. The old resource cases cover all three final SQL branches through all three public readers, valid WAIT/cancel, missing proof/ledger, corrupt source and unknown/malformed identity. Old70 cases still exercise full original source, rollback, historical Summary/policy refresh, source ambiguity, cancellation/restart, legacy34–40 restore, all-table/DATA equality and rehashed ZIP counterexamples.

## Integrity, scope and evidence review

- d784→b354 modifies only three product files (`state.py`, `long_distillation_persistence.py`, `intelligence_read.py`) and the casefold test extension, plus handoff/evidence metadata. a286→d784 changes one doctor version comparison and three necessary legacy fixtures. No unrelated rewrite, assertion removal/skip, generic error-regex widening, dependency/lockfile/config/credential change identified.
- All40 migration resources in001–041 are byte-identical to d784. The39 old resources in001–040 remain immutable from the overall base. SQL final branches, old cancellation trigger and conditional physical-usage versus035-sidecar contract are unchanged.
- All11 product source hashes match the frozen candidate evidence. SourceAuthority is byte-identical to base, and TimedTranscriptCueWrite AST is identical; no ASR authority-tuple change was introduced here. Qualification resource remains unchanged `records=[]`, SHA-256 `0bf8f9526727d0c6f3c217ab3caf5630dc23cd97b6d1bcee525512a043d20347`.
- Read task-owned genuine-v7 receipt metadata only: SHA-256 `f91cfc0e7ad26de65a086b72d27485d656dc1555cc3d3f5ea697efec040e00ad`, actual video0eMzc-WnBfQ114 Evidence/2406 cues;79 SQL tables/19 DATA files equal after restore, source stock/old rows unchanged, m0371→2 solely new long cancellation, zero model/HTTP calls. These equalities are author backend evidence, not an independently repeated root GUI or model qualification.
- Independently opened only the specified isolated genuine-v6 database with `mode=ro`/query_only and bound its task DATA directory. R3 `verify_execution`, full `verify_database` and `read_cancellation` pass despite stored long-persistence code hash differing from current source; database main bytes unchanged. This directly confirms historical authority does not require current-code-SHA equality. No source body/private semantic content was printed.

## Verification history and remaining gates

Author logs were inspected separately: original60-file fixed run **1794PASS/6FAIL1401.93s**; exact six repairs **6PASS7.50s**; doctor-affected four files **104PASS75.48s**; final16-file group **561PASS381.82s**, one expected duplicate-ZIP-member warning. Its result JSON has pytest_exit0 and all11_product_hashes_unchanged=true (SHA-256 `6c30b5252a9b777d6827d9b23a3cf1fafbcc1812bc1d4c98d609628d7897022f`). This is evidence across fixed runs and verified deltas; it is **not** one1800-case passing run. Interrupted/mixed-source runs and the original failures remain historical evidence and are not counted as final passes.

APPROVE applies to this ordinary complete-source durable WAIT0/cancel/restart/BackupRestore engineering slice and its safety boundaries. Root alone decides acceptance/integration after its native GUI and remaining task gates. This is not DONE, main adoption, long model generation, qualification, paid-cloud authorization, positive long Save/Topic validation or completion of the whole ordinary-user-readiness Goal. No current or historical failed model evidence is promoted to qualification.
