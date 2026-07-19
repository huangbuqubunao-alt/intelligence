# TASK-007 Correction 2 — Codex Implementer

## Authority and isolation

You are the **original Codex Implementer** for this correction only.

- Common base: `6b4d59c882ccdcbd0e5a6069a6661e0672921a80`
- Source worktree/branch: `/Users/hua/Documents/yia-worktrees/task-007` /
  `codex/task-007-local-scoring`
- Start head: `d8eaeabdd2454141eeb646d9254f4a0a24626605`
- Required sole parent for your correction commit: `d8eaeabdd2454141eeb646d9254f4a0a24626605`
- Main dynamic authority: from `/Users/hua/Documents/youtubek agent`,
  `git log -1 --format=%H -- agent-prompts/TASK-007-CORRECTION-2-CODEX.md` must resolve to the
  current authorization commit. Main TASK-007 must be `IN_PROGRESS` with Codex as the original
  Implementer. The source task card is a frozen historical snapshot and is not the live status.

Do not read, run checks in, modify, clean, wait on, or report
`/Users/hua/Documents/yia-worktrees/task-006`. Stop on wrong source/main state, dirty source,
unexpected parent, scope expansion, lockfile change, secret, real-resource action, or an
unexplained test failure.

## P1 to close — ADR-007 L-09 recovery

Correction 1 persists successful scoring, but its provider discards a received primary raw response
when that response is invalid and the one permitted repair also fails. A requeued Job therefore sends
both a new primary request and a new repair. This violates ADR-007 L-09.

Implement the smallest private Adapter/application-service change that:

1. Safely transfers a received primary raw response to the repository-backed service even when the
   repair attempt fails; it must be bound to the existing request hash and not become a new public
   free-form contract.
2. Persists that primary response through existing `ArtifactWrite`, `ProviderCallRequest`, reservation
   and failure semantics as `SCORING_RAW` / `RAW_RESPONSE_30D`, while keeping the Provider Call
   retryable. Do not write a structured Artifact, summary, Pipeline `SCORED` state or successful Job
   until a valid repaired result exists.
3. On a requeued identical request, verifies the recovery raw Artifact fully (root/path, size, hash,
   kind, deterministic key, request/video/provider/model/provenance) before reuse. A valid recovery
   Artifact must result in exactly one repair request and **no new primary scoring request**. It must
   not require a real service or default HTTP transport.
4. Treats missing, tampered or mismatched recovery state as a safe failure under existing retry
   semantics: no score fabrication, no unsafe cache hit and no untrusted content in message, args,
   cause, context or traceback.
5. Preserves existing one-repair ceiling, threshold-owned final decision, atomic `complete_stage`
   success path and Correction 1 regressions.

## Allowed scope

Only these paths may change:

- `src/youtube_intel/scoring.py`
- `src/youtube_intel/providers/ollama.py`
- `tests/unit/test_scoring.py`
- `tests/integration/test_ollama_provider.py`
- `tests/fixtures/scoring/**` only if genuinely required
- `handoffs/TASK-007.md`

Forbidden: `state.py`, any Schema/migration, `domain.py`, config/settings, prompts, dependencies,
`pyproject.toml`, `uv.lock`, main/task-status files, public-contract expansion, real resources or
unrelated refactors.

## Reuse decision

`DIRECT`: existing SQLite `ProviderCall`/Artifact/`complete_stage` contracts and Python standard
library HTTP/JSON; `ADAPT`: the existing private Ollama raw-response handoff. Do not add an Ollama SDK,
`httpx`, models or services.

## Required evidence and commands

Add focused unit and real-temporary-SQLite integration regressions for failed primary+repair
persistence, a requeued recovery repair with no repeated primary request, successful atomic recovery,
and fail-closed tamper/mismatch cases. Record exact Fake transport calls and all relevant Artifact/
Provider/Pipeline/Job assertions in the handoff.

Run in this source worktree only:

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
git diff --check d8eaeabdd2454141eeb646d9254f4a0a24626605...HEAD
git status --short
```

Verify both sdist and wheel include `youtube_intel/migrations/001_initial.sql`; do not commit build
output. A cache miss is a blocker, not permission to network. Do not call actual Ollama (even
loopback), install/start/stop services, pull models, or access media/YouTube/Cookie/remote components/
ffmpeg/Vault/credentials/deletion paths.

Append implementation evidence, Red/Green P1 proof, reuse/license evidence, exact scope, unrun paths
and remaining risks to `handoffs/TASK-007.md`. Make one correction commit with the required sole parent,
leave the source clean, and report its SHA. Do not start a Reviewer, merge, push or change task status.
