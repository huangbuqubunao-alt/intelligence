# READINESS-RETIRED-SUBTITLES

Assigned Implementer `/root/source_context`, base `fbe0e2b7323384ebb60408a436c4a6b732c61a72`,
branch `codex/task-readiness-retired-subtitles`, independent worktree
`/Users/developer/Documents/yia-worktrees/readiness-retired-subtitles`.
Independent Reviewer `intel_bounded_review` starts after commit.

User specifically approved root
`docs/validation/end-to-end-user-readiness/RETIRED_SUBTITLE_FAILURE_PROPOSAL.md`
on 2026-10-13: “批准该精确隔离整改与验收范围”. This authorizes isolated
implementation/validation, not main adoption or formal data changes.

Allowed: dedicated repository transition in state.py, normal idle maintenance
in runtime_composition.py, focused tests/task/handoff. Backup safety evaluation
is reused unchanged. No Schema/dependency/credentials/formal/GPU/network change.

Only exact `subtitle.fetch/yt-dlp/model=NULL/subtitle-selection-v1/subtitle-format-v1`
known RATE_LIMITED FAILED_RETRYABLE rows with no response, reservation or lease,
no unknown dispatch, and globally settled work may become FAILED_FINAL. Keep
original history/error text/request identity and add fixed retirement reason.
Protected gate and SQLite immediate transaction/CAS prevent startup races.
Any other provider, current/unknown policy, active job/run/check/checkpoint or
Restore blocks maintenance. Reuse existing cancellation authority for WAITING_MODEL.

DIRECT existing SQLite provider ledger, Backup protected gate/quiescence, worker,
pytest and standard library. REJECT blanket failure cleanup, Backup bypass,
unknown-dispatch reinterpretation, invented successes, deleted history.

TDD positive known429/new-success, idempotence, restart/BackupRestore, retained
all-table history, active/unknown/current/cloud controls, same-request and work
startup races, normal idle worker maintenance/no self-wakeup. Relevant suites,
Ruff, strict mypy and diff check before commit. Frontend page recovery may run
in its disjoint tree; caption persistence work waits until this writer stops.
