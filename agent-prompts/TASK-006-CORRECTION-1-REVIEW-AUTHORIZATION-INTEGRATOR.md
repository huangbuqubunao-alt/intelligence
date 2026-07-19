# TASK-006 Correction 1 review authorization — Status Integrator

Synchronize Correction 1 evidence and queue (do not start) a fresh independent Codex Reviewer. No product commands, source edits or TASK-007 access.

Preconditions: main `/Users/hua/Documents/youtubek agent` at `57f02d8c1bbbaa3e323aa2fe097a139cda0d464f`, empty index; TASK-006 source `/Users/hua/Documents/yia-worktrees/task-006` clean at `17afcd349827b36e5ba18fb0eab443c1ae5fb53f` with sole parent `f1c15ed6eb854a4a8ed2299bbbf89e1cb6266426`; correction range exactly its four approved paths; full task range allowed; `state.py`, Schema/migrations, dependencies/locks unchanged. Confirm `Mozhu <huangbuqubunao@gmail.com>` and `user.useConfigOnly=true`.

Stage/commit exactly these five prepared Markdown files:

1. `agent-prompts/TASK-006-CORRECTION-1-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-006-REVIEWER-2-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-006-local-transcription.md`

Prepared-content exception: main is expected to contain exactly these five unstaged/untracked paths. Record SHA-256 values, verify the combined modified/untracked path set is exactly these five, stage only them, repeat hashes after staging/before commit, and confirm staged blobs match. Any staged content, extra path/hash change, identity/source mismatch blocks: stop without cleanup/overwrite/restaging/commit.

Set TASK-006 `IN_REVIEW`, reviewer queued only, source `17afcd...` and self-reported checks recorded as unverified. The dynamic reviewer package must resolve to this new commit. Do not prewrite verdict/ACCEPTED/DONE; TASK-007 Reviewer is active, so do not start TASK-006 Reviewer until it reports final verdict. Preserve TASK-007 byte-for-byte and do not access it.

Run Git/document checks only (hashes, source parent/scope, EOF/whitespace, `git diff --check`, cached diff and post-commit scope/parent/clean). No uv/tests/build/database/model/media/network. Commit message: `docs: queue TASK-006 cleanup review`. Report all evidence, state and that TASK-007 was untouched. No Worker start, merge, push or cleanup.
