# TASK-025 — V1 Weekly Intelligence Foundation

- Status: `PLANNED`; Reuse: `ADAPT` existing report persistence only as a separate authority; preserve Weekly V2 `UNAVAILABLE`.
- START_ANCHOR: approved TASK-024 SHA. Dependencies: 018–024. Parallel-safe-with: none. Merge prerequisite: m011 dual-authority review APPROVE.

## Contract metadata

TASK_ID: 025. TITLE: V1 Weekly Intelligence Foundation. FILES / MODULE OWNERSHIP: m011, Brief repository/service/projection, local API tests. DOMAIN OBJECTS: Brief, BriefItem, DependencyEdge. DB IMPACT: m011. API IMPACT: controlled Weekly V1 projection. UI IMPACT: API only. TRUST IMPACT: trusted revision/Topic inputs only. COST IMPACT: no automatic new model call. MIGRATION IMPACT: v010→v011. ACCEPTANCE CRITERIA: below. STOP CONDITIONS and EXPECTED HANDOFF below. DO_NOT_TOUCH_FROZEN_CORE: frozen authority set.

## Purpose and scope

Add immutable V1 Weekly Brief snapshot/items that reference only trusted Intelligence revisions and Topics, deduplicate them, and record supersession markers after correction/deletion. Provide controlled read projection; distinguish generic existing reports, V1 Weekly projection, and unavailable Weekly V2.

## Ownership / impact

- Modules: m011, brief repository/service/projection, local API DTOs/tests.
- Domain: Brief, BriefItem, DependencyEdge. DB: m011. UI: API only. Trust: no raw video/blob input. Cost: no automatic new model call.

## Out of scope / frozen core

No Daily, Ask, report rewrite, arbitrary raw-video summary, V2 Weekly relabel/recompute, scheduler behavior modification, Deep Analysis, or provider changes.

## TDD and adversarial acceptance

Test exact revision/evidence links, dedupe, immutable snapshot, empty week, marker-on-supersession/deletion, generic-report separation and Weekly V2 unavailable state. Attack copied text with no dependency link, a changed current revision rewriting history, and raw video use. Run migration/service/API tests plus full pytest/mypy/Ruff/frontend contract build/diff check.

## Stop / handoff

Stop if existing Weekly authority must change. Handoff demonstrates authority labels and immutable history.
