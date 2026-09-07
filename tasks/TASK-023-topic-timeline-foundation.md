# TASK-023 — Topic Aggregation and Timeline Foundation

- Status: `PLANNED`; Reuse: `ADAPT` m006 revisions/dependencies; no graph library.
- START_ANCHOR: approved TASK-022 SHA. Dependencies: 018–022 plus 018A. Parallel-safe-with: none. Merge prerequisite: m011 topic provenance review APPROVE.

## Contract metadata

TASK_ID: 023. TITLE: Topic Aggregation and Timeline Foundation. FILES / MODULE OWNERSHIP: m011, Topic repository/service, local API tests. DOMAIN OBJECTS: Topic, association, timeline event, relation. DB IMPACT: m011. API IMPACT: Topic projections/mutations. UI IMPACT: API only. TRUST IMPACT: every state/event cites revision/evidence. COST IMPACT: none. MIGRATION IMPACT: v010→v011. ACCEPTANCE CRITERIA: below. STOP CONDITIONS and EXPECTED HANDOFF below. DO_NOT_TOUCH_FROZEN_CORE: frozen authority set.

## Purpose and scope

Add basic V1 Topic identity/current state, Intelligence-revision membership/deduplication, pin, source-traceable timeline events, and lightweight related-topic relations. Clustering consumes only trusted revisions; human create/rename/merge/split operations preserve underlying Intelligence/Evidence identity.

## Ownership / impact

- Modules: m011, topic repository/service, controlled local API read/write DTOs/tests.
- Domain: Topic, TopicAssociation, TopicTimelineEvent, TopicRelation. DB: m011. UI: API only. Trust: every state/event references supporting IDs. Cost: no model execution required.

## Out of scope / frozen core

No advanced knowledge graph, cross-source confidence inference, Early Signal, Investigation, external expansion, Weekly, frontend implementation, or score/provider changes.

## TDD and adversarial acceptance

Test stable association, idempotent dedupe, pin, timeline provenance, relation normalization, current-state pointer, merge/split preservation and invalidated revision behavior. Attack copied conclusion text, a timeline event without evidence/revision, and merging that mutates source identity. Run migration/repository/service/API tests, full pytest checkpoint, mypy/Ruff, diff check.

## Stop / handoff

Stop on requirement for active Investigation or inferred independent validation. Handoff maps every Topic field to source/revision evidence.
