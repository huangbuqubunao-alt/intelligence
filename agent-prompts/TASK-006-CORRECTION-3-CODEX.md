# TASK-006 Correction 3 — Codex Implementer

You are the original Codex Implementer. Work only in
`/Users/developer/Documents/yia-worktrees/task-006` on branch
`codex/task-006-local-transcription`.

## Authority and start gate

- Common base: `6b4d59c882ccdcbd0e5a6069a6661e0672921a80`.
- Required start/head: `66f0b31023c290d76e2c14bea72d1cc103cc27c7`; its sole parent must be
  `51b308828a6f2c433a9b4e92fb4a24e042f55d77`.
- Main authority: from `/Users/developer/Documents/youtubek agent`,
  `git log -1 --format=%H -- agent-prompts/TASK-006-CORRECTION-3-CODEX.md` must resolve to
  the active authorization commit, and main TASK-006 must be `IN_PROGRESS`.

Stop immediately on a dirty source worktree, wrong branch/head/parent/state, scope expansion,
any dependency or lockfile change after `66f0b310...`, secret, or unapproved real-resource
action. The original authorized TASK-006 range already contains `pyproject.toml` and `uv.lock`
additions. TASK-007 is closed and out of scope: do not read, run checks in, modify, clean, wait
on, or report it.

## Required P1 corrections

Fix both findings without changing the established cleanup order, Artifact API, Schema, or
resource boundary.

1. **Cache identity.** The request's `language_hint` is semantic input. Include its existing
   validated `WhisperDecodePolicy.language_hint` value in the transcription cache identity so
   otherwise-identical requests for different language hints cannot reuse an earlier transcript.
   Make `language_hint: str | None` a required keyword-only input of
   `build_transcription_cache_key()` and pass `self._decode_policy.language_hint` at the existing
   `MlxWhisperAdapter` cache-key call site. Do not add a new public Adapter method parameter,
   change executor invocation, or change the current decode-policy validation/normalization
   behavior. Preserve existing behavior for identical requests and existing `None`/empty
   validation behavior. Add focused regressions proving different language hints do not hit the
   same cached result or Artifact and identical hints retain the existing cache hit.
2. **Unified ineligible Artifact error.** Wrong kind, retention, or DATA root in cleanup
   preflight must return safe, retryable `INDEX_CONFLICT`, not `INELIGIBLE_ARTIFACT`. Preserve
   the file and any external target, redact paths, and retain existing semantics for unknown,
   missing, deleted, stale, hash-mismatched and path/symlink-escape records, valid deletion, and
   final post-delete CAS race. Do not introduce a reservation or claim exactly-once cleanup.

Use temporary real SQLite/DATA roots and synthetic audio for regressions. No model, media, or
network operation is authorized.

## Allowed scope

Only modify:

- `src/youtube_intel/transcription.py`
- `src/youtube_intel/providers/whisper.py` — only the cache-key wiring described above
- `tests/unit/test_transcription_policy.py`
- `tests/integration/test_whisper_provider.py`
- `handoffs/TASK-006.md`

Outside that single Provider call-site change, do not change Provider execution, model/resource,
error, download, or public Adapter behavior. Do not change `state.py`, domain/config,
Schema/migrations, dependencies/lockfiles, task status, main, source history, or any TASK-007
file.

## Required offline validation

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
git diff --check 66f0b31023c290d76e2c14bea72d1cc103cc27c7...HEAD
git status --short
```

Verify generated sdist and wheel contain `youtube_intel/migrations/001_initial.sql`. Never
download/load a Whisper model, invoke/install ffmpeg, run transcription, access media/YouTube/
network/Cookie/remote components/Vault/credentials, or delete real files.

Append P1 closure evidence, tests, scope, reuse, skipped paths, and remaining at-most-once risk
to the handoff. Create one commit with `66f0b310...` as its sole parent; leave the worktree
clean. Do not start a Reviewer, merge, push, or change task status.
