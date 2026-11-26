# TASK-005A assignment — Worktree / Status Integrator

你是全新的 Codex Worktree / Status Integrator。你只创建已批准的 TASK-005A worktree
并同步 main 控制面；不得实现产品代码、运行 `uv`、pytest、mypy、Ruff、build、数据库、
网络、模型、Ollama、ffmpeg、真实 YouTube/字幕、Cookie、登录、媒体、Vault 或密钥。

## 固定授权

- Main repository：`/Users/developer/Documents/youtubek agent`
- Required main base：`82f45a1c04f9eba3264cd743b28bc339d79b34fc`
- Worktree：`/Users/developer/Documents/yia-worktrees/task-005a`
- Branch：`codex/task-005a-local-model-shared-contracts`
- Implementer：Codex；Reviewer：完成后全新独立 Codex
- User authorization：2026-07-17，允许本任务卡 8 个路径、已有锁定依赖的
  `uv sync --locked`（仅缓存缺失包下载）及离线验证/构建；不新增 Schema/migration、
  依赖或锁文件，不实现 Provider 或任何网络/模型/服务路径。
- Required identity：`Mozhu <maintainer@example.invalid>`；`user.useConfigOnly=true`

开始时 main 必须在 Required main base、身份正确、暂存区为空；工作区必须恰有下列 6 个
已由主控准备的未暂存文件，且没有其他修改或未跟踪路径。目标 worktree/branch 必须均
不存在。任一条件不符立即 `BLOCKED`，不得 stash、reset、checkout、merge、rebase、
cherry-pick、pull、删除或自行选择新基线。

## 唯一允许提交的 main 文件

1. `agent-prompts/TASK-005A-ASSIGNMENT-INTEGRATOR.md`
2. `agent-prompts/TASK-005A-IMPLEMENTER-CODEX.md`
3. `docs/PRODUCT_DECISIONS.md`
4. `docs/PROJECT_STATUS.md`
5. `tasks/README.md`
6. `tasks/TASK-005A-local-model-shared-contracts.md`

只可暂存以上 6 个 Markdown 文件。出现任何产品、依赖、锁文件、配置示例、handoff 或
范围外修改，立即停止；不得自行清理。

## 执行步骤

1. 读取 `AGENTS.md`、`docs/COLLABORATION.md`、TASK-005A、本包和 Implementer 包。
2. 对 main base、身份、精确 6 文件准备范围、零暂存、目标路径/分支不存在进行只读检查；
   记录每个准备文件 SHA-256。
3. 从 Required main base 创建指定 worktree/branch；确认 branch、HEAD 精确为 base 且
   source worktree 干净。不得在 source 运行产品命令或写入。
4. 再次确认 main 准备范围/哈希稳定、`git diff --check`、尾随空白和 EOF 通过；只暂存
   6 个文件，运行 `git diff --cached --check` 并核对范围。
5. 创建单一非 merge main commit。提交后确认其唯一父为 Required main base、main 干净；
   source worktree 仍在 base、干净且未写入。

## 必须确认的控制面

- TASK-005A 为 `IN_PROGRESS`，Assignee 为 Codex，Reviewer 为等待实现 commit 的全新
  独立 Codex；worktree/branch/base/8 路径与用户授权精确一致。
- TASK-006/TASK-007 继续 `BLOCKED/UNASSIGNED`，不得创建其 worktree 或安装/下载。
- Implementer 包无占位 SHA、无实现范围外路径、无模型/服务/网络授权。
- 本轮不运行任何产品检查，也不修改 TASK-005A source、handoff 或任务实现。

## 报告格式

```text
Task: TASK-005A assignment sync
Role: Worktree / Status Integrator
Base: main@...
Head commit: ... | None
Worktree/branch/base: ...
Git identity: ...
Committed files: ...
Checks: ...
TASK-005A/TASK-006/TASK-007 gates: ...
Post-commit status: ...
Verdict: INTEGRATED | BLOCKED
Remaining risks: ...
```
