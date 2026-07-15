# TASK-004 Pre-review Correction Sync

## 身份与边界

你是原 Status Integrator。本轮只提交 TASK-004 的主控预审发现与 Grok Correction 包；不得修改产品代码、任务 worktree、依赖、锁文件、状态机或 Reviewer 记录，不得启动 Reviewer。

## 固定基线

- Task: `TASK-004 pre-review correction sync`
- Role: `Status Integrator`
- Required main base: `main@12079aee1bdb8d4063ff9ecc429c582714c807f4`
- Main worktree: `/Users/hua/Documents/youtubek agent`
- TASK-004 source worktree: `/Users/hua/Documents/yia-worktrees/task-004`，严格只读
- Required source branch: `grok/task-004-discovery-metadata`
- Required source head: `392edfb897003c1583b538667d10a2a89926a94b`
- TASK-003 worktree: `/Users/hua/Documents/yia-worktrees/task-003`，严格只读，不得触碰

## 唯一允许提交的 5 个文件

- `agent-prompts/TASK-004-CORRECTION-GROK.md`
- `agent-prompts/TASK-004-PRE-REVIEW-CORRECTION-INTEGRATOR.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-004-discovery-metadata.md`

初始范围不是精确这 5 个文件、已有 staged 内容、main HEAD 不符、TASK-004 source worktree 不干净/HEAD 不符或 main 出现并发写入时，立即停止并报告 `BLOCKED`；不得自行修复、清理或吸收修改。TASK-003 正在独立实现，其 worktree 可以有未提交改动；本轮不得读取、写入、清理或把它作为 TASK-004 门禁。

## 必查事实

- 首个 TASK-004 source diff 相对 `dcc7d85...` 精确属于批准的 17 个文件，`git diff --check` 通过，且 source worktree 干净。
- 预审 P1 是公共自由 `dict` 泄漏：`SAFE_YDL_OPTS`、`build_ydl_opts` 和 Mapping helper 被 `__all__` 导出，`YtDlpMetadataProvider` 公开 `last_opts: list[dict[str, Any]]`。
- P1 尚未修复；TASK-004 保持 `IN_PROGRESS`，Codex Reviewer 不得启动。
- Correction 包仅允许原 Grok 在 source worktree 修改 `youtube.py`、`test_discovery.py`、`handoffs/TASK-004.md`，且要求新 commit 不 amend 首个实现。
- TASK-003 保持 `IN_PROGRESS`，其独立 worktree 的未提交实现属于预期并行状态，不受本轮影响；TASK-005 及后续仍为 `BLOCKED`。
- Git 身份必须是 `Mozhu <huangbuqubunao@gmail.com>`，`user.useConfigOnly=true`，且不含 `.local`。

## 检查与提交

在 main 与 TASK-004 source worktree 只读运行 git 基线、分支、HEAD、状态和身份检查；完整阅读 5 个 Expected files，运行：

```bash
git diff --check
git diff --name-status
git -C "/Users/hua/Documents/yia-worktrees/task-004" diff --name-status dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176...392edfb897003c1583b538667d10a2a89926a94b
git -C "/Users/hua/Documents/yia-worktrees/task-004" diff --check dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176...392edfb897003c1583b538667d10a2a89926a94b
```

仅暂存 5 个 Expected files，运行 `git diff --cached --check`、`git diff --cached --name-status`、`git diff --cached`。提交：

```text
docs: request TASK-004 public contract correction
```

提交后确认新提交是 `12079aee...` 的单父后继，范围精确为 5 文件，main/source worktree 干净。不得运行产品测试、uv 命令、依赖安装或 TASK-004 Reviewer。

## 返回格式

```text
Task: TASK-004 pre-review correction sync
Role: Status Integrator
Base:
Head commit:
Git identity:
Checks:
- Initial/staged scope:
- TASK-004 source branch/head/scope/clean:
- P1 correction record and packet:
- TASK-003 isolation:
- git diff checks:
Committed files:
Final state: TASK-004=IN_PROGRESS (correction pending); Reviewer not started
Post-commit status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
