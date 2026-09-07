# TASK-022 — Personalized Video Distillation and Resource Ledger

- Status: `PLANNED`; Reuse: `ADAPT` existing runtime job/artifact/provider-call identity; do not copy authority.
- START_ANCHOR: approved TASK-021 SHA. Dependencies: 018–021 plus 018A. Parallel-safe-with: none. Merge prerequisite: m010 cost/trust review APPROVE.

## Contract metadata

TASK_ID: 022. TITLE: Personalized Video Distillation and Resource Ledger. FILES / MODULE OWNERSHIP: m010, distillation service/adapters, repository and local API tests. DOMAIN OBJECTS: Intelligence/Evidence, execution checkpoint/ResourceUsage. DB IMPACT: m010. API IMPACT: controlled manual admission/status. UI IMPACT: API only. TRUST IMPACT: evidence-bound admission. COST IMPACT: selected/actual model plus reliable usage/cost or UNKNOWN. MIGRATION IMPACT: v009→v010. ACCEPTANCE CRITERIA: below. STOP CONDITIONS and EXPECTED HANDOFF below. DO_NOT_TOUCH_FROZEN_CORE: frozen authority set.

## Purpose and scope

Implement the bounded application-service path from existing trusted transcript/input plus current preference/policy to an Evidence-bound personalized Intelligence candidate/Card and admitted revision. Add V1 execution checkpoint and ResourceUsage/Ledger (reason, target IDs/revisions, selected/actual provider/model, calls, duration, reliable usage/cost or UNKNOWN). It must pause on unavailable model/budget and does not depend on Deep Analysis.

## Ownership / impact

- Modules: m010, distillation service/adapters, repository records, local API manual admission endpoint/tests.
- Domain: Intelligence/Evidence; execution ledger/checkpoint. DB: m009. UI: API DTO only. Cost: first executable V1 path owns ledger.

## Out of scope / frozen core

No scheduler unification, Topic/Weekly/UI, provider qualification, scoring finalizer modification, automatic external validation, Deep Analysis, retry-after-AMBIGUOUS, credentials, or V2 capabilities.

## TDD and adversarial acceptance

Start with fake deterministic model fixtures. Test evidence binding, claim type, relevance/information gain, duplication candidate, actual identity, UNKNOWN usage, budget/model waiting, idempotent completed-step reuse, and admitted-versus-rejected output. Attack hallucinated/unsupported claim, absent transcript, forged usage, duplicate request, budget exhaustion and AMBIGUOUS: no admitted Intelligence or redispatch. Verify no real calls; run migration/service/API tests, diff check, Ruff/mypy.

## Stop / handoff

Stop if execution needs an unqualified provider or any frozen runtime mutation. Handoff includes outbound-data disclosure contract and ledger evidence.
