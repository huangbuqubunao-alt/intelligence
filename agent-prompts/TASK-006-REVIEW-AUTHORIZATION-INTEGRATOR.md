# TASK-006 Review Authorization — Status Integrator

## Role and fixed evidence

You are the main **Status Integrator**. This is a control-plane-only sync for
TASK-006 Phase A; do not run product commands or access the active TASK-007 worktree.

- Required main base: `78b7e54e32d8b97a148f151b0bf86127121de292`
- Source branch/worktree: `codex/task-006-local-transcription` /
  `/Users/hua/Documents/yia-worktrees/task-006`
- Required source head: `c6ff804569b376c347719296d80fbe1abf99057a`
- Required source parent/base: `6b4d59c882ccdcbd0e5a6069a6661e0672921a80`

## Allowed main files

1. `agent-prompts/TASK-006-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-006-REVIEWER-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-006-local-transcription.md`

## Initial-state exception and checks

The five Allowed files are prewritten, authorized control-plane content. Require main at the
fixed base, an empty index, correct identity and `user.useConfigOnly=true`; require the working
tree to contain exactly those five files and nothing else. Hash them before checks and require
stability through staging. Do not discard or recreate prepared files.

Verify source branch/head/parent, clean worktree, exact 8-path base...source range, no first-party
Schema/shared-contract/task-status change, exact direct dependency addition only, unchanged source
after checks, and `git diff --check`. Confirm TASK-007 is not read, checked, modified, staged,
waited on or cleaned.

Set TASK-006 to `IN_REVIEW`, name a fresh independent Codex Reviewer, and leave TASK-007 as
`IN_PROGRESS`. Do not prewrite any review result.

Run only Git/hash/whitespace/EOF checks, stage the five Allowed files, run
`git diff --cached --check`, commit `docs: authorize TASK-006 independent review`, then verify
main and TASK-006 source are clean. Do not run uv/tests/build, install packages, modify source,
merge/push/remove worktrees, or touch ignored artifacts.
