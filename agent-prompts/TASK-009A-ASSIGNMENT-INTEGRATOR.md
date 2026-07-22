# TASK-009A 分配同步 — Worktree / Status Integrator

你是全新的 Codex Worktree / Status Integrator。你只创建已批准的 TASK-009A worktree 并提交主控预写控制面；不得实现、审查、安装依赖、运行 `uv`、pytest、mypy、Ruff、build、数据库、网络、Vault 或任何产品命令。

## 固定授权

- Required base：`main@e4271e41910bba54b37b48df709dcf632fe3b0eb`
- Worktree：`/Users/hua/Documents/yia-worktrees/task-009a`
- Branch：`codex/task-009a-obsidian-note-shared-contracts`
- Implementer：Codex；Reviewer：实现 commit 后启动全新独立 Codex Reviewer。
- 身份必须为 `Mozhu <huangbuqubunao@gmail.com>`，`user.useConfigOnly=true`。

## 唯一允许的 main 提交范围

仅以下五个已准备 Markdown 文件：

1. `agent-prompts/TASK-009A-ASSIGNMENT-INTEGRATOR.md`
2. `agent-prompts/TASK-009A-IMPLEMENTER-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-009A-obsidian-note-shared-contracts.md`

初始 main 必须正好是 Required base、暂存区为空，且工作树仅有以上五个预写变更。目标路径和分支在创建前必须都不存在。准备文件在两轮 SHA-256 检查之间若有字节变化，或出现任何范围外/并发变化，立即 `BLOCKED`；不得覆盖、重写、取消暂存、清理或自行解决。

## 操作与门禁

1. 在无网络、无产品命令情况下，创建指定 worktree/branch，明确基于 Required base；验证 source branch、HEAD、洁净度。
2. 仅提交上述五个控制面文件。创建后的 task source 仍显示 `BLOCKED/UNASSIGNED` 是预期冻结基线；main 提交后的控制面才是 TASK-009A 的实时状态。
3. main 控制面必须将 TASK-009A 标为 `IN_PROGRESS`、Assignee=`Codex`、Reviewer=`全新独立 Codex（等待实现 commit）`，记录固定 base/worktree/branch、五路径产品范围、Jinja2 已批准依赖和红线。
4. TASK-008A 保持 `DONE`；TASK-008/TASK-009 和后续任务保持 `BLOCKED/UNASSIGNED`。修正 `docs/PROJECT_STATUS.md` 的两处重复状态文字，但不得改变 TASK-008A 的 merge/验收事实。
5. 核验 LF-at-EOF、尾随空白、`git diff --check`、暂存范围、`git diff --cached --check`、提交范围、唯一父链和最终 main/source 洁净度。

只在全部通过后，创建单父提交：

```text
docs: assign TASK-009A worktree
```

回传 `Task/Role/Base/Head/worktree/branch/identity/精确文件范围/检查/状态/Post-commit status/Verdict/remaining risks`。
