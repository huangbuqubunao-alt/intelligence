# TASK-006 Correction 3 Scope Resolution — Status Integrator

You are the Status Integrator. Work only in `/Users/hua/Documents/youtubek agent` on `main`.
This is a documentation-only control-plane commit. Do not run product commands, install
packages, run tests/builds, merge, push, clean, start a Worker, or access TASK-007. Read-only
Git verification of the TASK-006 source is allowed.

## Fixed facts and decision

- Required main base: `bdd1f432bdcc8da2e49a70c107d19cf65538527f`.
- TASK-006 source is `/Users/hua/Documents/yia-worktrees/task-006` on
  `codex/task-006-local-transcription`, clean at
  `66f0b31023c290d76e2c14bea72d1cc103cc27c7`; no source edit or product command
  occurred after the scope conflict was reported.
- The original Implementer correctly stopped: `WhisperDecodePolicy.language_hint` is defined in
  `providers/whisper.py`, while `build_transcription_cache_key()` is defined in
  `transcription.py` and its sole production call site is in `providers/whisper.py`.
- The product owner/orchestrator resolves the conflict by adding
  `src/youtube_intel/providers/whisper.py` to Correction 3. This is within TASK-006's original
  approved scope. In that file, only the existing cache-key call site may change to pass
  `self._decode_policy.language_hint`.
- `build_transcription_cache_key()` must take a required keyword-only
  `language_hint: str | None`. Do not add a public Adapter method argument or change current
  decode-policy validation/normalization, executor invocation, model/resource behavior, error
  mapping, dependencies, lockfiles, Schema, `state.py`, main, or TASK-007.
- TASK-006 remains `IN_PROGRESS` with the original Codex Implementer. Do not create a Reviewer
  packet or write `IN_REVIEW`, `ACCEPTED`, or `DONE`.

## Prepared-control exception and exact scope

The working tree intentionally contains exactly these prepared control-plane paths:

1. `agent-prompts/TASK-006-CORRECTION-3-CODEX.md`
2. `agent-prompts/TASK-006-CORRECTION-3-SCOPE-RESOLUTION-INTEGRATOR.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/TASK-006-local-transcription.md`

Before staging, require an empty index and `git status --short` containing exactly these four
paths and nothing else. Record SHA-256 for all four files. Read their final prepared contents
and verify the five-path Correction scope, Provider call-site-only boundary, unchanged task
state, and unchanged TASK-007 status. Any extra path or hash change is a blocker: stop without
cleanup, overwrite, or restaging.

## Required gates and commit

1. Confirm `main@bdd1f432...`, `Mozhu <huangbuqubunao@gmail.com>`, and
   `user.useConfigOnly=true`.
2. Confirm the TASK-006 source branch/head/cleanliness and that no source commit followed
   `66f0b310...`.
3. Run `git diff --check`; verify LF-at-EOF and no trailing whitespace in all prepared files.
4. Stage only the four listed files. Recheck working-file and staged-blob SHA-256, exact staged
   scope, and `git diff --cached --check`.
5. Commit `docs: resolve TASK-006 correction 3 scope`; verify the sole parent is the required
   base, committed scope is exactly four files, and main/source worktrees are clean.

After the commit, resolve
`git log -1 --format=%H -- agent-prompts/TASK-006-CORRECTION-3-CODEX.md`; it must equal this
commit and becomes the active Implementer authorization. Do not launch the Implementer. Report
the commit SHA, checks, fixed decision, task status, and unchanged real-resource restrictions.
