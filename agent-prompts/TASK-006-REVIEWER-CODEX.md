# TASK-006 阶段 A — Independent Codex Reviewer

## Identity and authority

You are a **fresh independent Codex Reviewer**. You did not implement TASK-006. Review only:

- Base: `6b4d59c882ccdcbd0e5a6069a6661e0672921a80`
- Source branch/worktree: `codex/task-006-local-transcription` /
  `/Users/hua/Documents/yia-worktrees/task-006`
- Reviewed implementation: `c6ff804569b376c347719296d80fbe1abf99057a`
- Main dynamic authorization: resolve `git log -1 --format=%H -- agent-prompts/TASK-006-REVIEWER-CODEX.md`
  from `/Users/hua/Documents/youtubek agent`; it must designate this exact source and `IN_REVIEW`.

The active TASK-007 Implementer is outside your scope. Do not read, run checks in, modify, wait
on, clean, or report on `/Users/hua/Documents/yia-worktrees/task-007`.

## Review scope and write rule

Review base...source. You may write only `handoffs/TASK-006.md`, then create one review-evidence
commit whose sole parent is `c6ff804...`. Do not amend the source, alter product code/tests,
dependencies/lockfiles, task status or main. Stop on a dirty source worktree, wrong branch/head,
scope expansion, secret, model/resource action, or unexplained package change.

Expected implementation range is exactly:

- `src/youtube_intel/transcription.py`
- `src/youtube_intel/providers/whisper.py`
- `tests/unit/test_transcription_policy.py`
- `tests/integration/test_whisper_provider.py`
- `tests/fixtures/audio/README.md`
- `pyproject.toml`
- `uv.lock`
- `handoffs/TASK-006.md`

## Required reruns

1. `uv lock --check`
2. `uv sync --locked` (network only for already authorized package cache/download recovery; no
   model, media or unrelated download)
3. Focused unit and integration tests from the task card
4. Full `uv run python -m pytest`
5. `uv run mypy src`, `uv run ruff check .`, CLI help
6. `uv build --offline`; inspect sdist/wheel for migration SQL
7. `git diff --check <base>...<source>` plus complete scope, secret and dependency review

Never run `mlx_whisper.transcribe`, download/load a model, invoke/install ffmpeg, download media,
make YouTube/Hugging Face calls, or use Cookie/login/remote components/Vault/credentials.

## Independent probes

### A — dependency, import and offline boundary

Verify `mlx-whisper==0.4.3` is the only new direct dependency and lock changes are its necessary
transitives. Inspect import/call paths and run a read-only/static or temporary test-local probe
that does not alter repository files, proving the Phase A adapter cannot import/call real
`mlx_whisper.transcribe`, subprocess/ffmpeg, model download or network APIs. Review fixture
provenance: it must be deterministic/local and not real media.

### B — cache and policy integrity

Independently vary each cache identity input required by ADR-007 (audio content hash, Provider,
model/revision and parameter-policy/hash) and ensure reuse only occurs for the identical request.
Probe oversize duration/audio, timeout, resource failure and malformed executor output; require safe
typed error mapping, no poisoned cache and no sensitive raw path/content disclosure.

### C — Artifact deletion confinement and recovery

Use a temporary real SQLite repository plus controlled DATA-root files. Prove success deletes only
the registered `AUDIO`/`EPHEMERAL_AUDIO` Artifact with matching hash and successful CAS mark;
reject wrong kind/retention/root/hash, missing record, stale CAS and symlink/path escape. Verify
failure/timeout/over-limit retains audio and cleanup failure cannot undo a committed transcript.

### D — phase honesty and review axes

Confirm no hidden real-model, multiprocessing, resource-baseline, ffmpeg or media claim is made;
these are deferred phases, not omissions to silently fill. Review correctness, architecture,
security/privacy, performance/resources, readability, reuse/license evidence and all TASK-006
acceptance items. Classify findings P0–P3 with file/line evidence.

## Verdict and handoff

Append commands/results, each probe, AC matrix, scope/red-line/reuse review, skipped authorized
paths, risks and `APPROVE` or `REJECT` to the handoff. `APPROVE` requires all Phase A ACs and no
unresolved P0/P1. Commit the handoff only, report SHA and leave source clean. Do not set
`ACCEPTED`/`DONE` or merge.
