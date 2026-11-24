# TASK-READINESS-BIGMODEL-TRANSPORT-REVIEW-R2

## Fixed scope and verdict

- Reviewer `/root/bigmodel_audit_review`; no subagents; date2026-10-27.
- Original author `a7a9d710816c316e5719f9fcf5ed8da0b9b80e57`, prior independent REJECT report `a4f9d405a813f748e4eeba8205dafedb5d3b67d1` preserved.
- Fixed repair `00789303e02292450b23461927332ac7c96790dd`.
- Review baseline `176afbabf67dabf680f2b4adeab6bb79d947a790`, only Root review task/prompt added to fixed source.
- Worktree `/Users/developer/Documents/yia-worktrees/readiness-bigmodel-transport-review-r2`, branch `codex/task-readiness-bigmodel-transport-review-r2`.
- **Cumulative verdict: REJECT a7+007 pending one newly confirmed P2 audit-read snapshot race.** Original input-projection P2 is correctly fixed by007; that specific correction passes independent reproduction and actual isolated Backup/Restore. No confirmed new P0/P1, no observed duplicate model dispatch or data corruption.

Only this report was written. No product/test repairs, SQL/schema/dependency/settings/configuration/credentials/native Keychain/owner/Root QA/main changes or actual HTTP/model calls. All fixtures are synthetic and isolated. Review does not grant qualification, budget or fees.

## Original P2 closure on007

The complete repair delta is eight production lines,88 new test lines and12 handoff lines. It calls the existing pure `_cloud_request_preview` only for the new pair after exact permit/consent validation and before credential readiness/claim. It catches only the finite `CloudPreviewRejected`, preserving unrelated storage/programmer failures. Unsupported input now records `REJECTED_EVIDENCE`, count0, `CLOUD_INPUT_NOT_SUPPORTED_BEFORE_TRANSPORT` through the existing finish transaction, with no new lifecycle/schema or budget authority. Valid bounded requests continue through the existing once-only path. No original assertion was removed or weakened.

Independently reconstructed165000B public caption through actual TimedTranscriptCueWrite/EvidenceTextBindingWrite, normal reservation, sealed hash, exact owner permit and immutable OWNER_QUALIFICATION consent. All physical DATA in this probe was registered and its real SHA metadata was prepared before reservation; no fake Backup hash or quiescence bypass was used. Actual results:

```text
before refusal readiness: ready=False, reasons=['DISTILLATION_ACTIVE']
refusal: REJECTED_EVIDENCE 0 CLOUD_INPUT_NOT_SUPPORTED_BEFORE_TRANSPORT key/wire: 0 0
after refusal readiness: ready=True, reasons=[]
Backup/Restore: 80 non-internal tables; entire SQL dump identical;
1 registered DATA file identical; restart no replay; ready=True
```

The probe used the real BackupRestoreService create→download→stage→confirm→recover-and-apply flow, then normal repository initialize and continuation. Strict new audit verification passed before and after restore. The entire dump, including internal schema rows, was compared;80 is the explicitly counted non-`sqlite_%` table count, not a claim that a missing table was ignored. Consent, checkpoint, usage and Evidence/history survive. Actual identity/tokens/cost/HTTP remain unknown/NULL; no orphan PENDING or response failure is invented. The new full integration file also checks these original boundary requirements and no replay on restart.

## New P2-02 — coherent completion can look corrupt across unsnapshotted reads

Location `src/youtube_intel/state.py:10260` (`get_distillation_execution`) and4661 (`_validate_zhipu_execution`). The getter selects a checkpoint then separately reads consent/failure/usage/NO_NEW without a single read transaction. A concurrent valid completion can commit between those SELECTs. The validator then compares a stale PENDING checkpoint to the newly committed terminal usage, raises `StateStoreError: BigModel execution usage differs`, and turns a legitimate competing continuation into an error. SQLite state is coherent; the reader combined two points in time.

This was first observed in the unchanged concurrency test during the complete independent group:

```text
test_concurrent_owner_continuations_and_claimed_restart_make_one_post
_continue_reserved_distillation_impl -> _recover_reserved_execution
-> get_distillation_execution -> _validate_zhipu_execution
StateStoreError: BigModel execution usage differs
1 failed,268 passed,1 expected duplicate-ZIP warning in89.98s
```

One subsequent run of only that test passed (1PASS2.03s); that timing-dependent pass does not invalidate the failure. No assertions were changed and no further blind retries were run.

### Deterministic interleaving proof

Using `PYTHONDONTWRITEBYTECODE=1`, explicit review src+tests/integration PYTHONPATH and Root's existing Python, the following probe performs only legitimate repository writes. The instance hook schedules another repository's normal finish exactly after the reader captures its checkpoint, reproducing a normal competing completion without corrupting SQL or disabling any guard:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from test_bigmodel_distillation_transport import _setup, _permit
from test_task022_personalized_distillation import NOW
from youtube_intel.state import SQLiteStateRepository, StateStoreError

with TemporaryDirectory(prefix='bigmodel-r2-reader-race-') as td:
    repo, source, video, evidence, service = _setup(Path(td))
    r = service.reserve_distillation_execution(source_id=source, video_id=video, evidence_ids=(evidence,))
    record = repo.get_distillation_execution(r.execution_id)
    _, verified = service._reserved_command_from_record(record)
    _permit(service, verified)
    service.authorize_reserved_cloud_execution(record.execution_id, consent_kind='OWNER_QUALIFICATION')
    repo.claim_reserved_distillation_execution(**{k: getattr(record, k) for k in ('execution_id','source_id','video_id','reason','use_case','selected_provider','selected_model','output_language')}, now=NOW)
    reader = SQLiteStateRepository(Path(td) / 'state.sqlite3')
    validate = reader._validate_zhipu_execution
    def interleave(connection, checkpoint):
        print('reader captured:', checkpoint['status'], checkpoint['invocation_count'], 'transaction:', connection.in_transaction)
        repo.finish_distillation_without_admission(execution_id=record.execution_id, status='AMBIGUOUS', budget_state='UNKNOWN', outcome='TRANSPORT_OUTCOME_UNKNOWN', invocation_count=1, actual_provider=None, actual_model=None, input_tokens=None, output_tokens=None, cost_microunits=None, duration_ms=None, now=NOW)
        validate(connection, checkpoint)
    reader._validate_zhipu_execution = interleave
    try:
        reader.get_distillation_execution(record.execution_id)
    except StateStoreError as error:
        print('deterministic torn read:', str(error))
    fresh = repo.get_distillation_execution(record.execution_id)
    with repo._connect() as c:
        repo.verify_cloud_audit_database(c)
    print('fresh coherent read:', fresh.status, fresh.invocation_count, 'strict audit PASS; zero model calls')
```

Actual exit0 output:

```text
reader captured: PENDING 1 transaction: False
deterministic torn read: BigModel execution usage differs
fresh coherent read: AMBIGUOUS 1 strict audit PASS; zero model calls
```

Minimal repair: keep the checkpoint and all its associated audit/accounting reads in the same consistent read snapshot; retain strict corruption rejection and once-only protections. Do not swallow StateStoreError, reclassify genuine corruption, automatically dispatch/retry, or rewrite terminal records. Check other new-provider multirow readers for the same boundary without a broad refactor. This implementation predates007 and is inherited from the accepted audit chain; the new transport made the already present read race observable. It blocks the cumulative candidate regardless of which commit originally introduced it. Root was notified immediately; only Root assigns the repair.

## Independent verification

Commands use `/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`, `PYTHONDONTWRITEBYTECODE=1`, explicit `PYTHONPATH=/Users/developer/Documents/yia-worktrees/readiness-bigmodel-transport-review-r2/src` and temporary SQLite/DATA. Compile preceded pytest.

| Check | Actual independent result |
|---|---|
| In-memory compile all source |122PASS |
| Full seven-file pytest below |268PASS/1FAIL,89.98s; concurrency failure above |
| One failed concurrency test follow-up |1PASS2.03s; original failure retained |
| Original trusted165000B refusal plus actual Backup/Restore probe |PASS; zero key/wire, full SQL/DATA equality, no replay |
| Deterministic concurrent-read interleaving |Confirmed new P2-02; fresh state/strict verification valid |
| `python -m mypy --strict src` |122files PASS |
| `ruff check --no-cache src/youtube_intel/distillation.py tests/unit/test_bigmodel_distillation_adapter.py tests/integration/test_bigmodel_distillation_transport.py` |PASS |
| `git diff --check a7a9d710 00789303` |PASS |
| Fixed source/tests equality after run |435files exact007; combined path+bytes SHA256 `3ebf384c8da69bb2ebd9743d48fb48389cbe7f7332b205cc3b7ec194396c9bc4` |
| All packaged SQL |41 files exacta7 |
| Entire BigModel adapter/native wire/request bytes/credential helper/shared prompt AST segments |Exacta7; no profile change |

Exact seven-file command after the environment/interpreter prefix:

```text
-m pytest -p no:cacheprovider
tests/unit/test_bigmodel_distillation_adapter.py
tests/integration/test_bigmodel_distillation_transport.py
tests/unit/test_distillation_dispatch.py
tests/unit/test_moonshot_distillation_adapter.py
tests/unit/test_openai_distillation_adapter.py
tests/integration/test_task023b_distillation_reservation.py
tests/unit/test_backup_restore.py -q --tb=short
```

The new files include bounded valid admission/NO_NEW, consent absent/wronghash/wrongkind, profile invalidation, normal/generic production denial, malformed identity/usage/private reasoning, fixed TLS/deadline/DNS/no-replay and the repaired precredential refusal. Relevant old provider/reservation/Backup tests ran complete. Author579PASS384.83s is retained separately, not substituted for this failing independent group. Original reviewer578PASS408.14s and the original concrete input P2 remain valid historical evidence; overlapping totals are never added. Whole12file repetition was unnecessary after the deterministic new defect; no tests were deleted, skipped or weakened.

Reviewed full tiny repair diff, original task/report and current source under existing code-review-and-quality/security guidance. Graph discovery was already completed for these common service/state methods; current source supplied final delta. DIRECT reuse of pure preview and existing persistence/backup remains appropriate; no dependencies/framework/authority change. The original P2 correction itself is minimal and correct, but cumulative **REJECT** remains necessary for P2-02. No actual account, key, free entitlement, billing, network generation or semantic quality has been verified. Root owns repair assignment, independent re-review, integration, real public qualification and complete ordinary-user/production gates.
