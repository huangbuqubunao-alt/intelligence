# TASK-008 Correction 3 状态一致性修正 — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的最小控制面修正；不得运行产品命令、改 source、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@b85c83cfe4fd6e24059dd9644aa1bed2ee90155b`，必须干净且为唯一父基线。
- Source：`/Users/developer/Documents/yia-worktrees/task-008` / `codex/task-008-deep-analysis@b380a8c87d99a3d2dbf88b28bde3ec5b0de4da0f`，必须干净且未触碰。
- `tasks/README.md` 与已提交的 `TASK-008-CORRECTION-3-CODEX.md` 均已把 TASK-008 定义为 `IN_PROGRESS`；但 main `tasks/TASK-008-deep-analysis.md` 顶部仍错误写为 `IN_REVIEW`。这是唯一需要修正的控制面冲突。

## 唯一允许提交范围

1. `agent-prompts/TASK-008-CORRECTION-3-STATUS-CORRECTION-INTEGRATOR.md`
2. `tasks/TASK-008-deep-analysis.md`

不得修改任务内容、Correction 3 实现者提示词、状态索引、项目状态、任何产品代码、依赖、锁、Schema、迁移、handoff 或 TASK-009。

## 必须执行

1. 核验 main/source branch、HEAD、身份 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、empty index/worktree、以及上述唯一状态冲突。
2. 准备文件必须精确为上述两条路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 将 main 任务卡顶部状态仅从 `IN_REVIEW` 修为 `IN_PROGRESS`；不改变其他字节或任务语义。
4. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、凭据或任何产品文件 I/O 命令。
5. 提交信息：`docs: correct TASK-008 correction status`。提交后 main/source 必须干净；TASK-008=IN_PROGRESS，TASK-009 不得触碰。

## 回传格式

```text
Task: TASK-008 Correction 3 status correction
Base / Head: <base> -> <head>
Committed files: <exact two>
Status: TASK-008=IN_PROGRESS consistently
Checks: <git-only gates>
TASK-009 untouched: yes
Verdict: INTEGRATED | BLOCKED
```
