# Independent review R4: machine settings and ordinary Content entry

## Fixed scope and verdict

**REJECT** fixed candidate `6e0f59e2f40fb62d371945cac0253346aa1616ce`. Two ordinary failure-path defects remain, and the mandatory affected group is not a passing final gate. No P0 or newly confirmed P1 was found. Return both fixes to the original Implementer; Reviewer made no business or test changes.

- Reviewer: `/root/long_wait_independent_review`,2026-10-21.
- Worktree/branch: `/Users/hua/Documents/yia-worktrees/readiness-long-input-wait-review-r4`, `codex/review-readiness-long-input-wait-r4`; exact candidate HEAD and clean state verified before review.
- Main delta: approved R3 candidate `b3546ff14627be51c27ce799e4de800ec1e9336d`→this candidate,20 files. Overall base remains `4f7cc46ed1381782288a2f4915dce027b38c3b94`.
- Read current root task/package, settings completion plan including explicit0.40.6 installation-only addition, and [R3 report2f3a8e8](/Users/hua/Documents/yia-worktrees/readiness-long-input-wait-review-r3/handoffs/TASK-READINESS-LONG-INPUT-WAIT-INDEPENDENT-REVIEW-R3.md). Applied code-review-and-quality and new-worktree graph-first discovery (fast/persistence=false).
- Only this report is written. No production/test edits, dependencies/install, model/tokenizer/network/cloud/owner access, integration, task-state changes or main adoption. Frontend used the provided link to existing dependencies.

## Required findings

### P2 — Native snapshot protection now reports an unrelated Content retry

Location: `src/youtube_intel/backup_restore.py:318` and `:330`; affected existing assertion `tests/integration/test_dogfood_day2_native_import.py:211`.

The new shared admission lock is held SH by `background_work(native_import=True)`. `stage_restore_stream` enters `_protect_background` EX before `_require_native_import_idle` at line461. Its lock conflict therefore maps to the generic Content-retry message and prevents the existing native-snapshot-specific failure feedback from executing. Restore remains closed, but users are told the wrong unfinished work is blocking it, and the existing required regression fails.

Independent exact reproduction:

```text
PYTHONPATH=src:tests:. <root-venv-python> -m pytest -q tests/integration/test_dogfood_day2_native_import.py::test_native_background_window_blocks_backup_and_restore_without_deleting_data
1 failed in0.72s
Expected regex: 'local snapshot'
Actual message: 'Content retry is still writing; wait before Backup or Restore.'
```

This is also the first F in the author's running76-file group (collection index149), independently mapped by collection and reproduced against the fixed R4 worktree. Preserve the correct native reason while retaining the new machine/DB lock and protection; do not weaken the assertion to accept an unrelated blocker or generic error.

### P2 — HTTP protocol discovery errors escape safe unavailable status

Locations: `src/youtube_intel/model_settings.py:120` and `:146`–`:151`; downstream `local_intelligence_settings.py:262`/`:267` and `:331`.

The new fixed installation probe catches OSError/ValueError/UnicodeError, while `http.client.HTTPException` subclasses such as `IncompleteRead` and `BadStatusLine` are not covered. A truncated chunked response or malformed local HTTP response can escape metadata discovery. The settings status loop and startup `bind_actual` also omit this exception family. Thus an unavailable or restarting local model service can turn Settings reads into500 and can abort normal composition reconstruction when a selection has already been saved, instead of retaining an accessible, safely unavailable route.

Independent deterministic no-network counter:

```python
from http.client import IncompleteRead
from youtube_intel.model_settings import ModelSettingsService
from youtube_intel.local_intelligence_catalog import CATALOG
c = CATALOG[1]
def interrupted():
    raise IncompleteRead(b'',20)
s = ModelSettingsService(
    object(),
    tags_fetch=lambda: {'models':[{'name':c.model,'digest':c.model_digest}]},
    version_fetch=interrupted,
)
s.fixed_local_identity(c)  # escapes IncompleteRead, should return UNAVAILABLE
```

Actual output: `version_probe_escaped IncompleteRead`. No credential method was used. Normalize bounded HTTP protocol failures at the metadata boundary or catch that exception family in its consumer, preserve connection closure, and verify tags/version discovery plus selected-runtime reconstruction and Settings read/retry. Do not convert bad discovery into READY, qualification or a model call.

## Independent checks

Interpreter: `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`; review cwd. Backend tests used `PYTHONPATH=src:tests:.`, strict mypy used `PYTHONPATH=src`. Import proof resolved R4's `local_intelligence_settings.py`.

| Check | Actual result |
|---|---|
| compileall src/tests/scripts | PASS |
| Ruff src/tests/scripts | PASS |
| strict mypy src | PASS,119 files |
| `git diff --check 4f7cc46...HEAD` | PASS |
| settings54 + existing long lifecycle/resource integration files |129PASS164.59s |
| risk-selected old accounting/budget/Cloud/NO_NEW/API/Backup/R14 |53PASS30.60s;283 deliberately deselected |
| runtime composition/background Following/model-settings group |78PASS79.43s |
| frontend TypeScript and production build | PASS |
| complete frontend tests,38files |980PASS32.41s; existing React act warnings |
| native snapshot exact prior regression | FAIL,1 case,0.72s |
| malformed metadata counter | FAIL, IncompleteRead escapes |

Primary backend command: `python -m pytest -q tests/integration/test_local_intelligence_settings.py tests/integration/test_long_input_wait_lifecycle.py tests/integration/test_long_resource_usage_closure.py`.

Risk selection: `python -m pytest -q tests/unit/test_local_fixed_runtime_profile.py tests/unit/test_local_model_capacity.py tests/unit/test_local_api.py tests/unit/test_backup_restore.py tests/integration/test_task022_personalized_distillation.py -k 'resource or usage or budget or no_new or known_response or consent or accounting or fixed_variant or v1_projection'`.

Runtime group: `python -m pytest -q tests/integration/test_runtime_composition.py tests/integration/test_background_following.py tests/unit/test_closure_model_settings.py`.

Frontend: `npm run typecheck && npm run build && npm test -- --maxWorkers=2 --minWorkers=1`. No dependency changes or installs were performed. Backend syntax/type checks preceded test debugging.

## Reviewed boundaries and preserved evidence

- Machine then DB lock ordering is consistent. The DATA-derived sibling scope shares a machine gate across external/legacy database paths and separates different DATA roots. API mutation wrapper covers local/cloud/manual/check-stale; native/stream entry participates; worker/CLI scheduler and legacy CLI bootstrap enter the barrier. Backup control routes correctly avoid an outer SH→inner EX upgrade and own their protected EX windows.
- Apply holds EX through complete quiescence/closure and persisted journal/CAS. The durable journal plus per-runtime bound_etag keeps old compositions closed after the EX window and after new composition clears the journal. Safe cancellation remains available and still checks original proof. Pending/active/unknown/cloud/budget work is not auto-cancelled or rewritten.
- The server schedules settings shutdown before sending202, covering the specifically reproduced BrokenPipe ACK-loss boundary. Worker.stop joins before CLI reconstruction; composition rereads sidecar despite cached AppConfig. Runtime provider/model/digest, etag and installation metadata must match before journal removal; actual route is distinct from desired candidate and qualification.
- Invalid bounded regular bytes remain CAS-repairable; unsafe symlink/hardlink/directory/permissions/oversize identity stays closed. Recovery only recognizes recorded old/new bytes; invalid old text is not copied to the journal. The sidecar/journal is outside DATA/ZIP and restored DATA does not overwrite destination machine selection. Historical proof reading remains independent of current-code hashes.
- Explicit0.40.6 catalog entries carry no execution options/profile/permit. Unknown0.40.7/wrong digest is rejected. Existing0.40.1 profiles, capacity, permits and qualification resources remain unchanged; correct short/long unqualified route yields truthful WAIT0 with no transport. Old8b config is retained for fast/scoring/Summary and YAML is not rewritten.
- UI preserves explicit draft/CAS and offers refresh/retry, polls via GET after an unknown ACK rather than replaying PUT, and distinguishes actual route from closed qualification. Existing Intelligence action/result panel moves ahead of transcript/Evidence without removing its contents. New English/Chinese copy and unchanged historical result/deep-link behavior are covered by the full frontend suite; root's real headed GUI remains separate acceptance evidence.
- Independently verified all495 source/frontend/test file hashes match `settings-all-source-freeze.json`. All40 SQL001–041 resources are byte-identical to R3; SourceAuthority bytes, TimedTranscriptCueWrite AST, short/long profiles, capacity module and empty qualification resource are unchanged. No test assertion weakening, migration rewrite, production dependency, credential/config edit or unrelated refactor identified.
- Inspected task-owned genuine-settings-v9 receipt metadata only, SHA-256 `6168ca00e9c4094fa5985079e0db2137f93c1e8cf50d35e48804f8823a425039`: actual0eMzc-WnBfQ114 Evidence/2406cues, same cached config,9b/profileNone route,79tables/19DATA equality after restore, original stock/old rows unchanged, old8b histories and priorv6proof read, machine selection retained and model HTTP/load/generation0. External metadata is explicitly a fixture. This is author backend evidence, not independent real installation verification, GUI or qualification.

The author's unique76-file group is still running and already contains the native failure above; no final result JSON existed at inspection. Do not count it as a final passing gate, merge a changing source result, or relabel previous975+5 frontend/1794+6 backend/fixture failures as one all-green run. Root confirmed the new actual GUI reached Settings0.40.6→applied9b without changing79SQL/19DATA, but root has not accepted the slice. Corrections require a new fixed SHA and bounded independent delta review. Whole-Goal generation/real qualification/positive Save/Topic/main adoption remain outstanding.
