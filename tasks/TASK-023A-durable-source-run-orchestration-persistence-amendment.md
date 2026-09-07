# TASK-023A — Durable Source Run Orchestration Persistence Amendment

- Status: `APPROVE`; Product Owner correction task following approved TASK-023.
- START_ANCHOR: `02334a9a1891b363a2badfa5464f93b1fe42d841`. Dependencies: 018–023 plus 018A. Parallel-safe-with: none. Merge prerequisite: m012 durable-orchestration persistence review APPROVE.

## Contract metadata

TASK_ID: 023A. TITLE: Durable Source Run Orchestration Persistence Amendment. FILES / MODULE OWNERSHIP: m012, typed Source Run domain/repository primitives, migration/repository tests, task graph and handoff evidence. DOMAIN OBJECTS: SourceRun, SourceRunCheckpoint, SourceRunVideoExecution. DB IMPACT: m012. API IMPACT: none. UI IMPACT: none. TRUST IMPACT: none; it preserves closed upstream authorities. COST IMPACT: none. MIGRATION IMPACT: v011→v012. ACCEPTANCE CRITERIA: below. STOP CONDITIONS and EXPECTED HANDOFF below. DO_NOT_TOUCH_FROZEN_CORE: frozen authority set.

## Product Owner amendment and purpose

TASK-024's durable orchestration contract remains required. It cannot be
implemented truthfully with process memory, m005 `automation_runs`, m010
`distillation_execution_checkpoints`, or legacy jobs: those records respectively
own scheduled-occurrence history, protected per-video provider execution, and
an incompatible legacy identity/state model. TASK-023A exclusively owns the
minimal new persistence contract needed for TASK-024 to later represent a
top-level Source Run durably.

Migration m012 changes `user_version` from 11 to 12. TASK-024 remains
migration-free and consumes this contract. TASK-025's Weekly migration moves to
m013; this task creates neither m013 nor Weekly/Brief schema. Existing m006–m011
are immutable.

## Owned persistence contract

Persist a stable opaque Source Run identity bound to a Source, finite trigger
(`MANUAL_CHECK_NOW`, `SCHEDULED_SOURCE_RUN`, `MANUAL_ANALYZE_VIDEO`), finite
priority (`P0`–`P3`), bounded trigger reference/idempotency identity, creation
time, current finite execution state, append-only finite checkpoint progress,
finite Needs Attention reason, and legal schedule/manual-analyze relations.
Persist child/video execution association separately from m010's distillation
checkpoint identity. Provide typed repository operations for create/get,
idempotency admission, valid finite transitions, checkpoint progress, attention,
child association, and durable queued/resumable reads.

Source Run state is operational state, not Video disposition, Intelligence
lifecycle, Topic truth, or a provider-dispatch permission. Source Run checkpoint
progress cannot assert a protected provider success without a legal TASK-022
child checkpoint. AMBIGUOUS remains terminal/non-redispatchable in its child
authority and is surfaced as Needs Attention rather than converted to retry.

## Out of scope / frozen core

Do not implement Check Now, scheduled execution, queue workers, discovery,
filtering, transcript preparation, distillation, Intelligence admission, Topic
updates, retries/resume workers, provider dispatch, local API/UI paths, or
Weekly. Do not change m005, m010 terminal/immutable protections, dispatch v4,
AMBIGUOUS, trust readers, Source policy, budget/ledger, Topics, score authority,
provider qualification, credentials, or Deep Analysis. No real provider/model
call is permitted.

## TDD and adversarial acceptance

Write failing tests first for fresh and v011→v012 migration, preservation of
existing data, absence of m013/Weekly tables and synthetic runs, finite
identity/trigger/priority/state/checkpoint/attention values, source binding,
idempotent create, schedule/manual-analyze relations, invalid transitions,
durable resume query, partial child coexistence, and m010 AMBIGUOUS safety.
Attack cross-Source idempotency reuse, arbitrary priorities/triggers/states,
checkpoint advancement without protected-child proof, terminal-state regression,
attention-as-retry, secret persistence, historical-job reinterpretation, m005
mutation, and Task-024/025 leakage. Run focused migration/repository tests and
the prescribed upstream regressions, full pytest, mypy, Ruff, offline build,
diff check, and required security scan.

## Stop / handoff

Stop if m012 cannot represent the contract without changing m010/AMBIGUOUS,
requiring m013/Weekly, or implementing TASK-024 behavior. Handoff must show the
task graph amendment, m012 ownership, exact schema/test evidence, no real
provider calls, and whether TASK-024 can start migration-free from the approved
TASK-023A final head.
