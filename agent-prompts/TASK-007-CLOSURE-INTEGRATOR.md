# TASK-007 closure — Status Integrator

Close only the already-integrated TASK-007; do not run product commands or access TASK-006.

Main `/Users/hua/Documents/youtubek agent` must be `main@3d49ecaf31a4ab800d6a58b5b44f815ab830a06c`, clean index. Verify merge has exactly parents `7b33f6fd73ee5ab7019a7647d71a3b5e78b99e35` and `95087c115b799d6f4e1e063a0adba0a6d10352ce`, the accepted source is an ancestor, and merge first-parent range is exactly the 11 TASK-007 paths. Source worktree must remain `codex/task-007-local-scoring@95087c...` clean. Confirm identity `Mozhu <huangbuqubunao@gmail.com>` and `user.useConfigOnly=true`.

Stage/commit exactly five prepared Markdown files:

1. `agent-prompts/TASK-007-CLOSURE-INTEGRATOR.md`
2. `docs/PROJECT_STATUS.md`
3. `handoffs/TASK-007.md`
4. `tasks/README.md`
5. `tasks/TASK-007-local-scoring.md`

Prepared-control exception: main is expected to contain exactly these five unstaged/untracked paths. Record SHA-256, verify combined scope exactly, stage only them, recheck hashes/staged blobs. Existing index content, extra path/hash change, identity/source/merge mismatch blocks without cleanup/overwrite/restage/commit.

The prepared card/index/status/handoff must already consistently say `DONE`; verify that fact rather than editing any prepared content. Preserve TASK-006 byte-for-byte/no access. Do not rerun products checks; record existing merge evidence only. Git/document checks (parent/range/scope, diff/EOF/whitespace, cached diff and post-commit clean) only. Commit `docs: close TASK-007 after integration`. Report evidence and remaining real-resource risks. No push, merge, source cleanup or worktree removal.
