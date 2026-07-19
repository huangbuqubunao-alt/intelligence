# TASK-007 Correction 3 — Fourth Independent Codex Reviewer

You are a fresh independent Codex Reviewer. Review only `/Users/hua/Documents/yia-worktrees/task-007` on `codex/task-007-local-scoring`.

- Common base `6b4d59c882ccdcbd0e5a6069a6661e0672921a80`; reviewed head `9da12c2a6932d04b936d6ae1543acb55a72ec9dd`; required sole parent `1d27d3bdeb8981ca85deaacd5c1cad498ef7a632`.
- Dynamic authority: `git -C '/Users/hua/Documents/youtubek agent' log -1 --format=%H -- agent-prompts/TASK-007-REVIEWER-4-CODEX.md` resolves to the authorization commit; main TASK-007=`IN_REVIEW`.

Do not access TASK-006. Stop on wrong state/parent, dirty source, scope/lock change, secret or real-resource action. Review full base...source. Correction 3 can change only `scoring.py`, `providers/ollama.py`, two scoring tests, required fixtures and handoff; actual correction range is expected `scoring.py`, unit test and handoff. You may write only `handoffs/TASK-007.md`, then one evidence commit with sole parent `9da12c...`; do not modify code/tests/deps/locks/status/main/history.

Run source-only/offline:

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
git diff --check 6b4d59c882ccdcbd0e5a6069a6661e0672921a80...9da12c2a6932d04b936d6ae1543acb55a72ec9dd
```

Inspect sdist/wheel migration inclusion. No real Ollama (including loopback), network/model/service install/start/pull, media/YouTube/Cookie/ffmpeg/Vault/credentials/deletion.

With temporary real SQLite/data roots and in-process Fake transport, independently prove:

1. failed primary+repair persists a safe request-bound recovery marker and raw Artifact with no structured/summary/Pipeline/Job success;
2. valid recovery requeue validates it, makes exactly one repair and no tags/preflight/primary, then atomically succeeds; post-artifact rollback keeps recovery usable;
3. delete the **indexed recovery Artifact row**, then requeue: marker must force safe retryable `INVALID_RESPONSE`, with zero Fake transport calls, no cache hit/score/Pipeline/Job success. Repeat for missing file and provenance/hash/model mismatch; recursively inspect error graph for raw response/prompt/URL/path leakage;
4. original Correction 1/2 regressions, threshold decision, cache identity, one-repair limit and redaction remain unchanged.

Append checks/probes, AC-1–AC-3 and ADR-007 L-03–L-09 matrix, five-axis/scope/red-line/reuse review, skipped paths, P0–P3 and verdict. APPROVE requires no P0/P1. Commit handoff only, clean source; no ACCEPTED/DONE/merge/push.
