# TASK-007 Correction 3 review authorization — Status Integrator

Control-plane only; do not run product commands or access TASK-006.

Main must be `/Users/developer/Documents/youtubek agent` `main@5cb2a0d3ce5bc9f883e83e4861fc528a92a1f884`, empty index. Source must be `/Users/developer/Documents/yia-worktrees/task-007` clean at `9da12c2a6932d04b936d6ae1543acb55a72ec9dd`, sole parent `1d27d3bdeb8981ca85deaacd5c1cad498ef7a632`; Correction 3 three paths, full base range 11 allowed paths, locks unchanged. Confirm identity `Mozhu <maintainer@example.invalid>` and `user.useConfigOnly=true`.

Stage/commit exactly five prepared Markdown files:

1. `agent-prompts/TASK-007-CORRECTION-3-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-007-REVIEWER-4-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-007-local-scoring.md`

Prepared-control exception: main is expected to have exactly these five unstaged/untracked paths. Record SHA-256, verify combined modified/untracked set exactly, stage only them, repeat hashes after staging/before commit and verify staged blobs. Existing index content, extra path/hash change, identity/source mismatch blocks without cleanup/overwrite/restaging/commit.

Set TASK-007 `IN_REVIEW`, record source/evidence/self-reported checks as unverified, and dynamically authorize a fresh Reviewer. Do not prewrite verdict/ACCEPTED/merge/DONE; preserve TASK-006 byte-for-byte and never access it. Git/document checks only; no uv/tests/build/database/model/media/network. Commit `docs: authorize TASK-007 recovery marker review`. Report chain/scope/checks; do not start Worker, merge/push/cleanup.
