# TASK-006 Third Review Reject — Correction 3 Status Integrator

You are the Status Integrator. Work only in `/Users/developer/Documents/youtubek agent` on `main`.
This is a documentation-only control-plane commit. Do not run product commands, install
packages, run tests/builds, merge, push, clean, start a Worker, or access TASK-007. Read-only
Git verification of the TASK-006 source is allowed.

## Fixed facts

- Required main base: `3eeeac58a5662c4098b1d483f70c9b94fca23699`.
- TASK-006 source is `/Users/developer/Documents/yia-worktrees/task-006` on
  `codex/task-006-local-transcription`, clean at
  `66f0b31023c290d76e2c14bea72d1cc103cc27c7`; sole parent
  `51b308828a6f2c433a9b4e92fb4a24e042f55d77`; evidence modifies only
  `handoffs/TASK-006.md`.
- Reviewer verdict is `REJECT`, P1=2: `language_hint` missing from cache identity, and wrong
  kind/root/retention Artifact preflight returning `INELIGIBLE_ARTIFACT` instead of retryable
  `INDEX_CONFLICT`.
- Correction 3 may modify only `transcription.py`, the two existing transcription test files,
  and `handoffs/TASK-006.md`; no Provider, `state.py`, Schema/migration, dependency, lockfile,
  task-status, main, or TASK-007 change is allowed.
- Main must become `IN_PROGRESS` for the original Codex Implementer. Do not create a Reviewer
  packet or write `ACCEPTED`/`DONE`.

## Prepared-control exception and exact scope

The working tree intentionally contains exactly these prepared final control-plane paths; this
is not a product-code dirty-tree exception:

1. `agent-prompts/TASK-006-CORRECTION-3-CODEX.md`
2. `agent-prompts/TASK-006-THIRD-REVIEW-REJECT-CORRECTION-3-INTEGRATOR.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-006-local-transcription.md`

Before staging, require an empty index and `git status --short` containing exactly those five
paths and nothing else. Record SHA-256 hashes for all five files. Read the final prepared
contents: TASK-006 must consistently be `IN_PROGRESS`; correction scope and unverified status
must be accurate; TASK-007 wording must be unchanged. Any extra path/hash change is a blocker:
stop without cleanup, overwrite, or restaging.

## Required gates and commit

1. Confirm `main@3eeeac...`, `Mozhu <maintainer@example.invalid>`, and
   `user.useConfigOnly=true`.
2. Confirm source branch/head/parent/cleanliness, evidence one-file scope, Correction 2
   four-file range, full approved eight-path range, and no lockfile change after `51b308...`.
3. Run `git diff --check`; verify LF-at-EOF and no trailing whitespace in prepared files.
4. Stage only the five listed files. Recheck working-file and staged-blob SHA-256, exact staged
   scope, and `git diff --cached --check`.
5. Commit `docs: return TASK-006 for cache and enum correction`; verify the sole parent is the
   required base, committed scope is exactly five files, and main/source worktrees are clean.

After the commit, resolve
`git log -1 --format=%H -- agent-prompts/TASK-006-CORRECTION-3-CODEX.md`; it must equal this
commit. Do not launch the Implementer. Report SHA, checks, fixed facts, status, and remaining
unapproved model/media/network/Vault paths.
