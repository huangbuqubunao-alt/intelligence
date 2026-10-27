# TASK-READINESS-BIGMODEL-READ-SNAPSHOT

Implementer `/root/cloud_preview_writer`; new worktree `/Users/hua/Documents/yia-worktrees/readiness-bigmodel-read-snapshot`, branch `codex/task-readiness-bigmodel-read-snapshot`, base `17168de63afce55fde5d660a8f02e68e4463dcb8`. No unaccepted transport source or fixture is copied.

## Pre-edit graph/current-AST inventory

Graph lookup found four existing public getters; current AST (graph predates042) found all ten direct callers of `_validate_zhipu_execution`:

| Caller | Existing boundary / required action |
|---|---|
| get_distillation_execution | Own connection, multiple autocommit SELECTs; require one read snapshot |
| get_cloud_execution_authorization | Own connection, checkpoint then consent/accounting SELECTs; require snapshot |
| get_distillation_resource_usage | Own connection, receipt/checkpoint/authority SELECTs; require snapshot |
| list_distillation_resource_usage | Own connection, separate receipt unions and validations; require snapshot; existing calls to public usage getter open another connection, so reuse a private same-connection projection |
| verify_cloud_audit_database | Caller-owned connection; multiple schema/forward/reverse reads; require snapshot only when caller has no transaction, preserving caller transaction ownership |
| claim_reserved_distillation_execution | Already BEGIN IMMEDIATE; preserve byte-for-byte |
| claim_distillation_execution | Already BEGIN IMMEDIATE; preserve byte-for-byte |
| finish_distillation_without_admission | Already BEGIN IMMEDIATE; preserve byte-for-byte |
| record_distillation_no_new_intelligence | Already BEGIN IMMEDIATE; preserve byte-for-byte |
| admit_distillation | Already BEGIN IMMEDIATE; preserve byte-for-byte |

Caller inspection: initialize invokes whole-audit verification after committed migrations. Backup core verification passes its existing connection (sometimes already in a protecting transaction); nested audit verification must neither commit nor roll back caller work. Four public getters own/close their own connections. Reuse DIRECT Python SQLite deferred read transactions and existing validators, no retries/exception swallowing/new dependencies/schema/default connection changes. COLLABORATION/PRD/SYSTEM_DESIGN/REUSE_REGISTER bytes match the previously read523b baseline; new task, current status and independent R2 report reread.

This inventory was written before product edits. Fixed commit is reported in the final chat; completed implementation/checks follow below. Root alone accepts/integrates; no model qualification or whole-Goal completion claim.

## Implementation and deterministic evidence

`_read_snapshot` issues deferred BEGIN only when no caller transaction exists, pins the database view at its first read, and rolls back only its own read scope on every exit. Existing caller transactions are reused without commit/rollback. Four getters close their owned connection after leaving the snapshot, including errors; whole-audit verification keeps the caller connection usable. No IMMEDIATE lock is added to reads, so the controlled second WAL repository can commit while a reader retains its old coherent view.

All five public boundaries use this scope. Resource projection is extracted into a private same-connection method so the activity list does not reopen a later connection for its response union. The original usage projection body and original audit verifier body are AST-identical after extraction. All286 other repository methods, including _connect and every write/claim/finish/cancel method, are byte-identical to the accepted base. Validators are unchanged. No changed SQL resource, dependency, configuration, credential, model/profile/qualification, API/DTO/UI, owner data, Root service or main.

Initial baseline command (with the explicit task Python environment below): `-m pytest -p no:cacheprovider tests/unit/test_bigmodel_read_snapshot.py -q --tb=short`: **5FAIL2.61s**. Four exact deterministic checkpoint→normal finish interleavings raised `StateStoreError: BigModel execution usage differs` (usage getter should instead observe ordinary old-moment absent usage). The list recorded `in_transaction=False` at its union boundary. No sleeps, source corruption, trigger changes, transport or model calls were used for these legitimate race fixtures. Fixtures reuse accepted repository reserve→OWNER_QUALIFICATION consent→claim and real isolated SQLite/WAL+physical DATA; no unaccepted transport implementation or production permission is imported.

After repair the original5 passed2.65s; expanded19 focused tests passed7.36s. Coverage: normal claim and ambiguous completion between captured checkpoint and audit; list old normal+failure receipts versus new usage/failure commits, all on one reader connection; active caller IMMEDIATE success/error ownership; owned read cleanup success/error; all five readers still reject a genuinely corrupted BLOB consent hash without row/file changes and close owned connections; local WAIT cancellation returns its old snapshot while fresh read is CANCELLED0. Fresh BigModel terminal stays AMBIGUOUS1, another claim is refused, and repeated reads leave the entire SQL dump and physical DATA unchanged. Scalar-corruption fixtures restore the original schema and use the accepted corruption helper solely for rejection controls, never for the legitimate race.

Runtime for all checks: `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`, explicit `PYTHONDONTWRITEBYTECODE=1` and `PYTHONPATH=/Users/hua/Documents/yia-worktrees/readiness-bigmodel-read-snapshot/src`. Strict mypy122 source files PASS; in-memory compile122 source plus new test PASS; Ruff no-cache changed source/test PASS; whitespace diff PASS. Complete fixed-source affected regression is recorded below. Prior R2 reviewer268PASS1FAIL and one isolated follow-up PASS remain independent historical evidence and were not relabelled or rerun as a transport pass here.


## Final fixed-source checks and limits

| Check | Result |
|---|---|
| Complete12-file affected group |**612PASS**,578.40s; expected duplicate-path ZIP fixture warning only |
| Final process/source evidence |Exit0; all 164 source/SQL/new-test hashes unchanged before/after and rechecked against current files |
| Strict mypy all source |122 files PASS |
| In-memory compile source plus new regression |123 files PASS |
| Ruff no-cache changed source/new tests |PASS |
| Scope/whitespace review |PASS; only state.py, new unit regression, own handoff |
| Existing mutation/validator preservation |286 other repository methods plus IMMEDIATE helper byte-identical; extracted usage/audit bodies AST-identical |
| Migration resources |All41 packaged SQL files byte-identical to accepted17168 base |

The exact command/environment and source hashes are preserved in ignored `.var/bigmodel-read-snapshot/final-affected.json`, output in `final-affected.log` (SHA256 `b525d6aab3caaf83b81796020071fde56bca7ba4e7012b656059c74a32cc1edc`). The12 complete files are new snapshot regression, BigModel claims, Backup/Restore, state store, task022 personalized distillation, task023b reservation, source context, local timed/text Intelligence, long completion storage/lifecycle and local wire branches. Thus the group retains genuine scalar/link/schema/accounting corruption, old provider, local cancel/NO_NEW/long/text and backup controls. All existing assertions/tests remain unchanged; no retries, swallowed StateStoreError, schema/header weakening, or automatic execution was added. Counts overlap the19 focused cases and are not additive. No remaining test failure or skipped required check in this bounded slice.

Actual cloud transport/service-concurrency composition is deliberately not tested here: accepted base17168 contains only acceptedState42 and task/docs, not unaccepted a7/007. Root must compose the independently accepted state change with that separate adapter chain and recheck its service race before accepting transport. No real network, credential, model, account entitlement, semantic quality, fee, whole-feature completion or main adoption is claimed. Suggested task state IN_REVIEW; author clean STOP after scoped commit, Root alone accepts/integrates. DIRECT SQLite/contextlib and repository authority reused; no external code copied or new dependency/license obligation.
