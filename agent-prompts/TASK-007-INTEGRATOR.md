# TASK-007 — Product Integrator

Integrate only accepted TASK-007 source into main.

- Acceptance anchor: `65f87c197cbc64ed18280bed99457244ebefa73e`
- Execution base: dynamically resolve `git log -1 --format=%H -- agent-prompts/TASK-007-INTEGRATOR.md` in `/Users/developer/Documents/youtubek agent`; it must be the authorization commit and TASK-007 must remain `ACCEPTED`.
- Source: `/Users/developer/Documents/yia-worktrees/task-007`, branch `codex/task-007-local-scoring`, head `95087c115b799d6f4e1e063a0adba0a6d10352ce`, clean.

Do not access TASK-006 worktree. Stop on dirty worktree/index, wrong main/source chain, scope/lock difference, conflicts, secret or real-resource action. Do not rewrite source, rebase, cherry-pick, push or clean source/worktrees.

Before merge, verify acceptance evidence `95087c...` has sole parent `9da12c...`, source is accepted, full first-parent product scope is exactly:

- `handoffs/TASK-007.md`
- `prompts/scoring.md`
- `src/youtube_intel/providers/ollama.py`
- `src/youtube_intel/scoring.py`
- `tests/fixtures/scoring/**` (five approved fixtures)
- `tests/integration/test_ollama_provider.py`
- `tests/unit/test_scoring.py`

`pyproject.toml`/`uv.lock` must not differ. Perform a non-fast-forward merge with no code edits; stop on conflict. Stage only the merge result, use `git diff --cached --check`, and verify first-parent range exactly matches the paths above.

Run in main after merge, offline only:

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
```

Inspect sdist/wheel for `youtube_intel/migrations/001_initial.sql`; remove no files and do not commit ignored build output. Confirm merge has exactly two parents, source/evidence are ancestors, source stays clean/retained, main clean and no unexpected files. Do not change TASK-007 to DONE—that needs a separate closure control commit. No real Ollama/loopback/network/model/service/media/YouTube/Cookie/ffmpeg/Vault/credential actions.

Report execution base/source/merge SHA and parents, pre/post scope, every check, source retention, skipped resources and remaining real-resource risks.
