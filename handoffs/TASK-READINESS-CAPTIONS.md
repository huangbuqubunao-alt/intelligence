# READINESS-CAPTIONS implementation handoff

## Metadata

- Role: Implementer; original interrupted worker continued by `/root/caption_resume`.
- Worktree: `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness-captions`.
- Branch: `codex/task-readiness-captions`; base `0eeb288`.
- Implementation commit: `0b6b6284514beb5c2269c8bad65948df090a962c`.
- Reported: 2026-10-13, Asia/Shanghai.
- Recommendation: ready for independent review, not DONE or adopted.
- Exact security-sensitive state.py repair scope approved by user on 2026-10-12:
  “批准该精确隔离补全范围，继续验收”. Root proposal is
  `docs/validation/end-to-end-user-readiness/CAPTION_REPAIR_PROPOSAL.md` in
  `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness`.

## Result and implementation scope

Native JSON3 can contain append controls and overlapping rolling caption events;
accepted plain text does not prove nonoverlapping source timing. The previous
runtime could report completion while the Content UI kept saying it was organizing.

The subtitle adapter now tries at most one VTT and one SRT alternate for the same
source type, normalized language and track name. It accepts only the existing
strict native timing validator; it never invents, clips or repairs JSON3 timing.
429 and other non-candidate failures propagate instead of downgrading to plain
success. The accepted first plain raw body is kept even when an alternate wins.
`subtitle-format-v2-native-timing` creates a fresh request/cache identity; old
files, artifacts, jobs and provider records remain.

Verified native raw/canonical cache recovery now reestablishes exact timing and
Evidence after a persistence interruption. This uses existing source provenance,
managed-path/hash checks, cue validation and Evidence binding. Unknown dispatch
records do not grant repair authority.

For already-completed plain Content, an explicit normal one-time source check
creates a deterministic new `caption-repair-<sha256(run_id:video_id)>` child.
The current video stays TRANSCRIPT_READY; the old successful job stays unchanged.
The dedicated transaction validates current canonical pointer, original successful
subtitle history, current enabled VIDEO_URL/DISCOVER_ONLY source and linked video,
MANUAL_CHECK_NOW command, active owned job/lease, no competing unfinished Content
job, exact provider reservation/request policy, native file hashes and exact
normalized text/cues. It atomically writes the new artifacts, provider completion,
timed authority, original Evidence and child success. Existing complete_stage and
complete_job transition rules are preserved. Extractive Summary then uses the
ordinary source-bound service; restart recovers that remaining work idempotently.

Failed repair retry derives from the immutable original successful canonical job;
it does not enqueue an unrelated generic Content rerun. A restarted Source Run
defers while either the job or provider lease is still alive and resumes the same
child after expiry. Public repeated checks after success neither refetch nor create
another repair child. Backup continues to block unfinished work through its normal
protected gate; readiness opens only after this work genuinely finishes.

The API and English/Chinese Content UI explain missing original timing, offer the
normal Retry when the source permits it, preserve captured text/history, and poll
accepted work to organized completion. The message does not claim work is running.

No schema/migration, dependency/lockfile, credential, cloud, GPU, inference, transport
security, ASR qualification/profile, formal owner data/config/Vault or main changes.

## Measured acceptance evidence

| Check | Result | Evidence |
|---|---|---|
| Fresh bounded native-format fallback, track isolation, 429 fail closed, raw preservation | PASS | subtitle provider and policy tests |
| Explicit repair, original job/body retained, exact native timing/Evidence/Summary | PASS | runtime integration tests |
| Owner/expired lease/foreign run/current pointer/foreign artifact/modified timing/hash/unknown dispatch rejection | PASS | eight negative authority tests |
| Rollback after artifacts and after authority | PASS | no indexed repair artifacts, timing, Evidence, Summary or successful provider completion; original success retained |
| Two concurrent completions | PASS | exactly one commits; one rejects; two artifacts and one timed authority |
| Interrupted repair restart with job-live or provider-only-live lease | PASS | no fetch while live; same command/child resumes after expiry, attempt_count=2, no additional body read |
| Completed repair restart and repeated explicit check | PASS | timing identical, no new body fetch or child; readiness true |
| Captured real native VTT offline normalization | PASS, not live import | 415,676 bytes, SHA256 `1ce80bdb4602f3ad248ae11ae181435ccec6150159d5da22202b3ef3a36f3e88`, 2,406 strict native cues, 89,221 text characters; source `/tmp/readiness-sasha-0eMzc-WnBfQ.en.vtt` |
| Real GUI import/repair, restart and Backup/Restore | PENDING root acceptance | no claim from synthetic/offline tests |

Commands run with the existing `.venv` and existing frontend dependencies:

- `PYTHONPATH=src .venv/bin/python -m pytest -q tests/integration/test_runtime_composition.py tests/integration/test_subtitle_provider.py tests/integration/test_verified_timed_transcript.py tests/unit/test_local_api.py tests/unit/test_subtitle_policy.py tests/integration/test_state_store.py tests/integration/test_phase11r_source_run_quiescence.py tests/integration/test_task023a_source_run_persistence.py tests/unit/test_backup_restore.py`: **362 passed**, one existing duplicate ZIP member fixture warning, 91.53 seconds.
- Earlier focused runtime/provider/API suite: **187 passed**; added repair-specific suite: **13 passed**, 11 deselected by `-k caption_repair`.
- `npm test`: **343 passed, 22 files**, no skipped tests in the full run.
- `npm run typecheck` and `npm run build`: PASS.
- Ruff on the four changed source and three changed backend test files: PASS.
- Strict mypy on state.py/transcripts.py/runtime_composition.py/local_api.py: PASS, four source files.
- `git diff --check`: PASS.

Local raw command logs and captured-source metrics remain in ignored
`.var/readiness-captions/`: `backend.txt`, `frontend-all.txt`,
`frontend-final.txt`, `typecheck-final.txt`, `build-final.txt`, `ruff.txt`,
`mypy.txt`, `native-vtt-offline.json`. Frontend logs retain existing React act
warnings; no assertions or test scripts were suppressed or weakened.

## Reuse and diff review

DIRECT reuse: project SubtitleAcquisitionService, YtDlpSubtitleAdapter, native
normalizers, ProviderCall ledger, immutable job history, Source Run, managed artifact
hash/path checks, TimedTranscript/Evidence binding, ExtractiveSummaryService and
Backup protected gate. Python stdlib only; no external implementation copied,
new license or dependency introduced. Generic pipeline transition weakening was
REJECTED: the approved repair boundary is separate.

Changed product scope: transcripts.py, state.py, runtime_composition.py,
local_api.py, three small frontend files and their focused tests. Task card and
this handoff record the authorization and evidence. Ignored node_modules is an
existing local symlink and was not staged. No migration, generated build file,
test hiding or unrelated refactor is in the commit.

## Remaining risks / review requirements

- This is deterministic and captured-source implementation acceptance only.
  Independent review, actual ordinary product GUI repair and Backup/Restore,
  latest root full backend regression and final adoption remain pending.
- Sources lacking a strict native alternate still need attention; different
  language/source-type selection cannot silently replace the original provenance.
- The regular provider and job leases may defer interrupted repair for their
  remaining five-minute lifetime, deliberately preserving ownership safety.
- Summary is a separate recoverable ordinary projection after the atomic timing
  transaction; a crash between them does not roll back or fabricate authority.
- Recompute the actual ASR qualification tuple after root integration: shared
  timed-transcript/Evidence helper bodies changed. A previous receipt must not be
  assumed current if it binds those bodies. No receipt was altered here.
- Reviewer verdict, root acceptance and integration: PENDING.
