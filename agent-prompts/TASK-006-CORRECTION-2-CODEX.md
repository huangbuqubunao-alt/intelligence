# TASK-006 Correction 2 — Codex Implementer

You are the original Codex Implementer in `/Users/developer/Documents/yia-worktrees/task-006` on `codex/task-006-local-transcription`.

- Common base: `6b4d59c882ccdcbd0e5a6069a6661e0672921a80`
- Start/sole-parent evidence: `47599db196b1b9440de3ae57ec3547935f64b1dc`
- Main authority: `git -C '/Users/developer/Documents/youtubek agent' log -1 --format=%H -- agent-prompts/TASK-006-CORRECTION-2-CODEX.md` resolves to the authorization commit; TASK-006 must be `IN_PROGRESS`.

Do not access TASK-007. Stop on dirty source, wrong state/parent, scope expansion, dependency/lock change, secret or real-resource action.

Fix exactly one P1: cleanup preflight may safely retain symlink/path-escape files but returns `PATH_OUTSIDE_DATA`; it must instead return safe retryable `INDEX_CONFLICT` for symlink, absolute/relative escape and root escape. Preserve the files/targets, do not disclose paths, and do not change unknown/missing/hash/kind/retention/root, valid delete or final CAS-race semantics. No reservation/Schema/exactly-once change.

Allowed scope only: `src/youtube_intel/transcription.py`, `tests/unit/test_transcription_policy.py`, `tests/integration/test_whisper_provider.py`, `handoffs/TASK-006.md`. No provider/state/schema/migration/domain/config/dependency/lock/task status/main change.

Use existing SQLite Artifact API and Python standard library only. With temporary real SQLite/DATA roots and synthetic audio, add RED/GREEN cases for symlink/path escapes returning `INDEX_CONFLICT` plus no physical deletion; retain prior cleanup/CAS safety coverage.

Run source-only/offline:

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
git diff --check 47599db196b1b9440de3ae57ec3547935f64b1dc...HEAD
git status --short
```

Verify package migration inclusion. No model/weight download/load, ffmpeg, media/YouTube/network/Cookie/remote components/Vault/credentials/real deletion or transcription. Append evidence/reuse/scope/unrun paths to handoff; one commit; clean; no Reviewer/merge/push/status change.
