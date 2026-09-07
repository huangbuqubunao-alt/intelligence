# TASK-019 — Intelligence Admission and Trusted Read Contract

- Status: `PLANNED`; Reuse: `DIRECT` existing `AuthoritativeScoringReader` and local API/application-service boundary.
- START_ANCHOR: approved TASK-018A integration SHA. Dependencies: 018, 018A. Parallel-safe-with: read-only review only. Merge prerequisite: independent trust review APPROVE.

## Contract metadata

TASK_ID: 019. TITLE: Intelligence Admission and Trusted Read Contract. FILES / MODULE OWNERSHIP: Intelligence service/projection, local API/client DTO tests, repository readers. DOMAIN OBJECTS: admitted Intelligence revisions/dependencies. DB IMPACT: none (uses m007). API IMPACT: trusted DTO/read and deletion-impact preview endpoint. UI IMPACT: contract only. TRUST IMPACT: only admitted read data is displayable. COST IMPACT: none. MIGRATION IMPACT: none. ACCEPTANCE CRITERIA: TDD/adversarial cases below. STOP CONDITIONS and EXPECTED HANDOFF below. DO_NOT_TOUCH_FROZEN_CORE: TASK-016/scoring/dispatch/credentials/Note/Weekly/Deep Analysis.

## Purpose and scope

Define admission of persisted Intelligence and its local trusted read projection: required Evidence IDs, claim classification, revision/current-state resolution, invalid/disputed treatment, dependency-impact calculation for correction/evidence deletion, and isolation of untrusted intermediate output. The deletion/correction path supplies an impact preview and marks/recomputes current projections fail-closed; immutable snapshots are only marked later by TASK-025. Add only the application-service/repository read/write contract and controlled API DTOs necessary to prove it; it does not create personalized distillation.

## Ownership / impact

- Modules: Intelligence service/projection, `local_api.py`, client DTO tests, repository readers; no migration. TASK-018A persists the prerequisite finite revision claim classification; TASK-019 rejects legacy `UNCLASSIFIED` from trusted reads.
- Domain: admitted Intelligence revisions and dependency references. DB: uses m006. UI: contract only. Cost: none.
- Trust: a UI may only receive this projection; scoring remains read through its existing authoritative reader.

## Out of scope / frozen core

No raw artifact/score display authority, provider/model execution, Topic/Preference/Source policy, Weekly, scheduler, frontend redesign, dispatch or credentials. **DO_NOT_TOUCH_FROZEN_CORE** includes TASK-016B/C finalizer/scoring lineage and all listed frozen authorities.

## TDD and adversarial acceptance

Test admitted versus incomplete/forged/untrusted candidates, exact evidence/revision labels, current-pointer resolution, invalidated/disputed responses, dependency impact preview, unsupported-current marking after evidence removal, stable API errors, and no direct repository access from browser contract. Prove raw scoring rows/artifacts cannot become an Intelligence Card and API cannot claim confidence unsupported by evidence. Focused unit/repository/API tests, `git diff --check`, Ruff/mypy scope pass.

## Stop / handoff

Stop if satisfying V1 requires changing scoring admission or Weekly V2 authority. Handoff records DTO schema, trust tests, reused reader and SHA.
