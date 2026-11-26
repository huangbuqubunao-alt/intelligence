# TASK-006 阶段 A — Codex Implementer

## Authority and live control plane

- Source base: `main@6b4d59c882ccdcbd0e5a6069a6661e0672921a80`
- Worktree: `/Users/developer/Documents/yia-worktrees/task-006`
- Branch: `codex/task-006-local-transcription`
- Main control plane is authoritative. This source worktree intentionally starts from
  the pre-assignment snapshot, where its local task card says `BLOCKED`. Before writing,
  resolve `git log -1 --format=%H -- agent-prompts/TASK-006-IMPLEMENTER-CODEX.md` on
  `main` and verify that version of the task card says `IN_PROGRESS`/`Codex`.

## Goal

Implement the fully offline, model-free Phase A of the local Whisper Adapter: dependency
locking, typed policy/cache/error/cleanup behavior and Fake/fixture-backed tests. Do not
download or load a model, decode through ffmpeg, download media, or run a real transcription.

## Approved scope

- `src/youtube_intel/transcription.py`
- `src/youtube_intel/providers/whisper.py`
- `tests/unit/test_transcription_policy.py`
- `tests/integration/test_whisper_provider.py`
- `tests/fixtures/audio/**`
- `pyproject.toml`
- `uv.lock`
- `handoffs/TASK-006.md`

No other product, configuration, Schema/migration, shared-contract, task-status, or main files
may change. An audio fixture must be a documented redistributable or deterministic synthetic WAV;
it must not be obtained from YouTube or another real-media service.

## Dependency and reuse decision

- `DIRECT`: `mlx-whisper>=0.4.3,<0.5`, installed only through uv with the minimal necessary
  transitive resolution. Record resolved versions, license evidence and Python 3.12/arm64
  compatibility in the handoff.
- `DIRECT`: existing Pydantic/SQLite contracts and Python standard library.
- `REFERENCE`: official MLX Whisper documentation only; do not copy third-party implementation
  code.

Run `uv add "mlx-whisper>=0.4.3,<0.5"`, `uv lock`, and `uv sync --locked` only within this
worktree. If resolution needs a new direct dependency, an unapproved system tool, or an
incompatible Python/platform package, stop with `DECISION NEEDED`.

## Forbidden in this phase

No Whisper model/revision/weight download or loading; no Hugging Face/network model request;
no ffmpeg install, invocation or subprocess; no media/YouTube download; no real transcription;
no Cookie/login/`.netrc`/remote components; no Ollama; no Vault/secret; no file deletion outside
test-controlled temporary paths. Do not silently replace MLX Whisper with another library.

## Required checks

1. `uv lock --check`
2. `uv sync --locked`
3. `uv run python -m pytest tests/unit/test_transcription_policy.py`
4. `uv run python -m pytest tests/integration/test_whisper_provider.py`
5. `uv run python -m pytest`
6. `uv run mypy src`
7. `uv run ruff check .`
8. `uv run python -m youtube_intel --help`
9. `uv build --offline`
10. Confirm sdist/wheel include `youtube_intel/migrations/001_initial.sql`.
11. `git diff --check <base>...HEAD` and a complete scope/secret review.

## Handoff

Record AC evidence, package/transitive/license facts, fixture provenance, all deliberately
unrun resource paths, and final Diff scope in `handoffs/TASK-006.md`. Commit only after every
required check passes. Then report the commit SHA and keep the worktree clean. A fresh,
independent Codex Reviewer will be assigned by the main control plane.
