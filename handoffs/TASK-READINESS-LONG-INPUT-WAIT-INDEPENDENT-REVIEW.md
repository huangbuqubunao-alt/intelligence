# Independent review: long input wait lifecycle

## Metadata and scope

- Task: TASK-READINESS-LONG-INPUT-WAIT-LIFECYCLE; role: independent Reviewer `/root/long_wait_independent_review`.
- Fixed base: `4f7cc46ed1381782288a2f4915dce027b38c3b94`.
- Fixed candidate: `4da67d55d73d3db214825d5b19368bb36caac507`.
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-long-input-wait-review`.
- Branch: `codex/review-readiness-long-input-wait`.
- Reported: `2026-10-20T22:12:35Z` (`2026-10-21` Asia/Shanghai).
- Candidate HEAD and clean worktree verified before review. Only this report is written by the Reviewer; no product/test changes, integration, main adoption, task-state changes or model/network calls.
- Read repository instructions, product/design/reuse context, newer root task/package and long persistence/probe plans. Applied `code-review-and-quality`; indexed this review worktree with codebase-memory fast/persistence=false before code discovery. Jev routing unavailable (HTTP 451); retained default strong independent review.

## Verdict: REJECT

### P1 — Resource usage getters bypass the new long authority gate

Locations: `src/youtube_intel/state.py:11493` (physical usage early return), `src/youtube_intel/state.py:11616` (NO_NEW overlay), and `src/youtube_intel/state.py:11698` (list projection); publicly reachable through `src/youtube_intel/local_api.py:2241`.

The new shared long validator is called by `get_distillation_execution`, but neither `get_distillation_resource_usage` nor `list_distillation_resource_usage` invokes it. Physical rows are returned immediately, while NO_NEW rows only pass the legacy binding validator. Therefore the application exposes long model-result statuses and accounting even when the exact same execution is rejected for invalid frozen identity or disabled claimed/result authority. This violates the first-slice closed-result contract and the required shared ledger/getter validation before zero overlays. It also means a corrupted or missing long proof is ignored by the public resource-usage surface.

Independent reproduction used the candidate's own explicit synthetic SQL fixtures (`pending`, `receipt`, `finalize` from `test_long_completion_storage_contract`). These create the intentionally nonauthoritative `PREFIX + 'f' * 64` execution and commit final-contract rows without real model authority. No trigger changes, product edits, model calls or network were needed. For each branch, `get_distillation_execution` raised `StateStoreError`, but both resource getters accepted:

| Synthetic branch | Usage/list status | Invocation count | Outcome |
|---|---|---:|---|
| INTELLIGENCE | SUCCEEDED | 1 | SUCCEEDED |
| NO_NEW_INTELLIGENCE | SUCCEEDED_NO_NEW_INTELLIGENCE | 1 | NO_NEW_INTELLIGENCE |
| REJECTED | REJECTED_OUTPUT | 1 | REJECTED_OUTPUT |

For NO_NEW, `app.handle('GET', '/api/v1/settings/resource-usage')` returned HTTP 200 and included `('SUCCEEDED_NO_NEW_INTELLIGENCE', 1, 'NO_NEW_INTELLIGENCE')` for that rejected execution. This is observable application behavior, not merely raw fixture inspection.

Required repair: recognize the whole reserved long family and run the shared historical/execution validator on the same connection before every physical return, NO_NEW overlay and list projection. Keep legitimate raw WAITING_MODEL usage after logical cancellation, preserve old generic/Cloud semantics, and reject the unimplemented long claimed/result branches. Add counters for direct getter, list and public settings endpoint, including unknown/malformed family and missing/corrupt provenance. The current SQL storage test only asserts execution getter rejection (`test_long_completion_storage_contract.py:321`), leaving these paths uncovered. Return the repair to the original Implementer; Reviewer did not fix it.

Reproduction command structure (review cwd; private temporary fixture directory):

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from conftest import _load_module
m = _load_module('test_long_completion_storage_contract')
with TemporaryDirectory(prefix='long-review-') as d:
    repo, root, sid, vid, service, app, _ = m.long.workspace(Path(d).resolve(), 21)
    c, proof, checkpoint = m.pending(repo, service, sid, vid)
    checkpoint['execution_id'] = proof['execution_id']
    m.finalize(c, proof, checkpoint, m.receipt(proof, 'NO_NEW_INTELLIGENCE'))
    c.commit()
    c.close()
    # Rejects:
    # repo.get_distillation_execution(proof['execution_id'])
    # Currently accepts:
    repo.get_distillation_resource_usage(proof['execution_id'])
    repo.list_distillation_resource_usage()
    status, payload = app.handle('GET', '/api/v1/settings/resource-usage')
    assert status == 200
    assert any(x['execution_id'] == proof['execution_id']
               and x['status'] == 'SUCCEEDED_NO_NEW_INTELLIGENCE'
               for x in payload['usage'])
```

## Independent checks

All commands used `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python` with review cwd. Tests used `PYTHONPATH=src:tests:.`; strict typecheck used `PYTHONPATH=src`. Import proof printed the review worktree's `src/youtube_intel/long_distillation_persistence.py`.

| Check | Result |
|---|---|
| `python -m compileall -q src tests scripts` | PASS |
| `python -m ruff check src tests scripts` | PASS, All checks passed |
| `python -m mypy --strict src` | PASS, 117 source files |
| `git diff --check 4f7cc46...HEAD` | PASS |
| `python -m pytest -q tests/integration/test_long_input_wait_lifecycle.py tests/integration/test_long_completion_storage_contract.py tests/integration/test_long_source_boundary_counters.py` | PASS, 70 cases, 55.99 s |
| Existing Backup/Restore, LOCAL_TEXT, SourceRun and pure R13/R14 profile/codec/projection/canonical group | PASS, 497 cases, 132.00 s; one expected duplicate-ZIP-member warning from the negative archive fixture |
| Independent synthetic final-contract direct/list/API counters above | FAIL: confirmed P1 |

The existing group command is `python -m pytest -q tests/unit/test_local_fixed_runtime_profile.py tests/unit/test_long_grounding_codec.py tests/unit/test_long_grounding_projection.py tests/unit/test_long_distillation_profile.py tests/unit/test_long_card_canonical.py tests/unit/test_backup_restore.py tests/integration/test_local_text_input_proof.py tests/integration/test_task023a_source_run_persistence.py`.

## Diff and provenance review

- Reviewed the fixed 49-file diff as one full-source persistence/lifecycle vertical, including new final-contract SQL and tests. Of its breadth, 34 legacy fixture files change current schema expectations, migration resource/list/table counts, or future-invalid42 assertions. The genuine historical migration40 rollback remains explicitly pinned to <=40. No assertion removal, skipped tests, weakened thresholds, dependency change, lockfile change, unrelated refactor or formatting churn identified.
- All 39 pre-existing migration resource files in the 001–040 range are byte-identical to base (the existing sequence contains a prior gap). Migration41 appends exactly two tables and long guards. Reviewed final positive/NO_NEW/REJECTED branches, deferred conditional usage FKs, nullable observations and reliable integer checks. Dedicated SQL tests pass; production result qualification remains closed.
- `runtime_composition.py` remains byte-identical. The one SourceRun candidate callsite change is explicitly within the newer root task scope. Old LIMIT21 and generic20/Cloud/LOCAL_TEXT boundaries remain unchanged.
- All ten candidate product source hashes match the frozen implementer evidence JSON. The qualification resource is unchanged, `records=[]`, SHA-256 `0bf8f9526727d0c6f3c217ab3caf5630dc23cd97b6d1bcee525512a043d20347`.
- Inspected genuine backend receipt metadata only, not source body/private/owner data. Receipt SHA-256 `067f5d505b7a4a1168c950b6dc2c6cda4c6d2d31657a45847b17d592e04cb495` records video `0eMzc-WnBfQ`, 114 Evidence/2406 cues, 79 SQL tables/19 DATA files equal after restore, old rows/source stock unchanged, m037 1→2 with one new long cancellation, model/HTTP calls 0. These genuine counts/equalities remain author evidence, not a new independently rerun native GUI or model qualification.
- Dedicated independent cases verify ordinary POST→WAIT0→cancel→restart→BackupRestore, legacy34–40 restore compatibility, complete source/rollback counters, Summary/policy refresh, source ambiguity, 4103/byte overflow, cancellation races, raw-wait settled SourceRun quiescence and rehashed ZIP negatives. These passing checks do not excuse the missing resource-reader boundary.

## Failures, limits and handoff

- Reproduction harness first used macOS `/var` TemporaryDirectory spelling and hit existing `source storage cannot be rebound`; fixed the harness with `Path(d).resolve()`. A first API-print probe used `payload['items']` and raised `KeyError`; corrected the harness to the actual `payload['usage']`. Neither was a product/test modification or hidden failure. The final independent reproductions above completed and confirmed P1.
- Author's separate 57-file affected group was still running when inspected (not labeled passed); two collected pre-correction040 assertions require the planned precise rerun and honest original result. This report does not accept that unfinished verification story.
- No real model load/generation, tokenizer, paid service, native GUI, formal data/Vault access or production changes. Full long generation, qualification, Save/Topic positive use, root GUI and whole-Goal regression remain outside this slice's completion evidence.
- No P0 found; one unresolved P1. Return to Implementer for repair and a new fixed candidate; any new SHA requires re-review. No APPROVE, ACCEPTED, DONE or main adoption is granted here.
