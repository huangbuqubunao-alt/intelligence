# TASK-006 closure — Status Integrator

Close only the already-integrated TASK-006. This is a control-plane-only task.
Do not run product commands, modify source, merge, push, clean worktrees, or access the
retained TASK-007 source worktree.

## Fixed inputs

- Main repository: `/Users/developer/Documents/youtubek agent`
- Required main: `main@fd9a07462a0596e1c5d4c67c200c3a7f2561fea1`
- Merge parents, in exact order:
  1. `7d18ecffc61fc0def974ce07ee9dc1ceeb4bf305`
  2. `f00209c8018a9e728d9f6509f0ae70067fa33676`
- Retained source worktree: `/Users/developer/Documents/yia-worktrees/task-006`
- Retained source branch/head:
  `codex/task-006-local-transcription@f00209c8018a9e728d9f6509f0ae70067fa33676`
- Git identity: `Mozhu <maintainer@example.invalid>`
- `user.useConfigOnly=true`

Before staging, verify main is the exact merge commit with an empty index and no paths
other than the prepared files below. Verify the source worktree is clean at the fixed
branch/head and the accepted source is an ancestor of the merge. The merge first-parent
range must be exactly:

- `handoffs/TASK-006.md`
- `pyproject.toml`
- `src/youtube_intel/providers/whisper.py`
- `src/youtube_intel/transcription.py`
- `tests/fixtures/audio/README.md`
- `tests/integration/test_whisper_provider.py`
- `tests/unit/test_transcription_policy.py`
- `uv.lock`

Confirm the merge evidence already records all offline gates passing: lock check, locked
offline sync, focused `11/12`, full `305`, mypy, Ruff, CLI, offline build and sdist/wheel
migration inclusion. Do not rerun those checks.

## Prepared files and commit

The prepared-control exception applies. Main is expected to contain exactly these five
unstaged modified/untracked Markdown files:

1. `agent-prompts/TASK-006-CLOSURE-INTEGRATOR.md`
2. `docs/PROJECT_STATUS.md`
3. `handoffs/TASK-006.md`
4. `tasks/README.md`
5. `tasks/TASK-006-local-transcription.md`

Record SHA-256 for all five before staging. Verify combined scope, complete Diff, LF at
EOF, trailing whitespace and `git diff --check`, including the untracked prompt. The
prepared card/index/status/handoff must already consistently state:

- TASK-006=`DONE`;
- merge=`fd9a07462a0596e1c5d4c67c200c3a7f2561fea1`;
- TASK-007 remains `DONE`;
- TASK-008/TASK-009 remain `BLOCKED/UNASSIGNED`;
- no real model, ffmpeg, transcription, media, network, Vault, credential or real-file
  action has been authorized.

Verify rather than edit the prepared content. Stage only the five files, repeat hashes and
compare staged blobs, run `git diff --cached --check`, and confirm exact cached scope with
no unstaged content. Any extra path, pre-existing index content, changed hash, identity,
source, merge, scope, or status mismatch is a blocker: stop without cleanup, overwrite,
restage, or commit.

Commit:

```text
docs: close TASK-006 after integration
```

After commit verify it has sole parent
`fd9a07462a0596e1c5d4c67c200c3a7f2561fea1`, exact five-file scope, and main/source
worktrees are clean with the retained source unchanged.

Report base/head, identity, committed files, merge/source/first-parent evidence, final
TASK-006/TASK-007 and downstream status, checks, post-commit cleanliness, verdict and
remaining risks. Do not start another Worker.
