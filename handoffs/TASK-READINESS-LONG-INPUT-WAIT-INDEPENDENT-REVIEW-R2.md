# Independent review R2: long resource usage closure

## Metadata

- Reviewer: `/root/long_wait_independent_review`, 2026-10-21 Asia/Shanghai.
- Overall base: `4f7cc46ed1381782288a2f4915dce027b38c3b94`.
- Prior rejected candidate: `4da67d55d73d3db214825d5b19368bb36caac507`.
- R2 fixed candidate: `a2861e38dd36124a680377bbdc55f9ff105e53f3`.
- Review worktree/branch: `/Users/hua/Documents/yia-worktrees/readiness-long-input-wait-review-r2`, `codex/review-readiness-long-input-wait-r2`; exact HEAD and clean state confirmed before review.
- Prior REJECT report remains unchanged in separate worktree, commit `f9db3e4f74903be03b222a92412a63c1bb53f8ca`, [report](/Users/hua/Documents/yia-worktrees/readiness-long-input-wait-review/handoffs/TASK-READINESS-LONG-INPUT-WAIT-INDEPENDENT-REVIEW.md).
- Applied code-review-and-quality, read newer root task and prior report, and indexed this new worktree fast/persistence=false before graph-first code discovery. Only this report is written; no business/test changes, model/tokenizer/network/owner access, integration or task-state changes.

## Verdict: REJECT

The original direct/list/NO_NEW projection bypass is repaired for the rows the code actually enumerates. The new helper runs `verify_execution` and `read_cancellation` on the existing connection before trusting raw usage, and the API converts `StateStoreError` to `409 RESOURCE_USAGE_UNAVAILABLE`. The helper does not call either public usage getter, so there is no recursive getter loop; both getters retain their `finally: connection.close()` error handling. Existing nonlong rows leave the helper immediately and keep the old projection behavior.

### P1 — Case-sensitive reverse enumeration hides malformed family checkpoints

Location: `src/youtube_intel/state.py:11710`.

The new reverse enumeration uses `execution_id GLOB 'distillation:long-timed*'`. SQLite GLOB is case-sensitive, while the shared family predicate explicitly uses `execution_id.casefold().startswith(FAMILY)` and direct reads reject uppercase/mixed-case family identities. If a malformed case-variant checkpoint loses its ledger, it is absent from all bounded ledger projections and also absent from this GLOB query. Consequently the list/API reports an empty, successfully verified history despite retained reserved-family work whose direct getter fails closed. This misses the exact new reverse guard's purpose and the whole reserved-family contract.

Independent isolated reproduction on a2861e3:

1. Create the normal synthetic 21-Evidence workspace and reserve a valid WAIT0 execution.
2. In the private attack fixture only, disable FK enforcement, save/drop triggers, uppercase the checkpoint execution ID, delete its physical ledger, restore every original trigger and close the connection. This is a malformed-family-plus-missing-ledger counter; no product/schema resources are modified.
3. `get_distillation_resource_usage(uppercase_id)` raises `StateStoreError`.
4. `list_distillation_resource_usage()` returns `()`.
5. GET `/api/v1/settings/resource-usage` returns HTTP 200 and `{'usage': []}`; required result is failed verification / API409.

Actual output:

```text
direct REJECTED StateStoreError
list ACCEPTED ()
api (<HTTPStatus.OK: 200>, {'usage': []})
```

Required repair: make reverse family enumeration match the shared reserved-family predicate, including case variants, before any bounded projection can omit missing-ledger work. Add direct/list/API counters combining mixed/uppercase malformed or unknown family with absent ledger; retain the valid WAIT0/cancellation and nonlong accounting controls. Return the repair to the original Implementer. Reviewer made no product fix.

## Independent checks and comparison

All commands ran in the R2 review worktree using `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`. Tests used `PYTHONPATH=src:tests:.`, mypy `PYTHONPATH=src`. Import proof printed R2's `src/youtube_intel/state.py`.

| Check | Result |
|---|---|
| `python -m compileall -q src tests scripts` | PASS |
| `python -m ruff check src tests scripts` | PASS |
| `python -m mypy --strict src` | PASS, 117 sources |
| `git diff --check 4f7cc46...HEAD` | PASS |
| Four long integration files (old lifecycle/storage/source boundaries plus new resource closure) | PASS, 96 cases, 97.40 s |
| Risk-selected legacy/R14 accounting, budget, NO_NEW, Cloud, API and Backup cases | PASS, 53 passed / 283 deselected, 32.45 s |
| Independent case-variant + missing-ledger direct/list/API counter | FAIL, P1 above |

Long command: `python -m pytest -q tests/integration/test_long_input_wait_lifecycle.py tests/integration/test_long_completion_storage_contract.py tests/integration/test_long_source_boundary_counters.py tests/integration/test_long_resource_usage_closure.py`.

Risk-selected command: `python -m pytest -q tests/unit/test_local_fixed_runtime_profile.py tests/unit/test_local_model_capacity.py tests/unit/test_local_api.py tests/unit/test_backup_restore.py tests/integration/test_task022_personalized_distillation.py -k 'resource or usage or budget or no_new or known_response or consent or accounting or fixed_variant or v1_projection'`. Deselection is a bounded independent delta-review choice, not a substitute for the mandatory final affected group.

- R2 changes only state.py and local_api.py product code, one new 26-case test file, handoff and evidence metadata. Other eight frozen product files, old 70 dedicated cases and all 34 legacy fixture files are byte-identical to 4da67d5. No DDL/dependencies/qualification changes or assertion weakening.
- All ten product source hashes match candidate evidence JSON. All 39 prior migration resources in the 001–040 range remain byte-identical to overall base. Qualification resource remains `records=[]`, unchanged SHA-256 `0bf8f9526727d0c6f3c217ab3caf5630dc23cd97b6d1bcee525512a043d20347`.
- Read genuine-v5 receipt metadata only: SHA-256 `a11845389c8a1cde77d6e06ba5699b910a0aa1d59c52d6ca6d4ca22efd697c6f`, 114 Evidence/2406 cues, 79 tables/19 DATA files, all rows/files equal after restore, source stock unchanged, one appended cancellation and zero model/HTTP calls. These remain author backend evidence, not independently repeated native GUI or model qualification.

## Failed final group and remaining gates

Independently inspected author `.var/long-wait/affected-repaired-final.log`: **6 failed, 1794 passed, 1 warning, 1401.93 s**. It is not a passing final gate. Failures are doctor current-schema recognition, fresh-m014 table-list slicing, historical migration40 rollback expected41 versus pinned40, and three tracked counter archive fixtures rejected at migration-history validation rather than reaching their intended ownership/file-closure validator. Root already returned these to the Implementer. Do not weaken expected error-stage assertions; repair schema fixture identity or product current-version handling and reverify on a new SHA.

The prior interrupted mixed-source 57-file run is not counted as a final pass. Current R2 remains rejected for the residual P1 above and lacks the passing mandatory final affected result. Root native GUI/whole-Goal regression/real qualifications/positive long generation and Save/Topic remain separate outstanding gates. No APPROVE, ACCEPTED, DONE or main adoption is granted.
