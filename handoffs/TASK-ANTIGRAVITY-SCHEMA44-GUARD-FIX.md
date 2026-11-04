# TASK-ANTIGRAVITY-SCHEMA44-GUARD-FIX implementation handoff

## Metadata and scope

- Role: Implementer, `schema44_guard_resume`; reported 2026-11-04 Asia/Shanghai.
- Base: `f0e330129ad9243423a0c03feb598992e94517b1` (Antigravity candidate, not accepted main).
- Worktree: `/Users/hua/Documents/yia-worktrees/antigravity-validation-fix`.
- Branch: `codex/antigravity-validation-fix`.
- Root task: `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/tasks/TASK-ANTIGRAVITY-SCHEMA44-GUARD-FIX.md` and Root's bounded resume messages.
- Goal: reject semantic changes to quoted authorization predicates at startup, backup readiness and restore, including empty synthesis sidecars.
- Reuse: DIRECT existing SQLite `sqlite_master`, existing migration-derived `verify_schema`, standard-library SQLite/ZIP/hash test helpers. No dependency, migration SQL, state policy, model, credential or network changes.

## Implementation

1. Preserve the prior one-line repair: `_schema` strips only surrounding whitespace instead of removing whitespace inside SQL literals/comments/token boundaries.
2. Add the existing synthesis schema verifier to `BackupRestoreService._verify_core_database`, reached by readiness and staged restore irrespective of sidecar row count. Legacy schema34–43 use the verifier's existing legacy behavior; full result/row validation remains in place.
3. Retain 11 focused cases: space/tab/newline predicate changes rejected by direct schema validation, startup and empty-sidecar readiness; re-signed altered ZIP rejected before activation; normal legacy reserved claim still denied without consent.
4. Strengthen the ZIP test construction: checkpoint and close the mutated WAL database; inspect the actual repacked database's trigger and verify its ZIP CRC, manifest size and SHA before asserting rejection. The original live schema remains valid after rejection.
5. Separate test-only correction authorized by Root: latest migration test now checks actual044 filename/checksum, exact table set including four synthesis tables, and exact **43** migration history rows. Schema version44 is not migration-count44; the packaged migration list itself has43 entries. No old-version assertions were weakened.

## Verification

Commands use the existing interpreter `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`; `PYTHONPATH=src` binds imports to this worktree.

| Check | Actual result |
|---|---|
| `env PYTHONPATH=src <python> -m pytest tests/unit/test_system_synthesis_persistence.py tests/unit/test_schema44_guard_literal_integrity.py -q` | **51 PASS, 41.03s**, final log `.var/schema44-guard-fix/51-cases-final.log` |
| `env PYTHONPATH=src <python> -m pytest tests/unit/test_backup_restore.py tests/integration/test_state_store.py tests/integration/test_v1x_phase1b_backup_restore.py tests/integration/test_research_backup_restore.py -q` before latest-test correction | **187 PASS / 1 FAIL, 95.89s**, one existing duplicate-ZIP warning. Sole failure was stale latest-migration filename in state-store test. Includes schema34–43 backup round trips. |
| `env PYTHONPATH=src <python> -m pytest tests/integration/test_state_store.py -q` after precise latest-test correction | **48 PASS, 15.05s**. This is the complete affected file, not a repeated full188-case run. |
| Re-signed ZIP rejection test, final construction, focused invocation | **1 PASS, 1.48s**; subsequently included in51 PASS |
| `env PYTHONPATH=src MYPYPATH=src:tests <python> -m mypy --strict src/youtube_intel/system_synthesis_persistence.py src/youtube_intel/backup_restore.py tests/unit/test_schema44_guard_literal_integrity.py` | **PASS**, 3 source files |
| `<python> -m ruff check` on both product files, new test and state-store test | **PASS** |
| `<python> -m compileall -q` on same four files | **PASS** |
| `git diff --check` | **PASS** |

## Preserved failures and corrections

- Prior worker's recorded47 PASS /4 FAIL exposed the empty-sidecar verification omission; no original assertion removed.
- Initial resumed pytest collection without `PYTHONPATH=src` imported the unrelated existing editable package at `/Users/hua/youtube-intel`; two ImportErrors. Corrected the invocation, without editing environment files or installations.
- First strict-test invocations could not resolve `conftest`; `MYPYPATH=src:tests` supplies its actual location. No missing-import suppression used.
- After core wiring, first51 run was50 PASS /1 FAIL,41.55s: ZIP test said `DID NOT RAISE BackupRestoreError`. Focused rerun reproduced1 FAIL,2.48s; stopped repeating and inspected actual archive. The live mutation was in WAL, while staged archive's SQL still said `'moonshot'`. Corrected checkpoint/close and added archive-internal assertions.
- The next construction attempted in-memory `deserialize` on a WAL-header database and failed `sqlite3.OperationalError: unable to open database file` (50 PASS /1 FAIL,40.09s). Replaced only that inspection with an independent temporary file holding actual ZIP bytes, preserving all rejection assertions.
- Original compatibility run's `test_initialize_is_repeatable_and_records_packaged_checksum` failed at `first.name`:044 actual versus043 expected. Root authorized exact filename/checksum/table/count maintenance. An intermediate run incorrectly assumed count44; actual packaged list and database prove43, so that run was stopped (29 PASS /1 FAIL,8.13s), corrected and complete48-case file passed.
- No failure is counted as green or hidden by deletion/skip/coverage changes.

## Diff review and limits

- Product delta: 1 changed comparison line and8 added verifier-wiring lines. New focused regression file and this handoff accompany the security commit. Latest migration test maintenance is a separate test-only commit.
- No SQL migration, dependencies, lockfiles, toolchain, credentials, production configuration, UI or model qualification changes. Original Antigravity and formal worktrees were not edited. No actual model calls or paid actions.
- No full backend/frontend/build/GUI or candidate delivery claim: these two bounded repairs do not resolve the separate candidate credential-isolation and runtime-integration findings. No main merge/push/deployment.
- Suggested status: **IN_REVIEW**, clean STOP after reporting commit SHAs. Root must independently review the repair delta.

## Reviewer / integration

Pending Root. No acceptance or main adoption is asserted by this implementation handoff.
