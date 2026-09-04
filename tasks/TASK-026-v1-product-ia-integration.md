# TASK-026 — V1 Product IA Integration

- Status: `PLANNED`; Reuse: `ADAPT` existing FCC-inspired React shell/API client; relocate/reframe, do not delete working capabilities.
- START_ANCHOR: approved TASK-025 SHA. Dependencies: 018–025. Parallel-safe-with: none. Merge prerequisite: browser/trust review APPROVE.

## Contract metadata

TASK_ID: 026. TITLE: V1 Product IA Integration. FILES / MODULE OWNERSHIP: frontend workspace/client/tests/E2E and local API projections. DOMAIN OBJECTS: consumes all closed projections. DB IMPACT: none. API IMPACT: projection endpoints only. UI IMPACT: all frozen V1 IA surfaces. TRUST IMPACT: render only trusted DTOs. COST IMPACT: ledger/model/UNKNOWN display only. MIGRATION IMPACT: none. ACCEPTANCE CRITERIA: below. STOP CONDITIONS and EXPECTED HANDOFF below. DO_NOT_TOUCH_FROZEN_CORE: frozen authority set.

## Purpose and scope

Migrate the frozen IA to Dashboard, Intelligence, Topics, Sources, Investigations (truthful V2-reserved state), and Settings. Integrate trusted Intelligence feed/detail/evidence drill-down, Topic list/detail/pin, preference center, source policy editor, Needs Attention, cost/model state, Save Intelligence, raw video/transcript context, and existing weekly/automation/activity capabilities relocated or reframed.

## Ownership / impact

- Modules: frontend workspace/client/tests/E2E, local API projection endpoints only, accessibility styles.
- Domain: consumes all prior projections; no DB migration. Trust: cards come only from 019 contract. Cost: display ledger model/UNKNOWN state only.

## Out of scope / frozen core

No browser DB/provider access, product-domain write bypass, backend policy reinterpretation, active Investigation, Early Signal, Daily, Ask, Deep Analysis activation, Note/Weekly V2 authority change, or deletion of old capability.

## TDD and adversarial acceptance

Add focused UI/E2E tests for navigation, trusted card/detail evidence, topic trace, feedback/pin, policy validation error, raw context, Needs Attention, budget/model/AMBIGUOUS truthfulness and reserved Investigation. Attack raw/untrusted projection, missing evidence, unavailable model, old weekly confusion, and responsive keyboard navigation. Run frontend test/typecheck/build, API regression, full pytest/mypy/Ruff/uv build, browser console/network loopback check, diff check.

## Stop / handoff

Stop if an endpoint cannot honor the frozen authority. Handoff lists retained/reframed old screens and screenshots/test evidence.
