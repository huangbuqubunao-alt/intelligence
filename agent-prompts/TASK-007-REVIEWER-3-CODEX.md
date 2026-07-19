# TASK-007 Correction 2 — Third Independent Codex Reviewer

## Authority and isolation

You are a **fresh, independent Codex Reviewer**. You did not implement TASK-007 or either
correction. Review only this source:

- Common base: `6b4d59c882ccdcbd0e5a6069a6661e0672921a80`
- Source worktree/branch: `/Users/hua/Documents/yia-worktrees/task-007` /
  `codex/task-007-local-scoring`
- Reviewed head: `567b0f63f9cefc6c8bff43bfea0e9e156ac3a02c`
- Required parent: `d8eaeabdd2454141eeb646d9254f4a0a24626605`
- Main dynamic authority: from `/Users/hua/Documents/youtubek agent`,
  `git log -1 --format=%H -- agent-prompts/TASK-007-REVIEWER-3-CODEX.md` must resolve to the
  authorization commit and main TASK-007 must be `IN_REVIEW`.

Do not read, run checks in, modify, clean, wait on or report
`/Users/hua/Documents/yia-worktrees/task-006`. Stop on wrong main/source state, dirty source,
unexpected parent, scope expansion, lockfile change, secret, real-resource action or unexplained error.

## Write rule and expected range

Review `6b4d59c...567b0f...` and the Correction 2 range. You may write only
`handoffs/TASK-007.md`, then make one evidence commit whose sole parent is `567b0f...`.

Complete product range is exactly:

- `src/youtube_intel/scoring.py`
- `src/youtube_intel/providers/ollama.py`
- `prompts/scoring.md`
- `tests/unit/test_scoring.py`
- `tests/integration/test_ollama_provider.py`
- `tests/fixtures/scoring/**`
- `handoffs/TASK-007.md`

Correction 2 itself may change only `scoring.py`, `providers/ollama.py`, the two existing scoring tests
and the handoff. `pyproject.toml` and `uv.lock` must be identical to the common base. Do not modify
product code, tests, fixtures, dependencies, lockfiles, task status, main or source history.

## Required offline reruns

Run in the TASK-007 source worktree only:

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
git diff --check 6b4d59c882ccdcbd0e5a6069a6661e0672921a80...567b0f63f9cefc6c8bff43bfea0e9e156ac3a02c
```

Inspect sdist and wheel for `youtube_intel/migrations/001_initial.sql`. A cache miss is a blocker, not
network authority. Do not call a real Ollama endpoint (including loopback), install/start/stop Ollama,
pull models, or access media/YouTube/Cookie/remote components/ffmpeg/Vault/credentials/deletion paths.

## Independent L-09 probes

Use only temporary real SQLite/data roots and in-process Fake transport/providers.

1. **Persisted failed repair.** Make a primary response invalid and its single repair invalid. Confirm a
   request-bound `SCORING_RAW` recovery Artifact is saved with correct deterministic key, kind, retention,
   root/path/size/hash, video/provider/model/provenance binding and retryable Provider Call failure. No
   structured Artifact, summary, `SCORED` Pipeline transition or successful Job may appear. Recursively
   inspect errors/traceback for primary/repair response, prompt, URL, subtitle or absolute-path leakage.
2. **Requeued recovery.** Requeue the identical Job using that real SQLite state. Confirm it verifies the
   saved recovery Artifact and makes exactly one repair request, with no `/api/tags` preflight and no new
   primary scoring request. A valid repair must atomically write raw/structured Artifacts, successful
   Provider Call, threshold-owned summary, Pipeline CAS and Job completion. Inject each post-artifact
   database failure: successful writes must roll back while the validated recovery input remains usable.
3. **Fail closed.** Independently tamper/misbind/missing-check the recovery Artifact: content hash, path,
   request hash/key, video, provider, model and retention/provenance. It must not fabricate a result, leak
   content, issue a new primary request or silently claim a cache hit. Verify original Correction 1
   exception graph, short-read/malformed mapping, one-repair ceiling, cache identity and SQLite rollback
   regressions remain intact.

## Decision and handoff

Append commands/results, probes, AC-1–AC-3 and ADR-007 L-03–L-09 matrix, five-axis review, scope/
secret/red-line/reuse checks, unrun resource paths, P0–P3 findings and `APPROVE` or `REJECT` to the
handoff. `APPROVE` requires all offline criteria and no unresolved P0/P1. Commit the handoff only, report
SHA and leave source clean. Do not set `ACCEPTED`/`DONE`, merge or push.
