# Independent review R4: machine settings and ordinary Content entry

## Fixed scope and verdict

**REJECT** fixed candidate `6e0f59e2f40fb62d371945cac0253346aa1616ce`. Two ordinary failure-path defects and the subsequently confirmed restart/drain P1 below remain. The mandatory affected group is not a passing final gate. Return repairs to the assigned sole Implementer; Reviewer made no business or test changes.

- Reviewer: `/root/long_wait_independent_review`,2026-10-21.
- Worktree/branch: `/Users/hua/Documents/yia-worktrees/readiness-long-input-wait-review-r4`, `codex/review-readiness-long-input-wait-r4`; exact candidate HEAD and clean state verified before review.
- Main delta: approved R3 candidate `b3546ff14627be51c27ce799e4de800ec1e9336d`→this candidate,20 files. Overall base remains `4f7cc46ed1381782288a2f4915dce027b38c3b94`.
- Read current root task/package, settings completion plan including explicit0.40.6 installation-only addition, and [R3 report2f3a8e8](/Users/hua/Documents/yia-worktrees/readiness-long-input-wait-review-r3/handoffs/TASK-READINESS-LONG-INPUT-WAIT-INDEPENDENT-REVIEW-R3.md). Applied code-review-and-quality and new-worktree graph-first discovery (fast/persistence=false).
- Only this report is written. No production/test edits, dependencies/install, model/tokenizer/network/cloud/owner access, integration, task-state changes or main adoption. Frontend used the provided link to existing dependencies.

## Required findings

### P1 addendum — Old daemon HTTP requests survive shutdown and can abort Restore reconstruction

Locations: `src/youtube_intel/local_api.py:3713`, `cli.py:174`–`:176`, `backup_restore.py:347`–`:353` and `:547`; new machine EX acquisition at `backup_restore.py:262`/`:318`.

After the original R4 report, root's real headed GUI completed installed0.40.6 selection, actual9b route, full114/2406 WAIT0/cancellation and a genuine process restart with79SQL/19DATA equality. It then created/downloaded a real ZIP, selected it with the macOS native file chooser, staged it and confirmed RESTORE. Normal cached-config factory reconstruction terminated the service. Preserved root log `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.var/local-settings-r4/api-restart.log` shows `runtime_composition.py:510`→`recover_and_apply_pending_restore:547`→`_protect_background:318`→machine `store_lock(anchor):262`→`RetryConflict` at `tracked_retry_context.py:93`, ultimately uncaught `BackupRestoreError`. The first machine lock is contended; this is not staged-pair validation failure or an observed model invocation.

Read-only source/stdlib diagnosis establishes a lifecycle hole. `serve_loopback` returns the standard `ThreadingHTTPServer`, whose installed `daemon_threads` is True. Installed `socketserver.ThreadingMixIn.process_request` marks request threads daemon; `_Threads.append` explicitly discards daemon threads; `server_close` joins only that registry. Therefore `server_close()` does not drain in-flight request handlers. `worker.stop()` joins the source worker only. The production CLI and preserved root harness both call server_close then worker.stop before immediately reconstructing the runtime, without draining HTTP request holders.

There is a concrete normal browser path into that hole: `App.tsx:3733` confirmRestore calls `refreshStatus` in its finally block; that GET `/backup-restore/status` enters `BackupRestoreService.readiness`, which takes machine EX and performs full schema/artifact closure before adding RESTORE_PENDING to its public result. It does so even after the restore marker/restart request is set. The0.25s timer can stop accepting requests while this old readiness handler still holds EX. Because that handler is daemon and unjoined, a new composition can immediately fail its nonblocking Restore EX acquisition exactly as the preserved stack shows. An already-admitted mutation can pose the same old-handler lifecycle problem; draining the worker alone is insufficient. The historical log does not identify a specific lock-owning thread, so attributing its actual owner to that particular GET remains inference; the missing HTTP drain and overlapping ordinary GET/EX path are independently verified in fixed source and installed stdlib.

Required repair: establish a restart boundary that stops admitting new old-runtime requests and drains or safely cancels bounded in-flight request handlers before new Restore/configuration recovery and worker startup. Keep machine/DB exclusion, pending markers and unknown authority closed; do not remove EX, add a lucky sleep, or allow old handlers to write against an activated pair. Preserve graceful handling of external contention with an actionable recovery state rather than crashing the server loop. A deterministic controlled old-handler/EX overlap counter and real GUI native chooser→stage→confirm→restart need to demonstrate this boundary, including disconnect/cancel paths and non-waiting unknown/external work. Native import shutdown must retain its existing lifecycle as well.

This addendum was source/log/stdlib inspection only: no QA service was started, the failed scene was not changed or restarted, no broad test group was rerun, and no product file was modified. Root forwarded the diagnosis to the replacement sole writer `/root/settings_recovery_writer`.

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

At the original report the author's unique76-file group was still running with the native failure. The preserved final log, subsequently inspected during the P1 diagnosis, is **2159PASS/9FAIL/1warning1656.10s**. Failures are native feedback; LOCAL_TEXT model wait; LOCAL_TIMED model/budget wait; existing-video receipt; cancelled LOCAL_TIMED BackupRestore; cancelled LOCAL_TEXT039 proof restore; and two retained-subtitle background error-priority cases. This is not a final passing gate. Do not merge a changing-source result or relabel previous975+5 frontend/1794+6 backend/fixture failures as one all-green run. Root has not accepted the slice. Corrections require a new fixed SHA and bounded independent delta review. Whole-Goal generation/real qualification/positive Save/Topic/main adoption remain outstanding.
