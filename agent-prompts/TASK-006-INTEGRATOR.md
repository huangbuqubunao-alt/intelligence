# TASK-006 — Product Integrator

Integrate only the accepted TASK-006 source into main.

## Fixed inputs

- Acceptance anchor: `3a6d0c38b0869622581e4f763371147c6c30d2d9`
- Execution base: dynamically resolve
  `git log -1 --format=%H -- agent-prompts/TASK-006-INTEGRATOR.md` in
  `/Users/hua/Documents/youtubek agent`. It must equal current main HEAD, be the
  single-parent acceptance/authorization commit, and TASK-006 must be `ACCEPTED`.
- Source worktree: `/Users/hua/Documents/yia-worktrees/task-006`
- Source branch: `codex/task-006-local-transcription`
- Accepted source/review evidence: `f00209c8018a9e728d9f6509f0ae70067fa33676`
- Reviewed Correction 3: `548338978b8656db0c650be276f847850af940a1`
- Original source base: `6b4d59c882ccdcbd0e5a6069a6661e0672921a80`
- Git identity: `Mozhu <huangbuqubunao@gmail.com>` with
  `user.useConfigOnly=true`

Do not access the retained TASK-007 source worktree. Stop on dirty worktree/index, wrong
branch/HEAD/parent chain, scope mismatch, conflict, secret, unexpected file, or any
operation requiring a real resource. Do not rewrite source, rebase, cherry-pick, amend,
push, clean worktrees, or make integration-time fixes.

## Pre-merge gates

Verify:

1. main and source are clean and their branches/HEADs match the fixed inputs.
2. `f00209c...` has sole parent `548338978...`, changes only
   `handoffs/TASK-006.md`, records `APPROVE`, no P0/P1/P2/P3, and is the source
   branch HEAD.
3. `548338978...` has sole parent `66f0b310...`; Correction 3 changes exactly:
   - `handoffs/TASK-006.md`
   - `src/youtube_intel/providers/whisper.py`
   - `src/youtube_intel/transcription.py`
   - `tests/integration/test_whisper_provider.py`
   - `tests/unit/test_transcription_policy.py`
4. The full `6b4d59c...f00209c...` product range is exactly:
   - `handoffs/TASK-006.md`
   - `pyproject.toml`
   - `src/youtube_intel/providers/whisper.py`
   - `src/youtube_intel/transcription.py`
   - `tests/fixtures/audio/README.md`
   - `tests/integration/test_whisper_provider.py`
   - `tests/unit/test_transcription_policy.py`
   - `uv.lock`
5. The direct dependency change remains only approved
   `mlx-whisper>=0.4.3,<0.5`, resolved to `mlx-whisper==0.4.3`, plus necessary
   transitive dependencies. No model asset, media, secret, credential, or generated
   artifact is tracked.
6. TASK-006 is `ACCEPTED` and TASK-007 remains `DONE`.

## Merge and verification

Perform a non-fast-forward merge with no source edits. Stop on any conflict. Before
creating the merge commit, verify the staged merge result is exactly the eight approved
paths above and run:

```bash
git diff --cached --check
```

Run the following in main, offline only:

```bash
uv lock --check
uv sync --locked --offline
uv run python -m pytest tests/unit/test_transcription_policy.py
uv run python -m pytest tests/integration/test_whisper_provider.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
uv build --offline
```

If an offline cache miss occurs, stop and report it; this packet does not authorize
network access. Inspect both sdist and wheel for
`youtube_intel/migrations/001_initial.sql`. Do not delete pre-existing ignored files or
commit ignored build output.

Create the merge commit only after all gates pass. Verify:

- the merge has exactly two parents: execution base first and `f00209c...` second;
- `f00209c...` and `548338978...` are ancestors of the merge;
- first-parent Diff is exactly the eight approved paths;
- TASK-006 remains `ACCEPTED`; do not mark it `DONE`;
- TASK-007 remains `DONE`;
- main and retained source worktrees are clean and the source branch/HEAD is preserved.

No Whisper model download/load, ffmpeg, real transcription, media/YouTube download,
Cookie/login, remote component, network, Vault, credential, or real-file deletion is
authorized. Preserve the accepted post-unlink/final-CAS at-most-once risk; do not claim
exactly-once cleanup.

Report execution base, source and merge SHA/parents, pre/post scope, each check, package
evidence, unexpected files, source retention, skipped resources, verdict and remaining
risks.
