# TASK-006 Correction 2 — Third Independent Codex Reviewer

You are a fresh independent Codex Reviewer. You did not implement TASK-006 or either of
its corrections. Review only `/Users/hua/Documents/yia-worktrees/task-006` on branch
`codex/task-006-local-transcription`.

## Authority and isolation

- Common base: `6b4d59c882ccdcbd0e5a6069a6661e0672921a80`.
- Reviewed head: `51b308828a6f2c433a9b4e92fb4a24e042f55d77`; its sole parent must be
  `47599db196b1b9440de3ae57ec3547935f64b1dc`.
- Main authority: from `/Users/hua/Documents/youtubek agent`,
  `git log -1 --format=%H -- agent-prompts/TASK-006-REVIEWER-3-CODEX.md` must resolve to
  the active authorization commit, and main TASK-006 must be `IN_REVIEW`.
- Source worktree must be clean before review. Stop on wrong branch, head, parent, state,
  scope, an unexpected dependency/lockfile change after `47599db...`, secret, or any
  unapproved resource action. The authorized initial TASK-006 range already contains the
  original `pyproject.toml` and `uv.lock` additions.

TASK-007 is closed and completely outside this task. Do not read, run checks in, modify,
clean, wait on, or report on `/Users/hua/Documents/yia-worktrees/task-007`.

## Scope and write rule

Review the full `base...source` range. Correction 2 may change only:

- `src/youtube_intel/transcription.py`
- `tests/unit/test_transcription_policy.py`
- `tests/integration/test_whisper_provider.py`
- `handoffs/TASK-006.md`

You may write only `handoffs/TASK-006.md`, then create one review-evidence commit with
`51b308828a6f2c433a9b4e92fb4a24e042f55d77` as its sole parent. Do not amend source,
modify product code/tests, dependencies/lockfiles, Schema/migrations, `state.py`, task
status, main, or source history. Do not merge, push, or clean any worktree.

## Required offline reruns

Run only in the TASK-006 source worktree:

```bash
uv lock --check
uv sync --locked --offline
uv run python -m pytest tests/unit/test_transcription_policy.py
uv run python -m pytest tests/integration/test_whisper_provider.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
uv build --offline
git diff --check 6b4d59c882ccdcbd0e5a6069a6661e0672921a80...51b308828a6f2c433a9b4e92fb4a24e042f55d77
```

Inspect the generated sdist and wheel for `youtube_intel/migrations/001_initial.sql`.
Offline cache miss is a blocker, not network authority. Never download/load a Whisper model,
invoke or install ffmpeg, run transcription, access media/YouTube/network/Cookie/remote
components/Vault/credentials, or delete real files.

## Independent probes

Use temporary real SQLite/DATA roots and synthetic audio only. Do not alter repository files.

1. For absolute paths, relative `..` paths, DATA-root escapes, and symlinks, require the
   retryable error `INDEX_CONFLICT`, no path-content disclosure, no deletion of the indexed
   file, and no deletion of any external target. Repeat the probe through every public cleanup
   entry point.
2. Recheck the prior safety matrix: unknown, missing, already-deleted, stale, hash-mismatched,
   wrong-kind, wrong-retention, and wrong-root Artifact records all retain audio and return
   `INDEX_CONFLICT`.
3. Recheck the allowed success path: only a current matching `AUDIO` or `EPHEMERAL_AUDIO`
   record permits deletion; the existing post-delete CAS remains required. A final CAS race is
   non-success `INDEX_CONFLICT`, with no reservation, Schema change, or exactly-once claim.
4. Recheck Fake-only Whisper/import boundaries, cache identity, timeout/resource failure
   mapping, ownership/path redaction, and the original retention-policy regressions.

Review TASK-006 ACs, ADR-007 applicable L-01--L-15 boundaries, correctness, architecture,
security/privacy, performance/resources, readability, scope, red lines, reuse, and licensing.

## Handoff and verdict

Append commands/results, all probes, AC/ADR matrix, five-axis review, scope/red-line/reuse
review, skipped unauthorized paths, P0--P3 findings, and `APPROVE` or `REJECT` to the handoff.
`APPROVE` requires no unresolved P0/P1. Commit the handoff only; leave source clean and do not
set `ACCEPTED`/`DONE`.
