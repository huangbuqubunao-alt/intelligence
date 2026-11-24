# TASK-009 Implementer 启动语义修正 — Status Integrator

你是全新的 Codex Status Integrator。只提交主控预写的启动语义修正；不得创建/删除 worktree、实现、审查、合并、rebase、push 或清理，且不得运行 `uv`、pytest、mypy、Ruff、build、网络、数据库或产品命令。

## 固定事实

- Main：`/Users/developer/Documents/youtubek agent` / `main@f9aca7c15357695b4a9ca362fd7c58180011d4a5`。
- TASK-009 source worktree 刻意固定在 `473119704c7638d7afd4e68d84d00e85064ceabd`；因此其本地 `tasks/` 与 `docs/PROJECT_STATUS.md` 是分配前历史快照，仍显示 `BLOCKED/UNASSIGNED`。
- 实时状态与授权唯一来自 main 的本次提交及其后的 TASK-009 Implementer 包：TASK-009 为 `IN_PROGRESS` / Codex。历史快照不构成规格冲突，也不得被 source 写入或更新。
- 身份必须是 `Mozhu <maintainer@example.invalid>` 且 `user.useConfigOnly=true`。

## 唯一允许提交范围

仅以下五个预写 Markdown 文件，内容与 SHA-256 在检查期间必须稳定：

1. `agent-prompts/TASK-009-IMPLEMENTER-CODEX.md`
2. `agent-prompts/TASK-008-009-IMPLEMENTER-START-CORRECTION-INTEGRATOR.md`
3. `docs/PROJECT_STATUS.md`

初始 main 只能有上述三个未提交变更，暂存区必须为空。任何额外/并发变更、哈希变化、身份、main/TASK-009 source 基线或内容冲突，均立即 `BLOCKED`，不得覆盖、重新生成、取消暂存或清理。TASK-008 source 是独立活跃 Implementer worktree，不得读取、等待、修改、暂存或清理。

## 必须核验

1. main HEAD 为 `f9aca7c...`，TASK-009 source 的分支、HEAD=`473119...` 与洁净度正确。
2. main 的 `docs/PROJECT_STATUS.md`、`tasks/README.md`、`tasks/TASK-009-obsidian-notes.md` 均明确 TASK-009=`IN_PROGRESS`；source 副本的旧状态仅作为固定 base 历史，不可当作实时事实。
3. TASK-009 Implementer 包要求以 `git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-009-IMPLEMENTER-CODEX.md` 解析本次主线授权，并在执行前从该 main commit 读取实时状态。
4. `git diff --check`、LF-at-EOF、尾随空白、双轮 SHA-256、暂存范围和 `git diff --cached --check` 均通过。

全通过后只创建一个单父提交：

```text
docs: clarify TASK-009 start authority
```

提交后 main 与 TASK-009 source worktree 必须干净。不得启动 Implementer/Reviewer。回传 `Base/Head/范围/动态授权/source snapshot/状态/Verdict`。
