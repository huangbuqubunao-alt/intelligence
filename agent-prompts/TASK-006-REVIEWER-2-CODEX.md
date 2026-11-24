# TASK-006 Correction 1 — Second Independent Codex Reviewer

You are a fresh independent Codex Reviewer. Start only after TASK-007 Reviewer has ended.

- Main authority: `git -C '/Users/developer/Documents/youtubek agent' log -1 --format=%H -- agent-prompts/TASK-006-REVIEWER-2-CODEX.md` must resolve to the active authorization, and main TASK-006 must be `IN_REVIEW`.
- Source: `/Users/developer/Documents/yia-worktrees/task-006`, branch `codex/task-006-local-transcription`, reviewed head `17afcd349827b36e5ba18fb0eab443c1ae5fb53f`, sole parent `f1c15ed6eb854a4a8ed2299bbbf89e1cb6266426`, source clean.
- Common base: `6b4d59c882ccdcbd0e5a6069a6661e0672921a80`.

Do not read, run checks in, modify, clean, wait on or report TASK-007 worktree. Stop on wrong state, dirty source, unexpected parent/scope, lockfile change, secret or any model/network/media/resource action.

Review the full base...source range. Correction 1 may change only `src/youtube_intel/transcription.py`, `tests/unit/test_transcription_policy.py`, `tests/integration/test_whisper_provider.py` and `handoffs/TASK-006.md`. You may write only `handoffs/TASK-006.md`, then make one evidence commit with sole parent `17afcd...`. Do not modify code, tests, dependencies, lockfiles, schema, `state.py`, task status, main or source history.

Run only in TASK-006 source:

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
git diff --check 6b4d59c882ccdcbd0e5a6069a6661e0672921a80...17afcd349827b36e5ba18fb0eab443c1ae5fb53f
```

Inspect sdist/wheel for `youtube_intel/migrations/001_initial.sql`. Cache miss is a blocker, not network authority. Do not download/load models, invoke ffmpeg, access media/YouTube/network/Cookie/remote components/Vault/credentials, delete real files or run transcription.

Independently use temporary real SQLite/data roots plus synthetic audio to prove:

1. unknown/missing/deleted/stale/mismatched Artifact records; wrong kind/retention/root/path/hash; symlink and path escapes each return safe `INDEX_CONFLICT` and retain audio;
2. valid current audio Artifact permits deletion then only existing post-delete index CAS; a final CAS race is non-success `INDEX_CONFLICT`, with no exactly-once claim or Schema/reservation workaround;
3. error redaction, ownership/path bounds, Fake-only Whisper boundary, cache-key identity and original resource-policy regressions still hold.

Append checks, probes, AC/ADR-007 matrix, five-axis review, scope/red-line/reuse, skipped paths, P0–P3 and `APPROVE`/`REJECT` to the handoff. `APPROVE` requires no P0/P1. Commit handoff only, leave source clean; do not set `ACCEPTED`/`DONE`, merge or push.
