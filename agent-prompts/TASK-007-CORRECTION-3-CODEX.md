# TASK-007 Correction 3 — Codex Implementer

You are the original Codex Implementer. Work only in `/Users/hua/Documents/yia-worktrees/task-007` on `codex/task-007-local-scoring`.

- Common base: `6b4d59c882ccdcbd0e5a6069a6661e0672921a80`
- Start head and required sole parent: `1d27d3bdeb8981ca85deaacd5c1cad498ef7a632`
- Main authority: `git -C '/Users/hua/Documents/youtubek agent' log -1 --format=%H -- agent-prompts/TASK-007-CORRECTION-3-CODEX.md` must resolve to the active authorization; TASK-007 is `IN_PROGRESS` with you as original Implementer.

Do not access TASK-006. Stop on dirty source, wrong parent/state, scope expansion, lockfile change, secret or any real-resource action.

P1: after initial invalid primary+repair, correction 2 saves recovery input. If its indexed recovery Artifact row is deleted, retry cannot distinguish that recovery-required state from the first request and sends a new primary request. ADR-007 L-09 requires fail-closed.

Make the smallest change using only existing Provider Call data and private code: persist a fixed, safe, request-bound recovery-required marker under existing retryable Provider Call semantics; on a later reservation bearing that marker, require the deterministic recovery Artifact. Missing/tampered/mismatched recovery state must safely produce retryable `INVALID_RESPONSE` with **zero** tags/preflight, primary or repair calls, no cache hit and no score/Pipeline/Job success. Do not store raw content in markers/errors. Present valid recovery must remain exactly one repair and atomic success/rollback.

Allowed paths: `src/youtube_intel/scoring.py`, `src/youtube_intel/providers/ollama.py`, `tests/unit/test_scoring.py`, `tests/integration/test_ollama_provider.py`, needed `tests/fixtures/scoring/**`, `handoffs/TASK-007.md`. No `state.py`, schema/migration, domain/config/prompt/dependencies/locks/task status/main/public contract changes.

Reuse decision: DIRECT existing ProviderCall `last_error_*`, Artifact index and SQLite transaction semantics; ADAPT private raw-response recovery hook. No SDK/httpx/model/service.

Run source-only, offline:

```bash
uv lock --check
uv sync --locked --offline
uv run python -m pytest tests/unit/test_scoring.py
uv run python -m pytest tests/integration/test_ollama_provider.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
uv build --offline
git diff --check 1d27d3bdeb8981ca85deaacd5c1cad498ef7a632...HEAD
git status --short
```

Inspect package migration inclusion. No real Ollama/loopback/network, model/service install/start/pull, media/YouTube/Cookie/ffmpeg/Vault/credentials or external deletion. Append RED/GREEN evidence, transport counts, SQLite artifacts/provider/pipeline/job assertions, scope/reuse/unrun paths to handoff; create one commit, leave clean; do not start Reviewer/merge/push/status-change.
