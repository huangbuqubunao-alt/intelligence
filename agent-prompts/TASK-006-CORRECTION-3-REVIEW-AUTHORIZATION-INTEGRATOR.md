# TASK-006 Correction 3 — Review Authorization Status Integrator

You are the Status Integrator. Work only in `/Users/developer/Documents/youtubek agent` on `main`.
This is a documentation-only control-plane commit. Do not run product commands, install
packages, run tests/builds, merge, push, clean, start a Worker, or access TASK-007. Read-only
Git verification of the TASK-006 source is allowed.

## Fixed facts

- Required main base: `aee73330d864fa0806a999bce8168cd8ec403dc3`.
- TASK-006 source: `/Users/developer/Documents/yia-worktrees/task-006`, branch
  `codex/task-006-local-transcription`, clean at
  `548338978b8656db0c650be276f847850af940a1`; its sole parent is
  `66f0b31023c290d76e2c14bea72d1cc103cc27c7`.
- Correction 3 changes exactly `transcription.py`, the authorized cache-key call site in
  `providers/whisper.py`, the two existing transcription test files, and
  `handoffs/TASK-006.md`. The full `6b4d59c...source` range remains within the original eight
  approved TASK-006 path groups.
- Relative to `66f0b310...`, `state.py`, Schema/migrations, dependencies, lockfiles, config,
  domain, task status, main, and TASK-007 are unchanged.
- Implementer reports focused `11/12`, full `274`, mypy, Ruff, CLI, locked offline sync,
  offline build, and migration packaging PASS. These are unverified implementation evidence,
  not Reviewer approval.
- Main must become `IN_REVIEW` for a fresh independent fourth Codex Reviewer. Do not write
  `APPROVE`, `ACCEPTED`, a merge SHA, or `DONE`.

## Prepared-control exception and exact scope

The working tree intentionally contains exactly these prepared control-plane paths:

1. `agent-prompts/TASK-006-CORRECTION-3-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-006-REVIEWER-4-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-006-local-transcription.md`

Before staging, require an empty index and `git status --short` containing exactly those five
paths and nothing else. Record SHA-256 for all five files. Read their final contents and verify
the fixed source, five-path scope, unverified evidence, `IN_REVIEW` state, and unchanged
TASK-007 status. Any extra path or hash change is a blocker: stop without cleanup, overwrite,
or restaging.

## Required gates and commit

1. Confirm `main@aee73330...`, `Mozhu <maintainer@example.invalid>`, and
   `user.useConfigOnly=true`.
2. Confirm source branch/head/sole parent/cleanliness, exact five-file Correction 3 range,
   full approved eight-path range, and no dependency/lockfile change after `66f0b310...`.
3. Run `git diff --check`; verify LF-at-EOF and no trailing whitespace in prepared files.
4. Stage only the five listed files. Recheck working-file and staged-blob SHA-256, exact staged
   scope, and `git diff --cached --check`.
5. Commit `docs: authorize TASK-006 correction 3 review`; verify the sole parent is the
   required base, committed scope is exactly five files, and main/source worktrees are clean.

After the commit, resolve
`git log -1 --format=%H -- agent-prompts/TASK-006-REVIEWER-4-CODEX.md`; it must equal this
commit and becomes the Reviewer authorization. Do not launch the Reviewer. Report the commit
SHA, checks, source facts, task status, and unchanged real-resource restrictions.
