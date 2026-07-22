# TASK-009 — Codex Implementer

你是 TASK-009 的唯一 Codex Implementer。任务已由 main 控制面正式分配；source worktree 内的 `tasks/` **和** `docs/PROJECT_STATUS.md` 保留 `BLOCKED/UNASSIGNED` 是固定 base 快照。它们不是冲突：实时授权只以本包动态 main commit 中 TASK-009=`IN_PROGRESS` 为准，source 历史文档不得写回或自行更新。

## 固定对象

- Main authorization：动态读取 `git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-009-IMPLEMENTER-CODEX.md`
- Base：`473119704c7638d7afd4e68d84d00e85064ceabd`
- Worktree/branch：`/Users/hua/Documents/yia-worktrees/task-009` / `codex/task-009-obsidian-notes`
- Allowed scope：`src/youtube_intel/notes.py`、`src/youtube_intel/providers/obsidian.py`、`src/youtube_intel/templates/video.md`、`tests/fixtures/notes/**`、`tests/unit/test_note_rendering.py`、`tests/integration/test_obsidian_sink.py`、`handoffs/TASK-009.md`。
- Reuse：`DIRECT` Jinja2 already locked by TASK-009A, with fixed package template, immutable sandbox and StrictUndefined; existing PyYAML/Artifact/SQLite/Pydantic/stdlib. Registered yt2md candidates are `REFERENCE` only, with no copied code or Obsidian configuration reading.

开始前必须用上面的动态 SHA 读取 main 的 `docs/PROJECT_STATUS.md`、`tasks/README.md` 和 `tasks/TASK-009-obsidian-notes.md`，确认它们均为本次 `IN_PROGRESS` 分配；不得把 source 副本的历史状态视为 `DECISION NEEDED`。

## Approved boundary and checks

- File creation, replace, cleanup and symlink probes may occur only under test-created temporary directories. The worktree, a real Obsidian Vault, real user notes, and any location outside a test temp directory are never valid write targets.
- Do not access real Vault content, read credentials, call cloud/network/model paths, or delete/move/rename external files.
- No dependency/lockfile, shared-domain/config, state/Schema/migration, CLI, cloud Provider or task-status changes.
- Implement ADR-009 N-01 to N-15 and TASK-009 AC within scope. Required commands: `uv lock --check`; `uv sync --locked`; focused unit and integration tests named by the task card; full pytest; mypy; Ruff; CLI help; `uv build --offline`; and `git diff --check 473119704c7638d7afd4e68d84d00e85064ceabd...HEAD`.
- Verify sdist/wheel migration inclusion, exact seven scope groups, and handoff reuse/license evidence; commit once and report SHA. Do not merge or alter task status. Any public-contract, dependency, real-resource or out-of-scope need is `DECISION NEEDED`.
