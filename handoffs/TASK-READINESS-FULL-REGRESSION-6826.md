# TASK-READINESS-FULL-REGRESSION-6826 — Implementer

- Worktree `/Users/hua/Documents/yia-worktrees/readiness-regression-6826-fix`
- Branch `codex/readiness-regression-6826-fix`; base `ee66c8ce56298699b8467f6c376a54e1df77bec4`.
- Root is final reviewer/integrator and owns active real trials. This worker uses only owned temporary DB/data and no credentials, external requests/models/fees or live services.
- DIRECT current migration registry/checksums, authority reader/proof verifier, BackupRestore guard and stdlib resource lifetime. No schema/dependency/engine or alternate restore path.

## Evidence before safety-boundary edits

Root full frozen suite: 6815 PASS / 10 FAIL / 1 SKIP, 3213.38s. Nine failures stop on stale latest-schema43/tail assertions before intended domain/counter/rollback assertions. Actual schema44 has43 migrations (029 is absent). Plan: update only explicit latest version/name and append044 to exact28-tail ->29-tail, retain all old checksums/DDL and all domain/counter/rollback assertions.

LOCAL_TEXT positive Save→Topic→BackupRestore failure reproduced before edits with a diagnostic SQLite connection subclass/weak references and GC disabled only in temporary instrumentation. Raw RED `.var/regression-6826/local-text-red.log`: 1 FAIL, 7.37s. Exact unexpected files: `database/state.sqlite-wal` and `database/state.sqlite-shm`. Two still-open staging DB connections originate at `AuthoritativeIntelligenceReader._read_card` line244, called by `_validate_snapshot_authority` lines1459/1481. The outer backup validation connection is explicitly closed; read-side nested `with repository._connect()` only manages transactions and does NOT close SQLite. `_read_current` has the identical ownership mistake. Positive path invokes these readers; NO_NEW does not. This is a product connection-lifetime bug, not permission to ignore/remove WAL/SHM.

Precise minimal fix plan: replace those two reader-owned context managers by existing `contextlib.closing`, already imported and used by this reader. Preserve all verification calls, source/hash/proof/unknown gates, transactions and archive/stage-tree guard. Add focused actual-reader success/failure close assertions with strong references to the real connections (no reliance on GC), and run original positive/NO_NEW SaveTopic/all-table/DATA restore plus unknown-file rejection. No sidecar unlink, checkpoint deletion, migration or Backup guard edit.

Skip identified: `tests/unit/test_o200k_provisioning.py:134`, optional canonical o200k asset env `YOUTUBE_INTEL_O200K_TEST_ASSET` absent. Whole file without env: 7 PASS /1 SKIP 0.22s. Existing canonical asset located read-only at Root `.var/final-regression-assets/tokenizers/o200k_base.tiktoken`; will validate/copy to own temp resource and run original full file with explicit asset, without changing skip requirements.


## Applied minimal change / green evidence

- `intelligence_read.py`: precisely `_read_card` and `_read_current` wrap owned SQLite handles in the already imported `closing`; no validation removed/reordered, no BackupRestore modification, no WAL/shm removal/ignore, no schema or transaction-policy changes.
- New six cases in the existing LOCAL_TEXT integration file hold actual verifier connections strongly and assert immediate `ProgrammingError: closed` after current/card/recorded reads, both success and injected validation rejection. RED before fix:1 FAIL8.34s (`connection-close-red.log`); GREEN six + unchanged positive/NO_NEW SaveTopic/all-table/DATA restore:8 PASS28.94s (`local-text-green.log`).
- Repeating the original instrumented positive full restore AFTER the fix with GC disabled (diagnostic only):1 PASS10.76s (`local-text-stage-close-green.log`). All four stage checks contain only manifest-authorized DB/DATA/control files, no WAL/SHM and no open staging connections. Product does not depend on changing GC settings.
- Six stale-schema test files: only latest explicit43→44/name044 and append044 to exact28-tail→29-tail. Old migration names/checksums,37 rollback, source/run/domain assertions, every trigger/DDL check and forged-counter assertions retained. Counter1 remains honest positive control, counter0/2 reach the existing Content retry ownership/file closure rejection; all three passed in the complete affected run below.
- Complete `tests/unit/test_backup_restore.py tests/unit/test_synthesis_runtime.py tests/unit/test_system_synthesis_persistence.py`:182 PASS120.26s, one controlled duplicate-name UserWarning from the intentionally invalid duplicate-path ZIP. Includes original unknown-extra-file, corrupted-history, older-schema restore and synthesis positive Save/Topic/populated Restore guards. Log `.var/regression-6826/backup-synthesis-safety.log`.
- Original optional o200k whole file explicitly provisioned:8 PASS0.33s, no skip (`o200k.log`). Read-only original asset hash verified446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d, copied only to own ignored validation directory. No download/dependency/environment-requirement/skip modification. Root final full suite should explicitly set this same env to a verified owned canonical asset if all optional tests are required.
- Strict mypy on changed production reader:PASS; Ruff on all eight modified source/test files:PASS; compileall those files:PASS; diff whitespace:PASS.

## Scope / remaining work

Worker actual Native credential access/network/model calls/fees:0. No final candidate WT, fee-control, frozen r4 package, formal data/config, dependencies/migrations, main/push/deploy writes. Global53-minute suite not repeated; Root owns final rerun after exact delta integration. Complete seven affected integration files passed as recorded below. Suggested state IN_REVIEW; Root owns acceptance/integration and the final global rerun. Fixed commit SHA is reported in the implementer final message; this report is included in that commit.


## Final complete affected result / review

- `PYTHONPATH=src /Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python -m pytest -q tests/integration/test_local_intelligence_text.py tests/integration/test_provider_dispatch_crash_recovery.py tests/integration/test_retained_subtitle_derivations.py tests/integration/test_task018_domain_persistence.py tests/integration/test_task021_source_policy_filtering.py tests/integration/test_task023a_source_run_persistence.py tests/integration/test_tracked_content_retry.py`: **361 PASS678.75s**, no fail/skip/warning. Log `.var/regression-6826/affected-seven.log` in this worktree. All original nine latest-schema/tail failures now reach their unchanged domain/crash/rollback/DDL/counter assertions; the prior LOCAL_TEXT positive Restore failure and NO_NEW both pass. Six newly added connection-lifetime cases also pass.
- Full three-file Backup/synthesis safety group: **182 PASS120.26s**, controlled duplicate-path ZIP warning only. This includes the requested actual synthesis positive Save/Topic/populated Restore pathway on owned fake-wire fixtures (not real model qualification).
- Optional provisioned tokenizer whole-file group: **8 PASS0.33s** after explicit canonical asset provisioning; original env-absent behavior remains7 PASS/1 SKIP as designed. No skip removed, no test/assertion deleted or weakened.
- Final code scope: two ownership fixes in one production reader; latest-version/name/tail-only edits in six integration files; six new immediate-close cases in seventh integration file; own handoff. Every migration/lock/config/dependency/Backup source file unchanged. Reuse DIRECT Python sqlite3/contextlib and project existing verifiers/reader/Backup/domain APIs; project NOTICE/LICENSE unchanged, no copied third-party source.
- Final diff review found no unrelated refactor/formatting, temporary diagnostic instrumentation or canonical resource committed. All RED/GREEN logs and diagnostic probe remain only in ignored own `.var/regression-6826`.
- Global full6826 suite, frontend/TS/build and GUI were not repeated by this worker: this delta has no frontend/UI change and Root owns global acceptance. No claim that isolated unit/integration proofs establish real model quality or product adoption.
