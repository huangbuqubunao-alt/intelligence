# Phase 12 self-review and acceptance ledger

Baseline: a81b8e90a662eab72dda28fdc2140362649d9544.
Sole executor, dedicated worktree; no delegated review or owner approval needed.

## Provider neutrality

Reviewed shared source identity/observations/checks, adapter seam, Source Run
composition, dispatch, frontend, restore validators and ordinary Content runtime.
Bilibili enumeration is encapsulated; YouTube supplies resolve/enumerate/enroll to
the same lifecycle. Identity/Content validation is provider-scoped; persistence,
frontier, retry, pause, cooldown, source health and scheduling are shared. No new
source-run table, feed/subscription domain, plugin framework or migration.

## Incremental correctness

Reviewed baseline/new observations, canonical aliases, monotonic frontier, overlap,
partial enumeration, pending enrollment, atomic pause, restore validation and remote
removal. Reordering/duplicate entries do not create updates; publication timestamps
are not the sole coverage proof. Lost overlap remains incomplete without resetting
history. Unsupported items remain recorded; prior stored artifacts never disappear.

Findings remediated:

- Transcript-only helper queued scoring after stopping execution. Now scheduling
  also stops at TRANSCRIPT_READY; Backup has no orphan active scoring job.
- Partial checks updated last-success while preserving verified frontier. Only a
  complete successful acquisition check now updates the timestamp.
- Timed public YouTube captions were omitted from the shared Content API projection.
  Verified cues now render through the existing transcript view.
- Initial-caption transient retry was stranded after marking its discovery enrolled.
  An ordinary retry job leaves that identity PENDING and safely resumes next check.
- Stable canonical source id could be rebound before any Content existed. Validator
  rejects a mismatched canonical channel id, preserving supported legacy UUID adoption.
- Bounded offline tracking checks became unresolved Source Runs and blocked Backup.
  Tracking failures now terminate FAILED; paused queued tracking runs cancel without
  provider access. Normal processing/ambiguous dispatch semantics remain protected.

- Cross-provider stale checks inherited the list's source creation order. Newer
  follows repeatedly occupied the bounded slots before an older creator/channel.
  Sorting durable next-check time provides fair automatic checking without increasing
  the three-check event bound. The distinct-follow-time regression failed before
  remediation and passes afterward; shared actual UI confirms both provider filters.
- Date-only YouTube metadata at midnight incorrectly rejected a same-day new video.
  The persisted verified feed time now resolves same-day ambiguity while an older
  metadata date still rejects the item. Content metadata is preserved.
- A malformed video metadata response retained PENDING but returned COMPLETE.
  Nonterminal enrollment errors now propagate truthful source health and preserve
  last-success; the same identity enrolls once after recovery.

## Product review

Reviewed actual Chrome production UI, Chinese/English and 320/768/1024/1440px.
Shared form/detail, video-vs-channel distinction, Content follow, baseline, no-op,
new captions/missing captions, Check Now, pause/resume, update/attention filters,
mixed providers, Research, Delta, restart/offline, primary navigation and wrapping.
Manual YouTube video rows now state their actual import provenance. Channel inputs
cannot accidentally use the one-video form. Channel names/titles are rendered as
plain React text. No caption absence action routes to acoustic inference.

Harness findings were fixed rather than filtering console errors or weakening
assertions: canonical row selection, translation label, fixture upload time relative
to each follow, production Deep Analysis read service with no execution route,
restart-safe fixture config and waiting for a finished offline check. No tests,
assertions, coverage thresholds, dependency/toolchain or CI commands were removed.

## Evidence and scope

The raw red/green/focused/static/regression logs live in the local evidence folder
`/tmp/intelligence-phase12-evidence`; final copies and machine-readable browser,
restore, database, protected-worktree and final-diff records live beside this file.
Live public retrieval was attempted without cookies, credentials or bypass and was
unavailable with NETWORK_UNAVAILABLE; successful real resolution/baseline/repeat
is not claimed. Deterministic public fixtures verify incremental discovery.

Frozen acoustic and Deep Analysis capability states, historical migration bytes,
protected worktrees and all existing manual-provider paths remain acceptance gates.
Always-on execution, backfill, explicit caption refresh, notifications and other
providers remain outside this phase.


## Final gates on committed production code

Backend: 3,597 passed, one inherited skip requiring a provisioned canonical o200k
asset, two existing adversarial-fixture warnings (duplicate ZIP member and forged enum serialization). No new skip or weakened assertion.
Phase 12 plus shared tracker/ingestion focused: 101 passed. Named Phase 11/10B,
9R/9, 8, 7, Research, manual YouTube and integrated regressions: 842 passed in
the final broadened named regression gate (the earlier selected gate passed 425).
Frontend: 184 passed; typecheck and production build passed. Ruff all source/tests,
strict mypy (96 source files), compileall and both design lints passed.
Online, restarted offline, and restored offline Chrome matrices each passed eight
Chinese/English × four-width flows with zero overflow, external requests or
console errors. Schema 34 quick_check/integrity_check/foreign_key_check passed;
All 33 historical SQL migration files match baseline bytes; historical migration
029's existing lineage remains protected by the full state regression. All 22 protected worktrees
preserved, including pre-existing owner changes.

Failure evidence retained:

- `PYTHONPATH=src /Users/developer/youtube-intel/.venv/bin/python -m pytest -q
  tests/integration/test_youtube_following.py::test_initial_caption_network_retry_remains_durable_and_recovers`
  failed with `assert 'COMPLETE' == 'OFFLINE'`. The affected runtime enrollment
  marked a retry-pending caption acquisition enrolled; preserving PENDING and
  resuming the ordinary retry job fixed it. See caption-retry-red.txt and the
  final 101-test focused gate.
- The same command targeting
  `test_failed_bounded_tracking_run_is_terminal_and_backups_work_offline` failed
  with `NEEDS_ATTENTION is FAILED` for each provider. The shared orchestrator's
  unresolved-discovery branch blocked offline backup. The tracked-only terminal
  failure branch fixed both cases; ordinary processing attention tests still pass.
- Earlier mixed restore validation failed with `BackupRestoreError: JOBS_ACTIVE`.
  Stopping transcript-only execution had still scheduled scoring. Stopping the
  next-job scheduling at the transcript boundary resolved the restore failure.

The additional actual-UI gate passed both languages at 320px: YouTube and Bilibili
share detail, Check Now, pause/resume and all five filters. Insight filtering
correctly remains empty without admitted Intelligence; polling/summary acquisition
cannot manufacture an insight. Paused Check Now is disabled and resume preserves
verified frontier and update count.

Browser progress synchronization was verified with an independent Chrome probe:
`waitForFunction(async () => false)` returned false immediately instead of polling.
The Phase 12 harness now polls the local API with a fixed 30-second budget and
500ms spacing, waiting for a durable baseline and completed check before introducing
fixture uploads. This preserves the actual baseline, update and DOM assertions,
including under concurrent application-lifecycle checks; see async-predicate-probe.txt.

The final rapid-check experiment sends twelve concurrent commands per provider.
Each creates only one new Source Run, terminates truthfully offline and preserves
its verified frontier; see rapid-check-browser.json. Backup/Restore compares all
five authority tables exactly, including source identities and check receipts,
without network access. The final detail DOM also confirms update count 2.

Additional failure evidence: `pytest -q tests/integration/test_youtube_following.py
-k feed_publication_disambiguates` failed with an empty library instead of the new
video; date-only-red.txt records it. `-k invalid_video_metadata_preserves` failed
with COMPLETE instead of PROVIDER_ERROR; enrollment-error-red.txt records it.
Both pass in the final focused gate. An initial focused command used a nonexistent
unit-test path, ran zero tests, and was corrected to the integration paths.
