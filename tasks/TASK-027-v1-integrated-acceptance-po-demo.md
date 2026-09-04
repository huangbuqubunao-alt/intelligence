# TASK-027 — V1 Integrated Acceptance and PO Demo

- Status: `PLANNED`; Reuse: `ADAPT` existing PO demo/E2E fixture harness. START_ANCHOR: approved TASK-026 SHA.
- Dependencies: 018–026. Parallel-safe-with: none. Merge prerequisite: PO APPROVE; this task adds no product capability.

## Contract metadata

TASK_ID: 027. TITLE: V1 Integrated Acceptance and PO Demo. FILES / MODULE OWNERSHIP: synthetic fixtures, harness/E2E, demo evidence/handoff. DOMAIN OBJECTS: verification-only across all V1 objects. DB IMPACT: no product migration; test v005→v011. API IMPACT: verification only. UI IMPACT: verification only. TRUST IMPACT: proves boundaries. COST IMPACT: proves ledger/pause truthfulness. MIGRATION IMPACT: packaged upgrade verification. ACCEPTANCE CRITERIA: below. STOP CONDITIONS and EXPECTED HANDOFF below. DO_NOT_TOUCH_FROZEN_CORE: frozen authority set.

## Purpose and scope

Create provider-free realistic synthetic fixtures and execute the complete V1 acceptance journey. Repair only P0/P1 defects discovered in owned prior work through the original implementer/review flow; do not add features or reinterpret product authority.

## Ownership / impact

- Modules: synthetic fixtures, test harness/E2E, PO demo docs/handoff; no migration other than testing v005-to-v011.
- Domain/API/UI: verification only. Trust/cost: verifies all prior contracts.

## Out of scope / frozen core

No real provider/YouTube calls absent PO approval, no V2 activation, no feature work, no credentials/dispatch/scoring/Deep Analysis changes, and no release action.

## TDD and adversarial acceptance

Fixture covers source check, skip reason, manual override, admitted Intelligence/evidence, Topic/timeline/pin, feedback affecting later processing without explicit-rule mutation, V1 Weekly, Needs Attention, model wait, budget exhaust, AMBIGUOUS and Deep Analysis BLOCKED. Run full unit/domain/repository/migration/service/API/scheduler/frontend/E2E/packaged runtime suite, `uv build --offline`, diff check, scanner expected EXIT 1 / 11 accepted / 0 new. PO independently accepts product journey.

## Stop / handoff

Stop only at PO APPROVE or genuine frozen-contract blocker. Handoff reports fixture data, every command/result, scanner truthfully, remaining risks, and no production side effects.
