# TASK-023B — Distillation Reservation / Continue Seam Amendment

- Status: `PLANNED`; Reuse: `ADAPT` the existing TASK-022 application service and m010 checkpoint only.
- START_ANCHOR: approved TASK-023A SHA. Dependencies: 018–023A. Parallel-safe-with: none. Merge prerequisite: reservation/dispatch-safety review APPROVE.

## Contract metadata

TASK_ID: 023B. TITLE: Distillation Reservation / Continue Seam Amendment. FILES / MODULE OWNERSHIP: TASK-022 distillation service, repository application methods, focused tests and handoff. DOMAIN OBJECTS: m010 DistillationExecution checkpoint/ResourceUsage only. DB IMPACT: none. API IMPACT: application-service seam only. TRUST IMPACT: unchanged existing admission. COST IMPACT: retains the m010 ledger as sole authority. MIGRATION IMPACT: none; database remains v012. TASK-024 and TASK-025 implementation are out of scope.

## Purpose and scope

Provide the missing legal sequence for the later orchestrator:

```text
reserve canonical TASK-022 execution
-> bind the exact ID to the immutable m012 Source Run child
-> continue that exact execution once through TASK-022 admission
```

Reservation creates no transport call, ResourceUsage ledger row, Intelligence,
Evidence, Topic effect, success result, usage, or cost. It mints its canonical
identity inside TASK-022; callers do not choose an arbitrary execution ID.

The no-dispatch proof is the finite persisted compound m010 state
`PENDING / RESERVED_NOT_DISPATCHED / invocation_count=0`. Before a transport
call, TASK-022 atomically claims it as
`PENDING / DISPATCH_CLAIMED / invocation_count=1`. A claimed row is treated as
possibly externally executed on any later observation and is finalized as
`AMBIGUOUS`, never redispatched. Legacy/unrecognised `PENDING` rows are not a
continuation authority.

The reserved command is rebuilt from the immutable m010 identity and canonical
persisted available transcript Evidence. Its identity includes that Evidence
set; a changed set fails closed rather than substituting inputs after restart.
Normal TASK-021 eligibility, TASK-022 budget/model gates, structured-output
validation, Evidence admission, Intelligence creation and ledger rules still
run on continuation.

## Frozen boundaries

- No migration; do not edit m006–m012, including m010 terminal triggers and
  m012 child execution-ID immutability.
- m010 remains the sole execution/checkpoint/ResourceUsage authority; no Source
  Run ledger or second Intelligence path is created.
- `AMBIGUOUS` remains terminal/non-redispatchable. A reservation is distinct
  from unknown provider outcome.
- No real provider, provider qualification, credentials, Deep Analysis, Topic
  update, Source Run worker, queue, scheduler, Check Now endpoint, Weekly or UI.

## Acceptance / adversarial gate

Prove canonical idempotent zero-call reservation; immutable m012 child binding;
restart-safe continuation; success recovery without duplicate transport,
Intelligence, Evidence support or ledger; budget-before-dispatch; invalid output
without semantic retry; model identity ownership; and AMBIGUOUS no-redispatch,
including a restart after `DISPATCH_CLAIMED`. Verify v012/m013 absence and that
m010/m012 SQL is byte-for-byte unchanged. Stop for any need to change schema,
m010 terminal semantics, m012 binding, provider dispatch v4, or TASK-024
orchestration behavior.

## Handoff

TASK-024 may start only from an approved TASK-023B anchor and must use this
seam in the stated order. It must not pre-create an m010 execution and then call
the legacy `distill()` entry point.
