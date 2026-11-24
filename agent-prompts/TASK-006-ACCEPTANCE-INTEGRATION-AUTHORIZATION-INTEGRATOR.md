# TASK-006 acceptance / final integration authorization sync

Role: Status Integrator. Work only in `/Users/developer/Documents/youtubek agent`.

This is a control-plane-only task. Record the fourth independent Reviewer approval, move
TASK-006 to `ACCEPTED`, and authorize the separate Product Integrator packet. Do not run
product commands, modify or merge source, start another Worker, push, clean worktrees, or
access the TASK-007 source worktree.

## Fixed inputs

- Required main: `main@3a6d0c38b0869622581e4f763371147c6c30d2d9`
- Git identity: `Mozhu <maintainer@example.invalid>`
- `user.useConfigOnly=true`
- Source worktree: `/Users/developer/Documents/yia-worktrees/task-006`
- Source branch: `codex/task-006-local-transcription`
- Accepted review evidence: `f00209c8018a9e728d9f6509f0ae70067fa33676`
- Reviewed Correction 3: `548338978b8656db0c650be276f847850af940a1`
- Original task base: `6b4d59c882ccdcbd0e5a6069a6661e0672921a80`

Before staging, verify:

1. main and source branch/HEAD/identity are exact and both worktrees are clean except for the
   prepared files listed below on main; the initial index is empty.
2. `f00209c...` has sole parent `548338978...` and changes only
   `handoffs/TASK-006.md`.
3. `548338978...` has sole parent
   `66f0b31023c290d76e2c14bea72d1cc103cc27c7`; Correction 3 changes exactly:
   - `handoffs/TASK-006.md`
   - `src/youtube_intel/providers/whisper.py`
   - `src/youtube_intel/transcription.py`
   - `tests/integration/test_whisper_provider.py`
   - `tests/unit/test_transcription_policy.py`
4. The full `6b4d59c...f00209c...` source range contains exactly these eight approved
   paths:
   - `handoffs/TASK-006.md`
   - `pyproject.toml`
   - `src/youtube_intel/providers/whisper.py`
   - `src/youtube_intel/transcription.py`
   - `tests/fixtures/audio/README.md`
   - `tests/integration/test_whisper_provider.py`
   - `tests/unit/test_transcription_policy.py`
   - `uv.lock`
5. Reviewer evidence records `APPROVE`, no P0/P1/P2/P3, focused `11/12`, full `274`,
   mypy, Ruff, CLI, locked offline sync, offline build, migration packaging, fixed Diff,
   cache/API and temporary SQLite/Fake cleanup probes all passing.
6. TASK-007 remains `DONE`. Do not read, inspect, hash, or operate its retained source
   worktree.

## Prepared files and commit

The prepared-control exception applies. The main worktree is expected to contain exactly
these five unstaged modified/untracked Markdown files:

1. `agent-prompts/TASK-006-ACCEPTANCE-INTEGRATION-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-006-INTEGRATOR.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-006-local-transcription.md`

Record SHA-256 for all five before staging. Inspect the complete modified/untracked scope,
line endings, EOF, and `git diff --check`, including both untracked prompt files. Confirm:

- TASK-006 is consistently `ACCEPTED`, with source/review SHA and Reviewer verdict.
- Product Integrator is authorized but not started.
- No merge SHA or `DONE` is prewritten.
- TASK-007 remains `DONE`.
- Real model, ffmpeg, media, YouTube, network, Vault, credential and real deletion
  restrictions remain unchanged.

Stage only the five files. Recompute file hashes after staging and compare staged blob
contents. Run `git diff --cached --check`; verify exact cached scope and no unstaged content.
Any extra path, changed hash, conflicting content, identity/source mismatch, or concurrent
change is a blocker: stop without cleanup, overwrite, restage, or commit.

Commit:

```text
docs: accept and authorize TASK-006 integration
```

After commit verify:

- the commit has sole parent `3a6d0c38b0869622581e4f763371147c6c30d2d9`;
- committed scope is exactly the five files;
- `git log -1 --format=%H -- agent-prompts/TASK-006-INTEGRATOR.md` equals the new commit;
- main and source worktrees are clean and source HEAD is unchanged.

Do not start the Product Integrator. Report base/head, identity, committed files, checks,
TASK-006 source/review/status, dynamic integration authorization, TASK-007 status,
post-commit cleanliness, verdict and remaining risks.
