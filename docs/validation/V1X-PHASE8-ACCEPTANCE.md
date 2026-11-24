# V1X Phase 8 acceptance evidence

Baseline: `c09a6ae5077867610420e1aed80fe3c7abb10c08`, schema 32.
Worktree: `/Users/developer/Documents/yia-worktrees/v1x-offline-transcription`.
Branch: `chatgpt/v1x-offline-transcription`.
Authority: owner's continuous Phase 8 goal; sole engineering executor.
Decision: [offline timed transcription](../decisions/V1X-PHASE8-DR-001-offline-timed-transcription.md).
Design: [workspace reference](../../DESIGN.md).

## Acceptance boundary

Implementation is complete independently of model provisioning. Production uses
the already approved MLX Whisper 0.4.3 SDK, with explicit local model selection,
bounded isolated processes, actual ffprobe/ffmpeg preprocessing and shared timed
authority. The machine's real isolated SDK probe took 2.875 seconds and reported
runtime detected/available, model absent, executor not yet compatible, MODEL_MISSING.
No compatible MLX model was available in the bounded inspected locations or
configured application path. No weights/binaries were downloaded or installed.

Real model production transcription was **not validated**. The successful media
execution tests use real WAV/MP4 bytes and installed media tools, with an isolated
deterministic SDK response fixture. They validate process/media/persistence/product
contracts, not acoustic accuracy or native model performance. They use no personal
media. Provisioning a compatible local model is the remaining machine limitation,
not an implementation blocker or a claim of production model qualification.

## Reproducible checks

All logs, fixture databases and screenshots live in this worktree's ignored
`.var/phase8`; Phase 7 browser regression fixtures live in `.var/phase7` here.
Protected Phase 7/main/M13 worktrees are never used for execution or writes.
The dedicated environment was created from the frozen lockfile using offline
cached dependencies; production dependencies, lockfiles and toolchain are unchanged.

| Gate | Result / evidence |
| --- | --- |
| Exact Phase 7 baseline | 45 tests passed before implementation; `baseline.txt` |
| Focused Phase 8 | 44 passed before final executable-spoof guard; `phase8-tests.txt` |
| Final operational + Phase 7 media hardening | 86 passed; `hardening-final.txt` |
| YouTube projection remediation + Phase 8 | 54 passed; `summary-remediation.txt` |
| Final Content failure presentation | 60 API/runtime/offline tests passed; `status-projection-final.txt` |
| Phase 7 backend regression | 109 passed; `phase7-regression.txt` |
| Integrated V1.x backend regression | 499 passed; `integrated-regression.txt` |
| Full backend final | 3364 passed, 1 preexisting optional asset skip, 2 negative-fixture warnings in 561.52 seconds; `full-backend-final.txt` |
| Ruff | `ruff check src tests`: passed |
| Strict mypy | `mypy --strict src`: 86 source files passed |
| Python syntax | `python -m compileall -q src tests`: passed |
| Frontend types | `npm run typecheck`: passed |
| All frontend tests | 174 passed in 7 files; `npm test -- --run` |
| Production frontend build | Passed, 45 modules; `npm run build` |
| Design lint | `designmd lint DESIGN.md`: 0 errors, 0 warnings |
| Diff checks | `git diff --check` and staged checks passed |
| SQLite | quick_check=ok; integrity_check=ok; foreign_key_check=[]; 27 READY media transcripts reverified after final server shutdown |
| Migration lineage | initialize verified unchanged file checksums; highest ordinal 32 (31 historical migration rows, accepted ordinal 029 gap) |

Focused commands include:

```text
.venv/bin/pytest -q tests/unit/test_offline_transcription.py tests/integration/test_offline_transcription_jobs.py tests/integration/test_offline_mixed_authority.py
.venv/bin/pytest -q tests/integration/test_runtime_composition.py tests/integration/test_offline_transcription_jobs.py tests/integration/test_offline_mixed_authority.py tests/unit/test_offline_transcription.py
.venv/bin/pytest -q
```

The preexisting optional canonical o200k asset test requires an explicitly
provisioned `YOUTUBE_INTEL_O200K_TEST_ASSET`; it remains skipped under its existing
condition. No tests/assertions were removed, skipped anew or weakened. The only
accepted-test edit moves the Phase 7 probe interception to the new bounded process
boundary, retaining all format/protocol assertions.

## Actual browser verification

Installed Chrome through existing Playwright runs real HTTP/SQLite/product UI.
The fixture executor alone is injected; actual media preprocessing, jobs,
validation, authority publication, Summary and durable Evidence are production code.

```text
.venv/bin/python tests/e2e/offline_transcription_fixture_server.py .var/phase8/browser-fixture --port 5588
YIA_API_BASE=http://127.0.0.1:5588 npm run dev -- --port 5589
node frontend/offline-transcription.e2e.mjs
node frontend/offline-transcription-restart.e2e.mjs
```

The restart script owns/stops/restarts its own fixture server; run it while the
manual server above is stopped. The installed Chrome and existing dependencies
are used; no browser/runtime downloads occur.

Eight Phase 8 flows: zh-CN/en at 320/768/1024/1440; media picker import, runtime
unavailable, model missing, READY, failed attempt, explicit retry, RUNNING,
millisecond timed transcript, normal Summary, durable Evidence, reload and mixed
YouTube + Local text + Local media Research. Final rerun uses the committed backend
with the YouTube projection remediation. Screenshots were visually inspected.
All eight have zero overflow, unexpected console/page errors and external requests.

Separate video flow: actual MP4 picker import and audio extraction, owned server
termination during RUNNING, restart -> INTERRUPTED, explicit retry -> READY,
restart with MODEL_MISSING -> existing trusted transcript/Summary/Evidence remain
readable. Previously completed audio remains trusted. Zero external requests/errors.

Accepted Phase 7 browser matrix: eight Local multi-source flows, both languages
and four widths, passed via `frontend/local-provider.e2e.mjs`. Integrated browser
matrix: eight Settings/Following/DA-fixture/Evidence/Obsidian/Knowledge Delta/
Research/History/Diff flows passed via `frontend/local-provider-regression.e2e.mjs`.
Both recorded zero overflow, console errors and external requests. Native OS picker
interaction and acoustic model transcription are not claimed by automated browser
injection. No new primary navigation was added; all matrices assert six entries.

## Required adversarial coverage map

Names below resolve to the three new Phase 8 test modules, retained Phase 7
adversarial module, frontend component tests and browser scripts.

| Owner cases | Evidence |
| --- | --- |
| 1–4 runtime/model/readiness distinctions | `test_truthful_unavailability`, `test_no_discovery_readiness_or_unsafe_model_assets`, real SDK probe; isolated model compatibility receipt required |
| 5–6 real short audio/video preprocessing | `test_real_preprocessing_and_isolated_process_contract` (.wav/.mp4), browser video/restart flow |
| 7–8 malformed audio/video | Phase 7 `test_malformed_media_never_gains_content_authority`, `test_playlist_disguised_as_audio_never_gains_authority` |
| 9–11 nonzero/timeout/output flood | `test_bounded_success_nonzero_timeout_and_flood`, `test_isolated_process_failure_cleanup`, owner-death heartbeat test |
| 12–18 malformed/timestamp/empty output | `test_invalid_transcript_fails_closed`, `test_malformed_response`; finite/nonnegative/positive/nonoverlap/duration bounds |
| 19–21 Unicode and language | `test_multilingual_timing_and_original_output`, `test_unknown_language`, persisted zh source language assertions |
| 22–23 original removed/modified | `test_original_media_removed_or_modified_still_uses_snapshot`, Phase 7 original move/delete/mutation/dedupe test |
| 24–25 snapshot/transcript corruption | `test_snapshot_and_transcript_tamper_fail_closed`, Phase 7 source/canonical/media/archive tamper tests |
| 26–27 concurrency/repeated clicks | `test_concurrent_clicks_one_job_and_no_scheduler_steal`, frontend double-click test, shared machine lock |
| 28–29 restart and durable success | `test_stale_restart_and_ready_without_runtime`, `test_success_restart_summary_evidence_and_idempotency`, live server crash/restart browser flow |
| 30–33 retry and no fallback | `test_failure_retry_new_attempt_no_fallback`, `test_changed_selection_rejected`, successful start never replaces trusted transcript |
| 34–37 normal Summary/Evidence/ownership/YouTube | normal Summary pointer and timed Evidence tests; mixed authority test; unchanged YouTube runtime-composition assertion |
| 38–40 Intelligence/mixed Research | `test_three_source_research_and_mixed_timed_intelligence`: sealed normal dependencies, deterministic packet except execution bookkeeping; browser mixed scope |
| 41–44 restore without runtime/model/weights | `test_backup_restore_without_runtime_and_no_model_weights`, restored new media correctly unavailable; raw/canonical/envelope authority survives |
| 45 privacy | `test_api_safe_diagnostics_no_paths_and_stale_selection`, UI private-error test, path assertions in failure browser flow; subprocess stderr discarded |
| 46–47 no network/cloud | OS network denial negative test (errno EPERM, not connection refusal), worker socket/HF-download denial, local media protocols, all browser external request lists empty |
| 48–50 zh-CN/en/responsiveness | five frontend component tests and eight-flow browser matrix; 320/768/1024/1440 zero overflow |
| 51 no navigation addition | all browser matrices assert six existing primary entries |
| 52 production DA unchanged | fixture-server production route NONE assertion, retained Local DA structural fixture tests, integrated V1.x regression |

Additional operational tests cover model/snapshot/temp symlinks, unsafe dimensions,
executable PATH spoofing, source verification once per Evidence presentation,
stale owned temp cleanup without following symlinks, and child termination after
application death. Strict source-size/duration/result/model/profile bounds are
documented in the decision record.

## Review and remediation

Authority review: executable existence cannot publish authority; compatibility and
content identity are separate. Shared raw validation cannot be bypassed by a typed
executor result. Source, transcript, canonical text, envelope, language, timed cues
and ownership are verified before trusted publication/reread. Original edits do
not change snapshots. Summary/Evidence fail closed on corruption or wrong Content.
Backup/restore verifies artifacts independently of machine runtime/model capability.

Operations review: one shared file-locked heavy slot, idempotent active start,
explicit new terminal attempts, owned group lifetime/output limits and owner-death
supervision. Restart reconciliation acquires the same lock before interrupting
orphan jobs or cleaning exact owned directories. No unrelated process is killed;
no transcript/private-path/stderr logging occurs. Capability checks and execution
run in background threads; sequential two-second polling runs only during checks
or active jobs. Every normal user action stays in Local Content UI.

Product review: actual Chinese/English UI and mobile/desktop screenshots inspected.
Missing runtime/model and retry status are understandable. Completed media uses
the normal Summary/Evidence path; diagnostics are secondary. UI completion refresh
was guarded across Content remounts after browser testing found repeated refresh.
Timed Evidence presentation was bounded to one source verification transaction,
avoiding repeated 64 MiB hashing per cue. Interrupted Summary completion recovers
without rerunning transcription or requiring a model.
Final screenshot review removed the obsolete unavailable placeholder during live
Local execution, synchronized header status with the polling surface, and wrapped
Local media metadata into readable rows at 320 pixels. The final eight-flow
browser matrix asserts live failed/running header copy and absence of the obsolete
placeholder. All frontend tests/types/build were repeated after that UI correction.

First full backend command `.venv/bin/pytest -q` found one regression:
`tests/integration/test_runtime_composition.py:555`, expected YouTube
`timestamped_key_points == []`, received a Local-style timed point. That run had
3362 passed, 1 failed, 1 skipped. The projection was limited to Local Content;
the accepted assertion was preserved. The affected 54 tests passed, followed by a
complete backend rerun. Failure evidence remains in `full-backend.txt`, remediation
in `summary-remediation.txt`, passing rerun in `full-backend-remediated.txt`.
The final product review also found failed transcription appearing as "Import
failed" in the Content projection. It now projects the accepted localized
TRANSCRIPTION_FAILED presentation while the job state remains FAILED. A new
assertion was added to the failure/retry test; all 60 affected API/runtime/offline
tests passed. A final complete backend run against frozen code is recorded in
`full-backend-final.txt`.

Final review covers the entire baseline-to-final diff: discovery, model identity,
processes, preprocessing, raw validation, transactions, persistence/reread,
Summary/Evidence, retries/restart, archive portability, UI and all changed tests.
No P0/P1 or material Phase 8 P2 remains after remediation and final gates.

## Preservation and closure

Local main stays clean at `08d62d8cb459a7d157f9c4a4c87cf23a3209d4b8`.
Phase 7 stays clean at `c09a6ae5077867610420e1aed80fe3c7abb10c08`.
M13 stays at `e228294f705401b0200439076c3378b78f9c9d84`, with its preexisting
owner changes preserved byte-for-byte in git diff and unchanged porcelain status.
No protected worktree, secrets, dependency/lockfile, deployment configuration or
migration changed. No push, PR, merge, accepted-history rewrite or installer ran.

Implementation commits: `62529e3` (executor/authority/jobs), `a822ebd` (Local UX,
browser acceptance/design reference), `981b69e` (Content failure presentation)
and `bc02e1d` (consistent live status/readable mobile metadata).
Restart acceptance repeat isolation is `47e3e6c`; each run adds a valid MP4 free
atom nonce so immutable hash dedupe does not reuse a previously successful fixture.
Final documentation commit/HEAD are supplied
in the owner report to avoid a self-referential hash.

Recommended Phase 9: explicitly provision a compatible local MLX Whisper model,
then run a bounded real acoustic/multilingual/accuracy/performance qualification
against nonpersonal media, including restart/Summary/durable Evidence and offline
network denial. Keep DA model qualification separate.
