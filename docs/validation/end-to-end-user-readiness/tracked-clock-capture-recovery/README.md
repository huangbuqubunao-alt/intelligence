# Clock/capture recovery evidence

These are isolated offline tests and read-only diagnostic receipts. They do not assert a genuine GUI/network success, model qualification, or overall readiness. Original frozen failure and old stopped166 worktree remain intact. Full backend and real GUI acceptance are assigned to root after the fixed candidate is handed off.

## Causal diagnosis

Original real claim time was `2026-10-19T07:21:21.924732Z`; provider reservation wrote started_at `.929415Z`, then the same transaction assigned the earlier claim time to updated_at. The strict register guard correctly rejected this ordering. Failure settlement subsequently replaces updated_at with the terminal time, so the final failed ledger alone does not expose the earlier inversion.

The initial direct-register reconstruction set updated_at=started_at and passed. It establishes a structural boundary only. A full worker replay on a separate complete77-table/19-DATA copy, using the original3975B response through an explicitly offline adapter and actual progressing UTC, reproduced FAILED/local0/ADMITTED,CLAIMED,DISPATCH_INTENT,FAILED. The diagnostic trace captured `state.py:5028 LeaseConflict: subtitle capture lacks the exact owned live job/provider reservation`, propagated through transcripts.py2142/3052 and worker498. That trace was observed in tool output; no original raw traceback log was saved. The receipt here is an explicitly retrospective read-only snapshot, not a fabricated historical log.

A separate counterfactual copy replaced only the provider ownership UPDATE argument `at` with `self.timestamp()` in an in-memory compiled function, restoring the class afterward. It succeeded with canonical/timed/Summary/Evidence. This established causality; the final product instead uses one honest datetime snapshot for the atomic claim/reservation. The direct reconstruction has a nonempty WAL; its main-file hash is not claimed to describe its complete logical state. `diagnostic-snapshots.json` records all four locations and their actual selected rows plus main-file hashes/WAL sizes. No transcript content or DB is committed.

## Failure chain and fixed controls

Every log is preserved independently; counts from different runs are never added into a claimed single green run. Compressed logs are exact original bytes with deterministic gzip and raw/compressed hashes in `artifact-manifest.json`.

| Run | Actual result | Interpretation |
|---|---|---|
| advancing-clock-red | 3 FAIL /2.79s | Original source fails microsecond, millisecond and actual UTC clock controls. |
| advancing-clock-green | 3 PASS /4.09s | Atomic claim timestamp fixes those original controls. |
| known-capture-first | 7 PASS,4 FAIL /9.54s | New helper required dispatch.updated_at but the query selected only status; product query corrected. |
| known-capture-second | 11 PASS /13.12s | Original clock controls plus1/2 captures, absent/present non-authority capture artifacts. |
| capture-negative-first | 22 PASS,22 FAIL /40.95s | One real category-fallback defect: provider error corruption could fall back to generic retry admission. Other failures were fixture CHECK mismatches or status correctly raising integrity instead of returning a false flag. |
| capture-negative-second | 43 PASS,1 FAIL /41.13s | Remaining bad fixture set ACQUIRING with terminal error_code; corrected coherent corrupt fixture, retained CHECK. |
| capture-negative-third | 47 PASS /42.01s | Corrected strict negatives, no assertions or product CHECK removed. |
| capture-recovery-full-first | 52 PASS /52.78s | Includes restart/exact full restore, parent lock, reader/Backup semantic corruption. |
| capture-final-focused | 60 PASS /59.42s | Final fixed product/tests: backward-after-claim,39 condition corruptions,4 native-pair/cap2 controls and all previous controls. |
| schema40-affected | 562 PASS,4 FAIL /295.23s | Appended040 migration history still had four old suffix slices[-24:]; actual015..040 contains25 migrations because029 is absent. |
| schema40-suffix-final | 4 PASS /1.69s | Only those four suffix assertions corrected to25, complete history preserved. |
| schema40-final-full | 566 PASS /305.01s | Final complete24-file single invocation on the fixed source/tests; not the sum of previous runs. |
| existing-affected-final | 478 PASS /420.52s | Final original11-file group,1 existing duplicate-path ZIP negative UserWarning, not suppressed. |

The original final-repair ZIP falsegreen/WAL chain is retained in its existing166 evidence; it is not counted as this task's new cases. This task's added semantic ZIP control preserves ZipInfo, stages/cancels a positive archive, closes the mutated DB and verifies the actual immutable main bytes before asserting the exact retry-closure rejection.

## Schema40 expectation audit

`schema40-reviewed-edits.json` records each current-initialize expectation and reason. `schema40-ast-audit.json` records84 reviewed AST changes across24 files; `audit_schema_ast.py` is the actual audit script used against basebc306d1 (expects the companion inputs under the task's ignored `.var/tracked-clock-capture-recovery`). It permits current latest40/version/name, actual040 history append, future41 rejection/reset40, explicit historical039 failure selection and the four exact24→25 suffix corrections. It does not permit unrelated changes.

In particular: `test_tracked_content_retry.py:221/234` remains frozen39; migration33 and38 rollback assertions remain unchanged; migration39 failure test explicitly selects039 instead of now-last040 and still proves38 rollback; `test_state_store` migration_count39 and history tuple39 remain because029 is absent, with separate terminal tuple40. Full migration recovery/checksum/row/DATA assertions are retained. No migration/schema file is changed.

## Reproduction

Use the existing root venv, `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:.` and working directory at this worktree. `schema40-command.json` preserves the exact24-file command. Focused command is `python -m pytest -q tests/integration/test_tracked_clock_capture_recovery.py`; prior11-file command and all final results/source hashes are in `checks.json`.

No HTTP, tokenizer, model, ASR, Cloud, official runtime write, owner/main change, dependency, Schema, credential, frontend or qualification change was performed. Original2 unindexed DATA belong to MIXED and still independently block that real runtime's Backup.
