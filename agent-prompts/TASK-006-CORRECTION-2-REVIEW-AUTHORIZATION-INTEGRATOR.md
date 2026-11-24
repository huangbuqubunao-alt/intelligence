# TASK-006 Correction 2 — Review Authorization Status Integrator

You are the Status Integrator. Work only in `/Users/developer/Documents/youtubek agent` on `main`.
This is a documentation-only control-plane commit; do not run product commands, access the
TASK-006 source worktree except for read-only Git verification, access TASK-007, install
packages, run tests/builds, merge, push, or clean any worktree.

## Fixed facts

- Required main base: `a33c358c41fd255dc455b9ab57303336f9ff3f83`.
- TASK-006 source: `/Users/developer/Documents/yia-worktrees/task-006`, branch
  `codex/task-006-local-transcription`, head
  `51b308828a6f2c433a9b4e92fb4a24e042f55d77`, clean, sole parent
  `47599db196b1b9440de3ae57ec3547935f64b1dc`.
- Correction 2 range is exactly `transcription.py`, the two existing transcription test files,
  and `handoffs/TASK-006.md`; full product range from `6b4d59c...` remains the approved eight
  paths. Relative to `47599db...`, `state.py`, Schema/migrations, dependencies, and lockfiles
  are unchanged; the original authorized TASK-006 range already contains `pyproject.toml` and
  `uv.lock` additions.
- Reviewer evidence does not yet exist. Main must become `IN_REVIEW`, not `ACCEPTED` or `DONE`.
- TASK-007 is closed; do not read or modify its worktree or control-plane content.

## Prepared-control exception and exact scope

The working tree intentionally contains exactly these prepared control-plane paths; their
content is already final. This is not a product-code dirty-tree exception.

1. `agent-prompts/TASK-006-CORRECTION-2-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-006-REVIEWER-3-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-006-local-transcription.md`

Before staging, require an empty index and `git status --short` to show exactly those five
paths and no other changes. Record SHA-256 for every prepared file. Read their final content;
verify TASK-006 is consistently `IN_REVIEW`, Correction 2 is unverified self-report evidence,
and no TASK-007 wording changed. If an unexpected path appears or a prepared-file hash changes,
stop without cleanup, overwrite, or restaging.

## Required read-only gates

1. Confirm `main@a33c358...`, Git identity `Mozhu <maintainer@example.invalid>`, and
   `user.useConfigOnly=true`.
2. Confirm source branch, head, sole parent, clean status, Correction 2 four-file range,
   full approved eight-path range, and no `pyproject.toml`/`uv.lock` change in
   `47599db...51b308...`.
3. Run `git diff --check`; check LF at EOF and trailing whitespace for all prepared files.
4. Stage only the five paths. Recheck SHA-256 of working files and staged blobs; require exact
   staged scope and `git diff --cached --check` success.
5. Commit with `docs: authorize TASK-006 cleanup enum review`. Verify one parent equal to the
   required base, exact five-file committed scope, and clean main/source statuses.

Only after the commit, resolve
`git log -1 --format=%H -- agent-prompts/TASK-006-REVIEWER-3-CODEX.md`; it must return this
authorization commit. Do not start the Reviewer. Report the commit SHA, scope, checks, source
facts, status, and remaining unapproved real-resource paths.
