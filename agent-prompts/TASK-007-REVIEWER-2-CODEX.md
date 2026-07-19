# TASK-007 Correction 1 — Second Independent Codex Reviewer

## Authority and isolation

You are a **fresh, independent Codex Reviewer**. You did not implement TASK-007 or its
Correction 1. Review only this fixed source:

- Common base: `6b4d59c882ccdcbd0e5a6069a6661e0672921a80`
- Source worktree/branch: `/Users/hua/Documents/yia-worktrees/task-007` /
  `codex/task-007-local-scoring`
- Reviewed head: `f46881bc4a8ca0fda4d5ef7006b372bc566cff97`
- Required parent: `266c488c17fc82cb648053b5e1066211a7bea9a9`
- Main dynamic authority: from `/Users/hua/Documents/youtubek agent`,
  `git log -1 --format=%H -- agent-prompts/TASK-007-REVIEWER-2-CODEX.md` must resolve to the
  current authorization commit and main TASK-007 must be `IN_REVIEW`.

Do not read, run checks in, modify, clean, wait on, or report
`/Users/hua/Documents/yia-worktrees/task-006`. Stop on wrong main/source state, dirty source,
unexpected parent, scope expansion, lockfile change, secret, real-resource action, or an
unexplained error.

## Write rule and expected range

Review the complete `base...source` range and Correction range. You may write only
`handoffs/TASK-007.md`, then make one evidence commit whose sole parent is `f46881bc...`.
Do not modify product code, tests, fixtures, dependencies, lockfiles, task status, main, or the
source branch history.

Complete product range is exactly:

- `src/youtube_intel/scoring.py`
- `src/youtube_intel/providers/ollama.py`
- `prompts/scoring.md`
- `tests/unit/test_scoring.py`
- `tests/integration/test_ollama_provider.py`
- `tests/fixtures/scoring/**`
- `handoffs/TASK-007.md`

Correction 1 itself may change only `scoring.py`, `providers/ollama.py`, the two existing scoring
tests, and the handoff. `pyproject.toml` and `uv.lock` must be identical to the common base.

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
git diff --check 6b4d59c882ccdcbd0e5a6069a6661e0672921a80...f46881bc4a8ca0fda4d5ef7006b372bc566cff97
```

Inspect sdist and wheel for `youtube_intel/migrations/001_initial.sql`. A cache miss is a blocker,
not network authority. Do not call any real Ollama endpoint (including loopback), install/start/
stop Ollama, pull models or cloud tags, or access media/YouTube/Cookie/remote components/ffmpeg/
Vault/credentials/deletion paths.

## Independent probes

### A — complete public exception graph

With injected in-process Fake transport only, independently exercise invalid primary and repair
payloads containing a distinctive sensitive sentinel; missing/non-string/oversized response,
invalid UTF-8/JSON/schema, `IncompleteRead`, timeout, 401/403, 429 and 5xx. Verify error code,
retryability, `video_id`, stage and exactly-one-repair behavior. Recursively inspect `message`,
`args`, `__cause__`, `__context__`, traceback-linked exceptions and reachable exception objects:
no raw response, transcript, prompt, URL or absolute path may be retained. Confirm every response
is closed and no Fake invokes default urllib/network transport.

### B — real SQLite success, recovery and rollback

Use temporary real SQLite/data roots and only test-local Fake providers. Independently prove one
`TRANSCRIPT_READY -> SCORED` completion atomically records `SCORING_RAW`/`RAW_RESPONSE_30D`,
`SCORING_STRUCTURED`/`LONG_LIVED`, successful Provider Call bound to raw Artifact,
`ScoringSummaryWrite`, Pipeline CAS and Job success. Assert model suggestion never overrides the
threshold-derived final decision. Inject failures after artifacts, Provider Call, scoring summary
and Pipeline updates: database records must roll back and failure handling must remain safe.

Then reset/retry with the same verified request and prove no second Fake provider call; alter each
frozen request dimension (normalized input, model, prompt, schema, operation) and prove no reuse.
Tamper with artifact/hash/provenance and require fail-closed behavior without a provider call.

### C — architecture, cache and red-line integrity

Confirm Provider code still does not write SQLite directly; Repository-backed application service
uses only the established named Protocol/Repository types, `ProviderCallRequest`,
`ProviderCallCompletion`, `ArtifactWrite`, `ScoringSummaryWrite` and `complete_stage` semantics.
Check raw-response lifetime is one-shot/bound to request and not a public free-form surface.
Review Artifact path/hash boundary, failure/lease semantics, duplicate cache behavior, resource
bounds and no silent weakening of original sample/policy tests. Recheck no SDK/httpx/dependency/
lock/Schema/domain/config change and reuse/license evidence remains `DIRECT` standard library plus
existing SQLite/locked dependencies.

## Decision and handoff

Append commands/results, Probe A–C evidence, AC-1–AC-3 and ADR-007 L-03–L-09 matrix, five-axis
review, complete scope/secret/red-line/reuse checks, unrun resource paths, P0–P3 findings and
`APPROVE` or `REJECT` to `handoffs/TASK-007.md`. `APPROVE` requires all offline criteria and no
unresolved P0/P1. Commit the handoff only, report SHA, and leave source clean. Do not set
`ACCEPTED`/`DONE` or merge.
