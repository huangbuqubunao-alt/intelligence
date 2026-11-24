# READINESS-03-SOURCE-CONTEXT

- Role: Implementer; assigned by root Orchestrator, not self-selected.
- Base: `b861de3d96ad14f72ecad2a824f5f7dac07e42e2`.
- Worktree: `/Users/developer/Documents/yia-worktrees/readiness-source-context`.
- Branch: `codex/task-readiness-source-context`.
- Reviewer: independent `intel_bounded_review`, after caption review.
- Approval: user-approved isolated model remediation in root worktree
  `docs/validation/end-to-end-user-readiness/MODEL_REMEDIATION_PROPOSAL.md`.

## Scope and completion criteria

Fix missing source attribution in verified Intelligence inputs when a source
has no display name but its linked video has a persisted channel name. Existing
display names take precedence; absent metadata stays absent. Use the same
effective name in the verified input and semantic hash. No historical rows are
rewritten; changed context must fail closed for an older sealed reservation.

Allowed: `_compose_verified_input` in `src/youtube_intel/distillation.py`, a
small isolated integration test file, this task and its handoff. No prompt,
parser, qualification, schema, dependencies, Cloud consent, budget, production
configuration or formal data changes. No inference or network calls.

DIRECT reuse: existing repository source/video reads, exact Evidence resolver,
semantic hashing, reservation identity and Python/pytest. REJECT: invented
speaker names, caller-provided source prose, historical mutations and manual
qualification. No new third-party code or licensing obligation.

TDD: reproduce the missing-name failure, apply the smallest repair, then run
related distillation/wire/Cloud/no-new/cancellation tests, Ruff, strict mypy
and diff check. Produce a scoped commit and handoff, then stop for review.
Caption review is read-only in another tree; integration and model experiments
remain with root. This repair does not establish model qualification.
