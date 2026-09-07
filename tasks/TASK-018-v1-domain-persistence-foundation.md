# TASK-018 — V1 Domain Persistence Foundation

- Status: `IN_REVIEW`; Reuse decision: `ADAPT` existing SQLite migration/repository transaction pattern; no third-party dependency.
- START_ANCHOR: approved V1 integration commit at frozen `404c9e5...`.
- Dependencies: none. Parallel-safe-with: read-only review only. Merge prerequisite: migration 006 review APPROVE.

## Contract metadata

TASK_ID: 018. TITLE: V1 Domain Persistence Foundation. FILES / MODULE OWNERSHIP: migration 006, state repository, domain records and tests. DOMAIN OBJECTS: Evidence, Intelligence, IntelligenceRevision, StateHistory, DependencyEdge. DB IMPACT: m006. API IMPACT: none. UI IMPACT: none. TRUST IMPACT: persistence boundary only; no admission. COST IMPACT: none. MIGRATION IMPACT: v005→v006. ACCEPTANCE CRITERIA: all TDD/adversarial cases below pass. STOP CONDITIONS and EXPECTED HANDOFF are below. DO_NOT_TOUCH_FROZEN_CORE: all TASK-016, dispatch, credentials, Note/Weekly and Deep Analysis authorities.

## Purpose and scope

Add the minimal V1 persistence/repository contracts for immutable Evidence, Intelligence identity/current pointer, IntelligenceRevision/state history, exact revision-evidence links, and DependencyEdge. Evidence retains Video/artifact provenance and availability/lineage; no distillation, Topic, Preference, API, or UI behavior is included.

## Ownership / impact

- Files/modules: `src/youtube_intel/migrations/006_*`, `state.py`, domain records, focused repository/migration tests.
- Domain: Evidence, Intelligence, IntelligenceRevision, StateHistory, DependencyEdge.
- DB: new forward-only migration 006. API/UI/cost: none. Trust: creates IDs/constraints, not admission or display authority.

## Out of scope / frozen core

No provider calls, scoring changes, `AuthoritativeScoringReader`, dispatch/`AMBIGUOUS`, credentials, Note/Weekly V2, TASK-016G, Deep Analysis, source policy, V2 tables, deletion UI, or broad migration refactor. **DO_NOT_TOUCH_FROZEN_CORE** applies.

## TDD and adversarial acceptance

Write failing tests first for fresh/v005 upgrade, constraints/FKs/indexes, immutable revision append, valid current pointer, exact many-to-many evidence links, dependency direction, rollback/history mismatch, and v005 Source/Automation preservation. Prove pointer/evidence delete restrictions and that an unavailable/deleted evidence input cannot leave a supported current revision. `git diff --check`, focused pytest, Ruff/mypy scope, migration initialization tests pass.

## Stop / handoff

Stop for conflict with existing authority or any need to alter prior migrations. Handoff lists schema objects, upgrade evidence, reuse, commands, risks, and approved commit SHA.
