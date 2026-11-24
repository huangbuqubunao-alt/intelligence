# TASK-READINESS-Q3KS-DIAGNOSTIC execution package

Read root `tasks/TASK-READINESS-Q3KS-DIAGNOSTIC.md`, repository instructions,
PRD, System Design, reuse register and the two linked validation reports.

Task: TASK-READINESS-Q3KS-DIAGNOSTIC
Role: Implementer / subsequent independent Reviewer
Agent: existing model_diagnostic_qa_writer / long_completion_review_r1
Base: existing QA branch's clean HEAD; record exact SHA in handoff
Worktree: /Users/developer/Documents/yia-worktrees/readiness-model-diagnostic
Allowed scope: new ignored diagnostic/tests/evidence and task handoff only
Required checks: complete offline fake tests, compile, Ruff, frozen hashes, diff
Special approvals: user's continuing default approval; isolated fixed artifact
Reuse decision: ADAPT reviewed original thinking diagnostic; DIRECT fixed runtime
Parallel now: product-binding independent review in a separate worktree
Waiting: root's frozen package and independent preflight before any model call

Do not touch frozen product WT readiness-configurable-model-binding. Preserve
all original scripts/failed results. Return exact source/script hashes and
checks; stop cleanly before independent review. Root alone executes the one
authorized diagnostic after approval and fresh resource/ownership checks.
