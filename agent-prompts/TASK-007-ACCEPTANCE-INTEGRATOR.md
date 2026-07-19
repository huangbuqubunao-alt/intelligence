# TASK-007 acceptance sync — Status Integrator

Control-plane only: record the fourth independent review approval and move TASK-007 to `ACCEPTED`; do not run product commands, modify source or access TASK-006.

Main must be `/Users/hua/Documents/youtubek agent` `main@6b326451dfae599df138e5f7f42c26acb283761e` with empty index. Source must be `/Users/hua/Documents/yia-worktrees/task-007` clean at `95087c115b799d6f4e1e063a0adba0a6d10352ce`, sole parent `9da12c2a6932d04b936d6ae1543acb55a72ec9dd`; review evidence only handoff. Full source range is 11 approved paths, Correction 3 is three, locks unchanged. Confirm `Mozhu <huangbuqubunao@gmail.com>` and `user.useConfigOnly=true`.

Stage/commit exactly four prepared Markdown files:

1. `agent-prompts/TASK-007-ACCEPTANCE-INTEGRATOR.md`
2. `docs/PROJECT_STATUS.md`
3. `tasks/README.md`
4. `tasks/TASK-007-local-scoring.md`

Prepared-control exception: main is expected to contain exactly these four unstaged/untracked paths. Record SHA-256, verify combined modified/untracked scope exactly, stage only them, repeat hashes after staging/before commit and compare staged blobs. Index content, extra path/hash change, identity/source mismatch blocks without cleanup/overwrite/restage/commit.

Record `95087c...` APPROVE, all AC/ADR gates and P0–P3 none; set `ACCEPTED`, but do not prewrite merge/DONE. Preserve TASK-006 byte-for-byte/no access. Git/document checks only; no uv/tests/build/database/model/media/network. Commit `docs: accept TASK-007 recovery correction`. Report chain/scope/checks; do not start Integrator, merge/push/cleanup.
