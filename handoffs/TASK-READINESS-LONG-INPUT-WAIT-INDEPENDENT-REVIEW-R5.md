# Independent incremental review R5 — verification facts, verdict pending

## Scope and status

**Final verdict: PENDING.** No unresolved product issue was found in this bounded delta review, and all independently selected checks below passed. Final APPROVE still requires the single fixed-source76-file backend result and root's new complete-stock native GUI acceptance. No ACCEPTED/DONE/main adoption is granted by this report.

- Reviewer: `/root/long_wait_independent_review`,2026-10-21.
- Fixed candidate: `29228606ea230d1d3ccbe5b1fd2ef1e3111b0da4`.
- Incremental base: `6e0f59e2f40fb62d371945cac0253346aa1616ce`; overall task base remains `4f7cc46ed1381782288a2f4915dce027b38c3b94`.
- Worktree/branch: `/Users/developer/Documents/yia-worktrees/readiness-long-input-wait-review-r5`, `codex/review-readiness-long-input-wait-r5`. Exact HEAD and clean state checked before work.
- Read current root assignment/task/plan, author's recovery handoff, and [R4 report with Restore P1 addendum](/Users/developer/Documents/yia-worktrees/readiness-long-input-wait-review-r4/handoffs/TASK-READINESS-LONG-INPUT-WAIT-INDEPENDENT-REVIEW-R4.md), latest report commit8f8fe01. Applied code-review-and-quality and new-worktree fast/persistence=false graph-first discovery.
- Reviewed only6e→292 plus necessary preserved contracts. Only this report is written; no business/test edits, dependency install, model/tokenizer/cloud/owner access, root QA-scene changes, broad test restart or main integration.

## Findings disposition

R4's HTTP lifecycle P1 is addressed in fixed source. The local `DrainingHTTPServer` has `daemon_threads=False`, leaving standard block_on_close joining enabled. The main serve loop's server_close now joins accepted request handlers before native shutdown, source-worker stop/join and cached-config reconstruction. The shutdown call remains on a separate timer thread, so it does not join its own handler or call shutdown from serve_forever's thread. Both persisted settings apply and confirmed Restore schedule shutdown before sending their ACK, preserving recovery after BrokenPipe.

Handler setup applies the existing120-second **socket idle** bound to incomplete request lines and short JSON uploads as well as existing streams. It does not reduce the existing native2GiB limit or create an overall transfer deadline. A progressing accepted transfer can intentionally keep drain waiting; an idle partial request cannot wait forever. The controlled normal-worker/cached-config HTTP tests hold actual old status verification under machine EX, demonstrate server_close has not returned before release, then rebuild via the actual factory and prove Restore APPLIED/full SQL-DATA equality. Both received and lost Restore ACK paths pass.

R4's malformed metadata P2 is addressed at all three ModelSettingsService discovery boundaries: tags/runtime_status, version/fixed identity and discovered_models now catch the specific standard HTTPException family in addition to the existing expected I/O/validation errors. IncompleteRead/BadStatusLine become unavailable; selected-runtime binding does not claim APPLIED or consume the settings journal. Programming errors are not broadly swallowed.

Native/background feedback and no-op regressions are repaired without weakening protection. A failed EX acquisition rechecks the original native-import counter so active local snapshots retain their specific reason. Background retained-subtitle settlement returns the established empty result when its protected window cannot be entered; complete proof checks/transaction rollback and no-data-change assertions remain. The exact three previous native/retained background failures pass.

The wrong-route guard now belongs to the ordinary Content POST, matching its status guidance and preserving409 MODEL_CONFIGURATION_REQUIRED with no task. Removing that new guard from the lower reservation service restores historical LOCAL short wait/budget/cancel/restore semantics; all six previous LOCAL failures pass. Generic long invocation prohibitions, profile qualification and transport claim boundaries remain unchanged.

Legacy CLI admission no longer constructs BackupRestoreService or LocalIntelligenceSettings and cannot recover/clear a pre-promotion journal or create Backup storage through resolved control symlinks. It holds only the shared machine SH gate across bootstrap/dispatch, uses the same bounded no-follow reader and versioned decoder, refuses any journal and keeps unknown bytes closed. DATA path resolution still matches the normal GUI identity. The extracted reader/decoder is unchanged in behavior, and targeted external symlink/journal integrity counters pass.

## Independent verification

Used `/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python` in the R5 review cwd, `PYTHONPATH=src:tests:.` for tests and `PYTHONPATH=src` for strict mypy. Import proof resolved R5's `src/youtube_intel/local_api.py`.

| Check | Actual result |
|---|---|
| compileall src/tests/scripts | PASS |
| Ruff src/tests/scripts | PASS |
| strict mypy src | PASS,119 source files |
| `git diff --check 6e0f59e...HEAD` | PASS |
| Final67 settings cases plus the exact previous9 failures |76PASS99.41s |
| Frontend delta against6e | Empty; R4's independent980PASS/38files/TS/build evidence remains applicable |
|495-file fixed-source manifest comparison |495 entries, zero mismatches |

Exact independent command:

```text
python -m pytest -q tests/integration/test_local_intelligence_settings.py tests/integration/test_local_intelligence_text.py::test_text_wait_cancel_restart_and_unknown_are_never_redispatched[model] tests/integration/test_local_intelligence_timed.py::test_local_wait_gates_restart_and_model_cancel[model] tests/integration/test_local_intelligence_timed.py::test_local_wait_gates_restart_and_model_cancel[budget] tests/integration/test_local_intelligence_timed.py::test_existing_video_receipt_leaves_local_waiting_without_runtime_request tests/integration/test_local_intelligence_timed.py::test_local_terminal_backup_restore_preserves_all_tables_and_data[True] tests/integration/test_local_text_input_proof.py::test_schema39_terminal_proof_backup_restore_and_restart_do_not_redispatch[cancelled] tests/integration/test_dogfood_day2_native_import.py::test_native_background_window_blocks_backup_and_restore_without_deleting_data tests/integration/test_retained_subtitle_derivations.py::test_archive_gate_respects_background_and_staged_restore_lock tests/integration/test_retained_subtitle_derivations.py::test_mixed_global_guards_and_transaction_failure_preserve_every_row[background]
```

Node IDs containing brackets were individually shell-quoted in the actual command. No failure was hidden, skipped or addressed by changing tests. The new counters additionally cover6 malformed-HTTP cases, pre-promotion journal preservation, two external symlink variants, true HTTP drain with normal/lost ACK and two incomplete idle request variants. Existing settings cases retain full machine CAS/admission/catalog, correct short/long WAIT0/cancellation, whole-table/DATA, bad configuration repair and cross-process isolation checks.

## Integrity and remaining gates

- Delta changes seven product files, one test file and the author handoff. No frontend, package, lockfile, migration, profile or qualification edits. No unrelated refactor or assertion weakening found.
- Independently compared all40SQL001–041 resources, both short/long execution profile modules, local_model_capacity, SourceAuthority and empty qualification resource against6e: all byte-identical. TimedTranscriptCueWrite AST remains identical. Installation0.40.6 remains configuration only; no inference profile/permit/capacity/qualification is added or renewed.
- Independent495-file manifest match uses author `settings-recovery-source-freeze.json`, SHA-256 `7fce1a55bd88be6e8bf3172df0ca6338dc76ee88e76005db6657c3172b3656bb`. No moving implementation was reviewed.
- Previous6e's unique76-file result remains2159PASS/9FAIL/1warning1656.10s and its genuine GUI Restore crash remains rejected historical evidence. The new sole76-file run (`settings-recovery-affected.log`) was still running without a final result at this report; the independent76 **cases** above are not that76 **files** gate. Do not label either earlier partial/interrupted run or combined fixed-source targeted results as a single full-suite pass.
- Root reported newv4 GUI actual settings apply preserved79SQL/19DATA, and short/long WAITs remained inv0/receipt0; root was still checking the other blocker and native Restore. These are progress facts, not completed GUI acceptance. No root QA service was started, stopped or changed by this Reviewer.

Final decision waits only on the required final fixed-source backend result and root native GUI evidence; no additional product fix or repeated independent test run is currently requested. Real model qualification, positive long generation/Save/Topic, whole-Goal regression and safe main adoption remain separate outstanding gates.
