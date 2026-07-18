# TASK-007 离线实现 — Codex Implementer

## Authority and live control plane

- Source base: `main@6b4d59c882ccdcbd0e5a6069a6661e0672921a80`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-007`
- Branch: `codex/task-007-local-scoring`
- Main control plane is authoritative. This source worktree deliberately begins from
  the pre-assignment snapshot. Before writing, resolve
  `git log -1 --format=%H -- agent-prompts/TASK-007-IMPLEMENTER-CODEX.md` on `main` and
  verify that version of the task card says `IN_PROGRESS`/`Codex`.

## Goal

Implement the offline local-scoring service, strict structured parsing, sampling/cache/policy
integration and Fake-transport tests. The result must be fully testable without any running
Ollama instance or model.

## Approved scope

- `src/youtube_intel/scoring.py`
- `src/youtube_intel/providers/ollama.py`
- `prompts/scoring.md`
- `tests/unit/test_scoring.py`
- `tests/integration/test_ollama_provider.py`
- `tests/fixtures/scoring/**`
- `handoffs/TASK-007.md`

Do not modify dependencies, `pyproject.toml`, `uv.lock`, Schema/migrations, shared
config/domain/state contracts, task status, or main.

## Reuse and strict boundary

- `DIRECT`: Python 3.12 `urllib.request` and `json`, existing locked Pydantic and SQLite
  Repository contracts.
- `DIRECT-PENDING` only as a future runtime: Ollama API / `qwen3:8b`; neither may be installed,
  started, pulled, or contacted during this task.
- `REJECT`: `httpx`, an Ollama SDK, cloud tags, and any automatic service/model bootstrap.

All tests must use Fake transport or a test-local in-process substitute. Do not connect to real
`127.0.0.1:11434`, even if a local service happens to be listening. If the existing lock cannot
be used, `uv sync --locked --offline` may be tried; a cache miss is a blocker, not authority to
download packages.

## Forbidden in this phase

No Ollama installation/start/stop; no `qwen3:8b` pull; no actual model/API request; no remote
URL, cloud tag, media/YouTube, Cookie/login, remote component, ffmpeg, Vault/secret or deletion
operation. Do not add a dependency or broaden the loopback boundary.

## Required checks

1. `uv lock --check`
2. `uv run python -m pytest tests/unit/test_scoring.py`
3. `uv run python -m pytest tests/integration/test_ollama_provider.py`
4. `uv run python -m pytest`
5. `uv run mypy src`
6. `uv run ruff check .`
7. `uv run python -m youtube_intel --help`
8. `uv build --offline`
9. Confirm sdist/wheel include `youtube_intel/migrations/001_initial.sql`.
10. `git diff --check <base>...HEAD` and complete scope/secret/red-line review.

## Handoff

Record AC evidence, Fake-transport/no-real-Ollama evidence, prompt/schema versions, reuse/
license evidence, all forbidden paths not run, and final Diff scope in `handoffs/TASK-007.md`.
Commit only after all required checks pass, report the SHA, and leave the worktree clean. A fresh
independent Codex Reviewer will be assigned after the source commit is fixed on main.
