# TASK-018A Implementer Packet

From `7d89f5965a0c87d599e48ba72b887b3322ef4c17`, implement only
`tasks/TASK-018A-persisted-claim-classification-amendment.md`. First amend the
task graph: TASK-018A exclusively owns m007 and all later unimplemented
migrations shift by one. Do not alter m006 or TASK-018 history. TDD m007's
finite immutable `IntelligenceRevision` claim kind, using `UNCLASSIFIED` only
for upgraded v006 rows and rejecting it for new writes. Claim kind never
confers trust or replaces lifecycle state. Preserve scoring, dispatch,
credentials, Note/Weekly authorities, TASK-016 core, and Deep Analysis
**BLOCKED**. Do not implement TASK-019 or TASK-020. Run focused and regression
checks, handoff, adversarial review, fix P0/P1, re-review; do not push, merge,
tag, release, rebase, or squash.
