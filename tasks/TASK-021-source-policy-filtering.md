# TASK-021 — Source Intelligence Policy and Filtering

- Status: `PLANNED`; Reuse: `ADAPT` SourceSubscription/SourceVideoLink and ProductOrchestrationService configuration validation.
- START_ANCHOR: approved TASK-020 SHA. Dependencies: 018–020. Parallel-safe-with: none. Merge prerequisite: m008/API policy review APPROVE.

## Contract metadata

TASK_ID: 021. TITLE: Source Intelligence Policy and Filtering. FILES / MODULE OWNERSHIP: m008, Source repository/service, filter policy, local API tests. DOMAIN OBJECTS: Source policy revision, SourceVideo filtering/audit. DB IMPACT: m008. API IMPACT: Source/Settings policy DTOs. UI IMPACT: API only. TRUST IMPACT: filtering is not intelligence admission. COST IMPACT: deterministic filter makes no model call. MIGRATION IMPACT: v007→v008. ACCEPTANCE CRITERIA: below. STOP CONDITIONS and EXPECTED HANDOFF below. DO_NOT_TOUCH_FROZEN_CORE: frozen authority set.

## Purpose and scope

Persist V1 source/global processing policy: initial-history count, per-run max new videos, focus/ignore and Source overrides, distillation style, deterministic two-stage filter disposition/reason, and manual Analyze audit. Establish which metadata-only decisions need no LLM and a contract for ambiguous candidates; no model execution or scheduler wiring.

## Ownership / impact

- Modules: m008, Source repository/service, policy/filter domain, controlled local API/settings/source DTOs/tests.
- Domain: Source policy revision, SourceVideo filtering record/manual override. DB: m008. UI: API only. Cost: filtering itself records no model consumption.

## Out of scope / frozen core

No actual Check Now orchestration, discovery/provider/YouTube calls, distillation, retries, Topic/Weekly/UI refactor, or dispatch changes. Keep `FULL_INTELLIGENCE`/Deep Analysis blocked and actual provider qualification unchanged.

## TDD and adversarial acceptance

Test defaults for v007 rows, validation/cap, override precedence, deterministic metadata clear-relevant/clear-skip/ambiguous results, skip reasons, and manual override audit. Prove filtering cannot invoke provider/LLM; manual Analyze changes only relevance disposition, never budget/qualification/evidence/AMBIGUOUS; Check Now is not Retry. Run migration and focused service/API tests, diff check, Ruff/mypy.

## Stop / handoff

Stop if a policy asks for unsafely inferred history or provider fallback. Handoff lists default compatibility and no-LLM evidence.
