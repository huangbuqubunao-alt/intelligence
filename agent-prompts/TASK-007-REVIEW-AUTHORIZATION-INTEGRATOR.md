# TASK-007 Review Authorization — Status Integrator

## Role and fixed evidence

You are the main **Status Integrator**. This is a control-plane-only sync for
TASK-007's offline review. Do not run product commands or access the active TASK-006 worktree.

- Required main base: `92740a7c68c19657c5b0f70ce8655a6a72062a1d`
- Source branch/worktree: `codex/task-007-local-scoring` /
  `/Users/hua/Documents/yia-worktrees/task-007`
- Required source head: `258358fcd5227e144c9294beafdf7ec6e2feea63`
- Required source parent/base: `6b4d59c882ccdcbd0e5a6069a6661e0672921a80`

## Allowed main files

1. `agent-prompts/TASK-007-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-007-REVIEWER-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-007-local-scoring.md`

## Initial-state exception and checks

The five Allowed files are prewritten, authorized control-plane content. Require main at the
fixed base, an empty index, correct identity and `user.useConfigOnly=true`; require the working
tree to contain exactly those five files and nothing else. Hash them before checks and require
stability through staging. Do not discard or recreate prepared files.

Verify source branch/head/parent, clean worktree, exact 11-file base...source range within the
seven allowed path groups, unchanged `pyproject.toml`/`uv.lock`, no Schema/shared-contract/task
status change, and `git diff --check`. Confirm TASK-006 is not read, checked, modified, staged,
waited on or cleaned.

Set TASK-007 to `IN_REVIEW`, name a fresh independent Codex Reviewer, and leave TASK-006's
review state unchanged. Do not prewrite any review result.

Run only Git/hash/whitespace/EOF checks, stage the five Allowed files, run
`git diff --cached --check`, commit `docs: authorize TASK-007 independent review`, then verify
main and TASK-007 source are clean. Do not run uv/tests/build, install packages, modify source,
merge/push/remove worktrees, or touch ignored artifacts.
