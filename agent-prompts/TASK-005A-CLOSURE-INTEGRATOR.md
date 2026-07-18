# TASK-005A Closure — Status Integrator

## Role and authority

You are the **Status Integrator**. You may edit and commit only the five Markdown
files named in **Allowed files**. Do not run product checks, change source code,
alter dependencies, merge, push, delete build output, or remove worktrees.

## Fixed evidence

- Required main base: `865f4fed90dcc22ea43688442c1c4f210b4d31b7`
- Required merge parents: `7cdea4b1ff5996bfdcb42c00a245d5ae2b4e02e7` and
  `e726656ffcc96b3c61d12f649c5574dc927add62`
- Required source branch/worktree: `codex/task-005a-local-model-shared-contracts`
  at `e726656ffcc96b3c61d12f649c5574dc927add62`, clean and retained
- Required first-parent product range: exactly the eight paths listed in
  `tasks/TASK-005A-local-model-shared-contracts.md`; `pyproject.toml` and `uv.lock`
  must have no first-parent diff.

## Allowed files

1. `agent-prompts/TASK-005A-CLOSURE-INTEGRATOR.md`
2. `docs/PROJECT_STATUS.md`
3. `handoffs/TASK-005A.md`
4. `tasks/README.md`
5. `tasks/TASK-005A-local-model-shared-contracts.md`

## Required checks

1. Confirm `main` is exactly the required base, clean, and has no staged changes.
2. Confirm the merge has exactly the two required parents; verify the source is an
   ancestor; verify `git diff --name-status <first-parent>..<merge>` is exactly the
   approved eight paths and `git diff --check` passes.
3. Confirm the retained source branch/head/worktree is correct and clean.
4. Confirm initial scope is exactly the five Allowed files and all are Markdown.
   Treat ignored `dist/` as non-Git-visible: do not stage, delete, clean, or report
   it as a working-tree change.
5. Confirm task-card, task table, project status, and handoff all state
   `TASK-005A=DONE`; confirm TASK-006/TASK-007 remain `BLOCKED/UNASSIGNED`, now
   awaiting only their task-specific resource authorization.
6. Run `git diff --check`, whitespace/EOF checks, stage only Allowed files, run
   `git diff --cached --check`, commit with `docs: close TASK-005A after integration`,
   and verify clean status on main and the retained source worktree.

## Boundary

The Product Integrator already ran the approved post-merge checks (focused 53/10/34,
full 251, mypy, Ruff, CLI, locked sync, and offline build/package migration inclusion).
Record that evidence only; do not rerun it. Do not start or authorize TASK-006/007,
and do not grant models, Ollama, ffmpeg, media, network, credential, Vault, or
deletion operations.
