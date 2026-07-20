# TASK-006 Correction 3 — Fourth Independent Codex Reviewer

You are a fresh independent Codex Reviewer. You did not implement TASK-006 or perform any of
its earlier reviews. Review only `/Users/hua/Documents/yia-worktrees/task-006` on branch
`codex/task-006-local-transcription`.

## Authority and isolation

- Common base: `6b4d59c882ccdcbd0e5a6069a6661e0672921a80`.
- Reviewed head: `548338978b8656db0c650be276f847850af940a1`; its sole parent must be
  `66f0b31023c290d76e2c14bea72d1cc103cc27c7`.
- Main authority: from `/Users/hua/Documents/youtubek agent`,
  `git log -1 --format=%H -- agent-prompts/TASK-006-REVIEWER-4-CODEX.md` must resolve to
  the active authorization commit, and main TASK-006 must be `IN_REVIEW`.
- Source worktree must be clean before review. Stop on wrong branch, head, parent, state,
  scope, dependency/lockfile change after `66f0b310...`, secret, or any unapproved resource
  action. The initial TASK-006 range already contains its approved `pyproject.toml` and
  `uv.lock` additions.

TASK-007 is closed and outside this task. Do not read, run checks in, modify, clean, wait on,
or report on `/Users/hua/Documents/yia-worktrees/task-007`.

## Scope and write rule

Review the full `base...source` range. Correction 3 may change only:

- `src/youtube_intel/transcription.py`
- `src/youtube_intel/providers/whisper.py`, limited to the existing cache-key call site
- `tests/unit/test_transcription_policy.py`
- `tests/integration/test_whisper_provider.py`
- `handoffs/TASK-006.md`

You may write only `handoffs/TASK-006.md`, then create one review-evidence commit with
`548338978b8656db0c650be276f847850af940a1` as its sole parent. Do not amend source, modify
product code/tests, dependencies/lockfiles, Schema/migrations, `state.py`, task status, main,
or source history. Do not merge, push, or clean any worktree.

## Required offline reruns

Run only in the TASK-006 source worktree:

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
git diff --check 6b4d59c882ccdcbd0e5a6069a6661e0672921a80...548338978b8656db0c650be276f847850af940a1
```

Inspect the generated sdist and wheel for `youtube_intel/migrations/001_initial.sql`.
Offline cache miss is a blocker, not network authority. Never download, import, or load a
Whisper model; invoke/install ffmpeg; run transcription; access media, YouTube, network,
Cookie, remote components, Vault, credentials, or real files.

## Independent probes

Use only synthetic audio and temporary real SQLite/DATA roots. Do not alter repository files.

1. **Language cache identity.** With one shared cache and otherwise identical input, independently
   prove `None`, `"en"`, and `"zh"` produce distinct stable cache keys and do not reuse another
   hint's result; repeated requests with the identical hint must hit the existing cache. Confirm
   executor calls receive the matching existing `WhisperDecodePolicy.language_hint`.
2. **Hard-to-omit API.** Inspect and exercise `build_transcription_cache_key()` to prove
   `language_hint` is required, keyword-only, has no default, and is included in the deterministic
   JSON hash. Recheck the existing `None` and whitespace-only policy behavior. Confirm no new
   public Adapter method parameter, normalization, or executor behavior was introduced.
3. **Provider scope.** Prove Correction 3 changes `providers/whisper.py` only at the authorized
   cache-key call site. Recheck Fake-only construction, timeout/resource/error mapping, and the
   absence of model loading, download, media, subprocess, ffmpeg, or network behavior.
4. **Unified cleanup result.** Through Fake and temporary real SQLite repositories, require wrong
   kind, non-DATA root, wrong retention, and already-deleted input to return
   `INDEX_CONFLICT` before physical deletion, preserve indexed and external files, leave
   `deleted_at` unchanged, and disclose no path.
5. **Cleanup regression matrix.** Recheck unknown, missing, stale, hash mismatch, absolute/`..`
   escape, DATA-root escape, symlink paths, valid deletion, and final post-unlink CAS race.
   Preserve the existing read/verify/path/hash/unlink/CAS order; require no reservation, Schema
   change, or exactly-once claim.

Review TASK-006 ACs, applicable ADR-007 L-01--L-15 boundaries, correctness, readability,
architecture, security/privacy, performance/resources, scope, red lines, reuse, and licensing.
Tests passing alone are not approval.

## Handoff and verdict

Append commands/results, every probe, AC/ADR matrix, five-axis review, scope/red-line/reuse
review, skipped unauthorized paths, P0--P3 findings, and `APPROVE` or `REJECT` to the handoff.
`APPROVE` requires no unresolved P0/P1. Commit the handoff only; leave source clean and do not
set `ACCEPTED` or `DONE`.
