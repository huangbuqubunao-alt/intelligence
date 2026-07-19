# TASK-007 second review reject / Correction 2 — Status Integrator

## Purpose

Synchronize the second independent review rejection and authorize the original Codex Implementer to
perform **only** Correction 2. This is a control-plane commit; it must not alter TASK-007 source,
run product commands, or access TASK-006.

## Required main baseline and source proof

- Main worktree: `/Users/hua/Documents/youtubek agent`, branch `main`, required base
  `1eb3380ea329592a4259b5ead24fde5403f7fa0f`; its index must be empty before staging.
- Source worktree: `/Users/hua/Documents/yia-worktrees/task-007`, branch
  `codex/task-007-local-scoring`, clean at `d8eaeabdd2454141eeb646d9254f4a0a24626605`.
- Review evidence must have sole parent `f46881bc4a8ca0fda4d5ef7006b372bc566cff97` and modify only
  `handoffs/TASK-007.md`. Confirm the original base...source product range remains the approved 11
  path set and `pyproject.toml`/`uv.lock` remain unchanged.
- Do **not** read, run commands in, modify, clean, wait on, or report TASK-006 source worktree.

## Exact main scope

Stage and commit exactly these five Markdown files:

1. `agent-prompts/TASK-007-SECOND-REVIEW-REJECT-CORRECTION-2-INTEGRATOR.md`
2. `agent-prompts/TASK-007-CORRECTION-2-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-007-local-scoring.md`

### Explicit prepared-control-plane exception

At this task's start, the main working tree is expected to contain **exactly these same five paths** as
unstaged/untracked prepared control-plane content and no other change. This is the only exception to
the normal clean-worktree gate. Do not edit their content: record SHA-256 hashes for all five before
any staging, verify that `git diff --name-only` plus `git ls-files --others --exclude-standard` is exactly
this five-path set, then verify the hashes again immediately before commit and after staging. Their
staged blob IDs/content must match the recorded prepared files.

Any existing staged content, additional path, byte change in any prepared file, wrong identity or
unexpected source state is a blocker: stop without cleaning, overwriting, restaging or committing.
This exception does not authorize a concurrent writer, and it does not permit changing TASK-006 text or
accessing its worktree.

## Required state and content checks

- `TASK-007=IN_PROGRESS`; assignee/owner is the original Codex Implementer for Correction 2.
- Record Reviewer evidence `d8eaeabdd2454141eeb646d9254f4a0a24626605`, Verdict `REJECT`, P1=1,
  and its exact L-09 recovery gap.
- Correction boundary is only primary-response recovery persistence/reuse within existing Artifact,
  Provider Call and `complete_stage` semantics. Explicitly forbid Schema/migration/state/domain/config/
  dependency/lock/prompt/main status changes and all real model/service/media/auth/Vault resources.
- Keep every TASK-006 statement and control file byte-for-byte untouched. TASK-006 must not be accessed.
- `TASK-007-CORRECTION-2-CODEX.md` must contain no unresolved placeholder and dynamic authority must
  resolve to this new commit after commit.

## Git procedure

Run only Git/document checks from main; do not run `uv`, tests, build, database, model, media or network
commands. Confirm `Mozhu <huangbuqubunao@gmail.com>` and `user.useConfigOnly=true`.

At minimum run:

```bash
git status --short
git diff --check
git diff --cached --check
git diff --cached --name-only
git show --check --format=fuller HEAD
git status --short
```

Commit message: `docs: return TASK-007 for response recovery correction`.

## Report

Return base/head, identity, exact committed scope, source/evidence chain, state, all Git check results,
confirmation that TASK-006 was untouched, and remaining limits. Do not start the Implementer or Reviewer,
merge, push or clean any worktree.
