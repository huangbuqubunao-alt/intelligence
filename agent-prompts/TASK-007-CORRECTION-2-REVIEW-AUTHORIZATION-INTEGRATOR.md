# TASK-007 Correction 2 review authorization — Status Integrator

## Purpose

Synchronize Correction 2 implementation evidence and authorize a **fresh independent Codex Reviewer**.
This is a control-plane commit only: do not run product commands, modify TASK-007 source, or access
TASK-006.

## Preconditions

- Main: `/Users/developer/Documents/youtubek agent`, `main@1aa3dc22b96a0d0493c656a4ce4f5490bd6f770b`, empty
  index before preparation.
- Source: `/Users/developer/Documents/yia-worktrees/task-007`, branch `codex/task-007-local-scoring`, clean at
  `567b0f63f9cefc6c8bff43bfea0e9e156ac3a02c`; sole parent must be
  `d8eaeabdd2454141eeb646d9254f4a0a24626605`.
- Correction range is exactly five allowed files; full base...source range remains the approved 11 paths;
  `pyproject.toml` and `uv.lock` have no difference from the common base.
- Confirm `Mozhu <maintainer@example.invalid>` and `user.useConfigOnly=true`.

## Exact main scope

Stage and commit exactly these five Markdown files:

1. `agent-prompts/TASK-007-CORRECTION-2-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-007-REVIEWER-3-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-007-local-scoring.md`

### Explicit prepared-control-plane exception

At start, main is expected to contain **exactly these five paths** as unstaged/untracked prepared
control-plane content and no other change. This is the sole exception to the normal clean-worktree gate.
Do not edit their content: record SHA-256 hashes before staging, verify that `git diff --name-only` plus
`git ls-files --others --exclude-standard` is exactly this five-path set, and verify the hashes again
after staging and immediately before commit. Staged blobs must match the recorded prepared content.

Any pre-existing staged content, extra path, concurrent byte change, wrong identity or source mismatch is
a blocker. Stop without cleanup, overwrite, restaging, source modification or commit. This exception does
not permit a concurrent writer and does not permit a TASK-006 change or access.

## Required synchronization

- Set TASK-007 to `IN_REVIEW`; reviewer is a fresh independent Codex session.
- Record source `567b0f...`, parent `d8eaeab...`, Correction 2's five-file scope and self-reported checks
  as unverified evidence only.
- The Reviewer package must contain no placeholder; its dynamic authority must resolve to this new commit.
- Preserve TASK-006 statements and files byte-for-byte; do not access its worktree.
- Do not prewrite `APPROVE`, `ACCEPTED`, merge SHA or `DONE`; no Reviewer may start until this commit is
  confirmed.

## Checks and report

Use only Git/document checks: file hashes, `git diff --check`, `git diff --cached --check`, exact staged
scope, source range/parent checks, EOF/trailing whitespace, post-commit scope/parent and clean statuses.
Do not run uv, tests, build, database, model, media or network commands. Commit message:

```text
docs: authorize TASK-007 recovery review
```

Report base/head, identity, exact scope, source chain/status, state, checks, confirmation that TASK-006
was untouched and remaining resource limits. Do not start a Worker, merge, push or clean worktrees.
