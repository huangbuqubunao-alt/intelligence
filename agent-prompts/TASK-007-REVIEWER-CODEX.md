# TASK-007 离线实现 — Independent Codex Reviewer

## Identity and authority

You are a **fresh independent Codex Reviewer**. You did not implement TASK-007. Review only:

- Base: `6b4d59c882ccdcbd0e5a6069a6661e0672921a80`
- Source branch/worktree: `codex/task-007-local-scoring` /
  `/Users/hua/Documents/yia-worktrees/task-007`
- Reviewed implementation: `258358fcd5227e144c9294beafdf7ec6e2feea63`
- Main dynamic authorization: resolve `git log -1 --format=%H -- agent-prompts/TASK-007-REVIEWER-CODEX.md`
  from `/Users/hua/Documents/youtubek agent`; it must designate this exact source and `IN_REVIEW`.

TASK-006 is undergoing a separate review and is outside scope. Do not read, run checks in,
modify, wait on, clean, or report on `/Users/hua/Documents/yia-worktrees/task-006`.

## Review scope and write rule

Review base...source. You may write only `handoffs/TASK-007.md`, then create one review-evidence
commit whose sole parent is `258358f...`. Do not amend the source, alter product code/tests,
dependencies/lockfiles, task status or main. Stop on a dirty source worktree, wrong branch/head,
scope expansion, secret, real-service action, or unexplained lockfile change.

Expected product range is only:

- `src/youtube_intel/scoring.py`
- `src/youtube_intel/providers/ollama.py`
- `prompts/scoring.md`
- `tests/unit/test_scoring.py`
- `tests/integration/test_ollama_provider.py`
- `tests/fixtures/scoring/**`
- `handoffs/TASK-007.md`

## Required reruns

1. `uv lock --check`
2. `uv sync --locked --offline`; a cache miss is a blocker, not network authority
3. Focused scoring unit and Fake-provider integration tests from the task card
4. Full `uv run python -m pytest`
5. `uv run mypy src`, `uv run ruff check .`, CLI help
6. `uv build --offline`; inspect sdist/wheel for migration SQL
7. `git diff --check <base>...<source>` plus complete scope, secret and no-dependency review

Do not call a real Ollama endpoint, even loopback; do not install/start/stop Ollama, pull
`qwen3:8b`, access cloud tags/remote URLs, use ffmpeg/media/YouTube/Cookie/remote components, or
touch Vault/credentials/deletion paths.

## Independent probes

### A — offline HTTP and response safety

Prove all tests use injected Fake/test-local transport and cannot reach a listening
`127.0.0.1:11434`. Check loopback URL validation, fixed `/api/tags` and `/api/generate` paths,
bounded reads, response closing, `stream=false`, `think=false`, JSON Schema format, strict JSON
parsing, exactly one repair call, and error mapping/redaction for timeout, malformed/oversized
payload, 401/403, 429 and 5xx. No raw prompt/transcript/response/absolute path may escape.

### B — sampling, request hashes and policy truth

Independently test head/body/tail boundaries and Unicode character limits; vary title/channel/date/
duration/language/truncated description, full transcript hash, sample version/content, model,
temperature, output limit, prompt/schema version and operation to verify cache/request separation.
Check the exact threshold boundary and confirm `final_should_summarize` is derived from score, not
the model's suggestion; disagreement must be recorded without overwriting the model result.

### C — real SQLite completion and cache recovery

Use a temporary real SQLite repository with only allowed test-local inputs. Confirm raw response,
structured result, Provider call, `ScoringSummaryWrite`, Pipeline CAS and Job success commit
atomically; inject a post-write failure and require full rollback. Repeated identical input should
reuse verified cache without a second Fake call; altered request/model/prompt/schema must not reuse.

### D — scope and phase honesty

Confirm no `httpx`/Ollama SDK/dependency or lockfile alteration, no auto bootstrap/pull, and no
claim that Fake coverage validates a real model. Review correctness, architecture, security/privacy,
performance/resources, readability, reuse/license evidence and all ACs/ADR-007 L-03/L-05–L-09.
Classify findings P0–P3 with file/line evidence.

## Verdict and handoff

Append commands/results, each probe, AC/ADR matrix, scope/red-line/reuse review, all unrun
resource paths, risks and `APPROVE` or `REJECT` to the handoff. `APPROVE` requires all offline
ACs and no unresolved P0/P1. Commit the handoff only, report SHA and leave source clean. Do not
set `ACCEPTED`/`DONE` or merge.
