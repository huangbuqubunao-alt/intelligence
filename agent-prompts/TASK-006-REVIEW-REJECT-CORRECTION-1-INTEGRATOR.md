# TASK-006 Review Reject / Correction 1 — Status Integrator

## Role and fixed evidence

You are the main **Status Integrator**. This is a control-plane-only correction sync.
Do not run product commands or access the active TASK-007 Reviewer worktree.

- Required main base: `ecabaf70774858a90f949e635926a0ef0a83577e`
- Source branch/worktree: `codex/task-006-local-transcription` /
  `/Users/developer/Documents/yia-worktrees/task-006`
- Required review evidence: `f1c15ed6eb854a4a8ed2299bbbf89e1cb6266426`
- Required evidence parent/source implementation: `c6ff804569b376c347719296d80fbe1abf99057a`

## Allowed main files

1. `agent-prompts/TASK-006-REVIEW-REJECT-CORRECTION-1-INTEGRATOR.md`
2. `agent-prompts/TASK-006-CORRECTION-1-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-006-local-transcription.md`

## Initial-state exception and checks

The five Allowed files are prewritten authorized control-plane content. Require main at the fixed
base, an empty index, correct identity and `user.useConfigOnly=true`; require the working tree to
contain exactly those five files and nothing else. Hash them before checks and require stability
through staging. Do not discard or recreate them.

Verify source evidence/head/parent chain, evidence one-file handoff scope, implementation 8-path
range, source cleanliness and `git diff --check`. Confirm the P1 statement and approved boundary:
`mark_artifact_deleted` remains post-delete index-only confirmation; `state.py`, Schema and
migration remain forbidden. Do not access TASK-007 in any way.

Set TASK-006 to `IN_PROGRESS` for its original Codex Implementer Correction 1; preserve TASK-007
as `IN_REVIEW`, without prewriting any TASK-007 finding or verdict.

Run only Git/hash/whitespace/EOF checks, stage the five Allowed files, run
`git diff --cached --check`, commit `docs: return TASK-006 for artifact cleanup correction`, then
verify main and TASK-006 source are clean. Do not run uv/tests/build, edit source, merge/push or
remove worktrees.
