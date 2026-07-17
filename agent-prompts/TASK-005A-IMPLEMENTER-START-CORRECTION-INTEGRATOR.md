# TASK-005A Implementer start correction — Status Integrator

你是全新的 Codex Status Integrator。此前 TASK-005A Implementer 在零写入、零产品命令
状态下正确停止：source worktree 固定在 assignment 前 base，因此其任务卡仍显示历史
`BLOCKED/UNASSIGNED`，而旧 Implementer 包错误地把该快照当成实时阻塞。你只提交本
启动规则修正，不实现产品、创建/删除 worktree、运行 `uv`、测试、构建、数据库、网络、
模型、服务或真实资源路径。

## 固定基线

- Main repository：`/Users/hua/Documents/youtubek agent`
- Required main base：`99f0512ef9aa6f06c5cfc7daf46a4171a44c44e5`
- Source worktree：`/Users/hua/Documents/yia-worktrees/task-005a`
- Source branch/base：`codex/task-005a-local-model-shared-contracts` /
  `82f45a1c04f9eba3264cd743b28bc339d79b34fc`
- Required identity：`Mozhu <huangbuqubunao@gmail.com>`；`user.useConfigOnly=true`

开始时 main HEAD 必须为 Required main base、身份正确、暂存区为空；工作区必须恰有
下列 2 个准备文件且无其他修改/未跟踪路径。source 必须仍在固定 base 且干净，历史
任务卡为 `BLOCKED/UNASSIGNED` 是预期。任一条件不符立即 `BLOCKED`；不得清理、
stash、reset、checkout、merge、rebase、cherry-pick、pull 或更改 source。

## 唯一允许提交的 main 文件

1. `agent-prompts/TASK-005A-IMPLEMENTER-CODEX.md`
2. `agent-prompts/TASK-005A-IMPLEMENTER-START-CORRECTION-INTEGRATOR.md`

只可暂存此二文件。禁止修改产品、任务状态、Project Status、依赖、锁文件、测试、
handoff、worktree 或其他文件。

## 必须确认的修正

- main 的 TASK-005A 控制面仍为 `IN_PROGRESS/Codex`；它是实时状态的唯一来源。
- source 的历史 TASK-005A/PROJECT_STATUS 快照仍是 `BLOCKED/UNASSIGNED`；它不能使
  Implementer 阻塞，也不得被回填或修改。
- 修正后的 Implementer 包要求双重校验：assignment commit 是 base 的直接后继，
  本修正 commit 是 assignment commit 的直接后继；source 仍固定 base。
- TASK-006/TASK-007 状态和授权边界不变，且本轮不启动任何 Worker。

## 执行与报告

1. 读取 `AGENTS.md`、`docs/COLLABORATION.md`、本包和修正后的 Implementer 包。
2. 检查 main/source 基线、身份、精确范围、零暂存、hash 稳定性、`git diff --check`、
   EOF/尾随空白。
3. 只暂存两文件，运行 `git diff --cached --check`，创建单一非 merge main commit。
4. 提交后确认唯一父为 Required main base、main 干净；source 仍为 base 且干净。

```text
Task: TASK-005A Implementer start correction sync
Role: Status Integrator
Base: main@...
Head commit: ... | None
Committed files: ...
Main/source status model: ...
Checks: ...
Post-commit status: ...
Verdict: INTEGRATED | BLOCKED
Remaining risks: ...
```
