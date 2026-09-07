# TASK-018A — Persisted Claim Classification Amendment

- Status: `APPROVE`; Product Owner amendment to approved TASK-018.
- START_ANCHOR: `7d89f5965a0c87d599e48ba72b887b3322ef4c17`. Dependency: approved TASK-018. Merge prerequisite: independent persistence review APPROVE.

## Authority and scope

TASK-019 correctly blocked because m006 lacks durable, revision-specific claim
classification. Product Owner requires a finite immutable claim kind on every
`IntelligenceRevision`, orthogonal to its existing lifecycle state. TASK-018
remains closed; migration 006 and its history are immutable. TASK-018A owns
only new forward-only m007. It does not implement trusted reads, admission,
deletion impact, UI, preferences, distillation, Topics, Weekly, execution, or
any V2 capability. Deep Analysis remains **BLOCKED**.

## Contract

New revisions must persist exactly one of `FACT`, `EVIDENCE_BACKED_STATEMENT`,
`OPINION`, `PREDICTION`, `RUMOR`, or `SYSTEM_INFERENCE`. Migration of existing
v006 rows assigns only `UNCLASSIFIED`; it never infers meaning. `UNCLASSIFIED`
is a backward-compatibility sentinel, is not product-facing, and must be
rejected by normal post-m007 writes. Claim kind is immutable with the revision;
changing it requires a new revision. Classification does not establish trust or
change lifecycle semantics.

## Required evidence

TDD m006-to-m007 and fresh-v007 migrations; test every valid kind, rejection of
arbitrary kinds and new `UNCLASSIFIED`, immutable historical classification,
revision replacement, lifecycle orthogonality, no implicit trust, and package
discovery. Preserve TASK-018, Source/Automation, and scoring regressions.
Update the task graph to shift future migration ownership: 020→m008,
021→m009, 022→m010, 023→m011, and 025→m012. No Product Spec semantic change or
V2 expansion is authorized.

## Closeout

The finite classification prerequisite is now durable at m007. TASK-019 may
later consume only non-`UNCLASSIFIED` revisions from this correction's approved
anchor; it is not implemented here. Adversarial review and re-review found
`P0 = 0`, `P1 = 0`, and `P2 = 0`. TASK-018 and m006 remain unchanged; no
Product Spec semantics, V2 scope, scoring authority, provider/credential
contract, Note/Weekly authority, or Deep Analysis status changed.
