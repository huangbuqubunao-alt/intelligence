# TASK-006 阶段 A Correction 1 — Codex Implementer

## Authority

You are the original TASK-006 Codex Implementer returning to its source worktree.

- Worktree/branch: `/Users/developer/Documents/yia-worktrees/task-006` /
  `codex/task-006-local-transcription`
- Starting evidence: `f1c15ed6eb854a4a8ed2299bbbf89e1cb6266426`
- Required parent for your correction commit: exactly that review evidence
- Main authorization: resolve `git log -1 --format=%H -- agent-prompts/TASK-006-CORRECTION-1-CODEX.md`
  in `/Users/developer/Documents/youtubek agent`; its task card must be `IN_PROGRESS`/Correction 1.

TASK-007 is under independent review. Do not read, run checks in, modify, wait on, clean or report
on its worktree.

## P1 to fix

The current cleanup deletes an audio file before the repository's post-delete CAS call. A real
SQLite probe proved an unknown Artifact id or stale CAS returns `INDEX_CONFLICT` only after the
file is already gone.

## Approved design boundary

`SQLiteStateRepository.mark_artifact_deleted()` is intentionally an **index-only confirmation of
an already-performed deletion**. Do not change it, `state.py`, its public contract, Schema or
migrations; do not mark before deletion. Instead:

1. Before any unlink, use existing approved Repository reads to verify the registered Artifact
   identity/key/hash, `AUDIO` kind, `EPHEMERAL_AUDIO` retention, DATA-root relative path, matching
   non-symlink file and `deleted_at is None`.
2. If any precondition is absent/mismatched/stale, leave bytes untouched and return a safe
   `INDEX_CONFLICT` diagnostic.
3. Only after successful preflight may the controlled file be deleted; then call the existing
   post-delete CAS confirmation.
4. If the final CAS loses a concurrent race, return a safe non-success diagnostic and document the
   remaining at-most-once cleanup window. Do not falsely report index success or claim exactly-once.

No reservation, lock, Schema or `state.py` workaround is authorized. Such a design would require a
separate decision.

## Exact allowed files

- `src/youtube_intel/transcription.py`
- `tests/unit/test_transcription_policy.py`
- `tests/integration/test_whisper_provider.py`
- `handoffs/TASK-006.md`

Do not modify dependencies/lockfiles, Provider API surface unrelated to cleanup, state/migration,
shared contracts, task status or main. Do not download/load models, invoke/install ffmpeg, download
media, run real transcription, network, credentials, Vault or deletion outside test-controlled
temporary files.

## Required proof and checks

- Add regressions with a temporary real SQLite repository proving unknown id and stale/mismatched
  CAS keep audio bytes intact; verify valid success still deletes then records confirmation.
- Cover wrong kind/retention/root/hash, missing/deleted record, symlink/path escape and final CAS
  race diagnostics without sensitive path/content leakage.
- Re-run `uv lock --check`, `uv sync --locked`, focused unit/integration tests, full pytest, mypy,
  Ruff, CLI help, `uv build --offline`, package migration inclusion and fixed `git diff --check`.
- Record the P1 closure, exact residual at-most-once window, checks and 4-file correction scope in
  the handoff. Commit only after every check passes; source must end clean. Do not start a Reviewer
  or change task status.
