# TASK-024 — V1 Processing Orchestration

- Status: `PLANNED`; Reuse: `ADAPT` ProductOrchestrationService, automation runs, jobs/attempts, runtime boundary and dispatch protections.
- START_ANCHOR: approved TASK-023B SHA. Dependencies: 018–023B. Parallel-safe-with: none. Merge prerequisite: scheduler/duplicate-effect review APPROVE.

## Contract metadata

TASK_ID: 024. TITLE: V1 Processing Orchestration. FILES / MODULE OWNERSHIP: orchestration service/runtime adapter, scheduler delegation, local API/tests. DOMAIN OBJECTS: durable Source Run plus child execution detail. DB IMPACT: none; consumes TASK-023A m012. API IMPACT: triggers/status. UI IMPACT: no page work. TRUST IMPACT: invokes only closed contracts. COST IMPACT: applies priority/budget/ledger. MIGRATION IMPACT: none. ACCEPTANCE CRITERIA: below. STOP CONDITIONS and EXPECTED HANDOFF below. DO_NOT_TOUCH_FROZEN_CORE: frozen authority set.

## Purpose and scope

Unify Manual Check Now, scheduled Source Run, and manual analyze-skipped-video in one application-service pipeline: trigger, discover, deterministic filter, process, distill, persist, Topic update, Activity/Needs Attention. Implement P0–P3 semantics, queue/defer, budget/model wait, and partial completion/safe resume by consuming TASK-023A's durable Source Run contract and TASK-023B's exact `reserve -> bind immutable child ID -> continue` TASK-022 seam. Do not pre-create an execution and call legacy `distill()`; use the approved continuation seam.

## Ownership / impact

- Modules: orchestration service/runtime adapter, scheduler tick delegation, local API trigger projections, repository readers/tests; no migration.
- Domain: Task/Execution operational records referencing content. API: trigger/status only. UI: no page work. Trust/cost: consumes prior contracts.

## Out of scope / frozen core

No direct scheduler DB/provider/YouTube operation, browser shortcut, new provider, provider dispatch change, credentials, Deep Analysis, Weekly generation, or V2 automation.

## TDD and adversarial acceptance

Test common pipeline identity for three triggers, priority/budget decisions, at-most-once claims, cap, safe checkpoint resume, partial state, source disabled, model wait, and Needs Attention. Attack double scheduler/manual trigger, failure after provider dispatch, AMBIGUOUS, retry confusion, and failed Topic update: no duplicate provider effect and no auto-redispatch. Run scheduler/application/API tests, full regression checkpoint, diff check, mypy/Ruff.

## Stop / handoff

Stop for a required bypass of existing runtime/dispatch. Handoff shows call path and trigger equivalence evidence.
