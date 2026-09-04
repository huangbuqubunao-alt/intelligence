# TASK-020 — Preference and Feedback Domain

- Status: `PLANNED`; Reuse: `ADAPT` existing local API service mutation pattern.
- START_ANCHOR: approved TASK-019 SHA. Dependencies: 018, 019. Parallel-safe-with: none. Merge prerequisite: m007 and intent-boundary review APPROVE.

## Contract metadata

TASK_ID: 020. TITLE: Preference and Feedback Domain. FILES / MODULE OWNERSHIP: m007, preference domain/repository/service, local API tests. DOMAIN OBJECTS: Feedback, Preference. DB IMPACT: m007. API IMPACT: Settings/Preference scoped reads/writes. UI IMPACT: API only. TRUST IMPACT: correction cannot alter Evidence. COST IMPACT: none. MIGRATION IMPACT: v006→v007. ACCEPTANCE CRITERIA: TDD/adversarial cases below. STOP CONDITIONS and EXPECTED HANDOFF below. DO_NOT_TOUCH_FROZEN_CORE: frozen authority set.

## Purpose and scope

Add raw feedback event history and separately derived/current long-term, recent, and temporary preference state with expiry, user origin/confirmation, and explicit-config versus learned-preference boundary. Expose narrowly scoped Settings/Preference read/write projections; factual correction is a distinct recorded workflow boundary, not a preference mutation.

## Ownership / impact

- Modules: migration 007, domain/repository, preference application service, local API DTOs/tests.
- Domain: Feedback, Preference. DB: m007 only. UI: API contract only. Trust: correction never edits Evidence. Cost: no execution.

## Out of scope / frozen core

No source-policy filtering, model/provider settings replacement, Intelligence revision creation, Topics, scheduler, frontend pages, automatic learning activation, or V2. Preserve credentials and frozen runtime contracts.

## TDD and adversarial acceptance

Test event append/audit, derived projection determinism, temporary expiry, delete/edit semantics, explicit versus learned isolation, target validation, and correction type separation. Attack More/Less/Important and natural-language input: none may overwrite explicit interest/ignore/enabled/schedule/model; correction must create no altered source material. Test v006 upgrade, migration failure/restart, focused API/repository tests, diff check, Ruff/mypy.

## Stop / handoff

Stop for a policy requiring automatic permanent preference promotion. Handoff supplies migration, API contract, expiry clock strategy, adversarial evidence and SHA.
