# Phase 13 — automatic background Following

Owner-authorized continuous goal; sole executor; base main/origin
`404d0a76ef022647f242e295a87b7ed18c3b0667`.

## Authority and done criteria

Read PRODUCT_CONSTITUTION, V1_PRODUCT_SPEC and V1_IMPLEMENTATION_ROADMAP in
that order. They define bounded delegation, disabled-source execution stops,
safe recovery, truthful failures and explicit cloud consent, but no formal
V1.x Phase 13. Historical M13 is seven-day dogfood, not this implementation.
The owner's current Phase 13 contract supplies the bounded scope and overrides
historical no-Phase-13/no-adoption and independent-agent workflow restrictions.

Done requires durable due checks without UI activity; no paused/overlapping
work, historical flood or model calls; bounded failures, restart, shutdown and
Backup/Restore; deterministic and real/local acceptance; all required regression,
frontend and static checks; product/reliability/cost/security self-review; final
rerun; clean candidate commits; refreshed safe ff-only main adoption and push;
feature development frozen for real-user daily usage. Phase 14 is not started.

## Bounded implementation plan

1. Reuse schema-34 next_check_at, source_checks, source_runs and existing
   provider/tracker/runtime acquisition. Add deterministic failing tests first.
2. Add a small application scheduler that admits due tracking commands through
   ProductOrchestrationService onto the existing Source Run worker. Reuse atomic
   active-run admission for manual/background races. One worker gives concurrency
   one. Persist automatic origin in the existing command identity, not a new
   parallel schedule table or cron configuration.
3. Replace idle half-second worker polling with event/deadline waits. Notify on
   follow and pause/resume as well as existing command submission. Use a bounded
   clock/sleep reconciliation timeout when future due work exists.
4. Retain the existing 15-minute normal cadence. Automatic network failures
   back off from one minute to one hour; provider/parser/local failures use
   longer capped delays; actual provider cooldown remains authoritative.
   Manual network retry remains available after five seconds. Risk/untrusted
   authority fails closed. No provider transport/security redesign.
5. Protect automatic admission/execution during existing Backup/Restore
   windows. Restore applies only after the old worker drains and stops, before
   fresh repositories/workers open. No cached source jobs survive replacement.
6. Verify the 30 required deterministic cases, regression suites, real NASA
   baseline/due check, fresh runtime/UI/manual/pause/restart/backup, and all four
   reviews. Fix findings and rerun affected checks before acceptance/adoption.

## Scope and reuse

Expected product changes: following_tracking.py, one following_scheduler.py,
runtime_composition.py, cli.py, orchestration_service.py, local_api.py,
backup_restore.py, focused tests and Phase 13 decision/validation/handoff docs.
UI changes only if truthful existing status requires them; DESIGN.md is the
existing design reference. No settings console, notifications, new provider,
schema migration, dependency, lockfile, credential or deployment change.

DIRECT: approved Python threading/events/context managers/datetime/SQLite
(stdlib/PSF), existing project-owned Source Run worker/active admission and
schema-34 tracking, frozen provider adapters and transcript-only/extractive
Summary path. ADAPT: existing lifecycle refresh into backend-owned deadline
scheduling. REJECT: scheduler framework, second daemon, launchd installation,
cron surface, new model execution. All eight named protected worktrees remain
read-only; before fingerprints are in /tmp/intelligence-phase13-evidence.

Lifecycle: automatic Following operates for the lifetime of serve-api, including
when a browser window closes. It stops when that backend stops; reopening reloads
SQLite and checks only due work. No authority document requires independent OS
service installation or operation while the backend is absent.
