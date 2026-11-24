# TASK-011 closure — Status Integrator

你是全新的 Codex Status Integrator。只收口已经整合的 TASK-011 控制面 Markdown；不得运行产品命令、改 source、再次合并、推送或清理 worktree。

## 固定对象

- Main base：`main@2ba42c2f55082f5ce74ddc04d8aa18a7ef85fae1`，必须干净。
- Merge：`2ba42c2f55082f5ce74ddc04d8aa18a7ef85fae1`；父提交顺序必须为 execution base
  `3cdc9fc94568a4a836dc187995f98ec5148b6e97`、accepted source
  `1ecd4bc8c6138bab6683a011cbbecddf281263c3`。
- Retained source：`/Users/developer/Documents/yia-worktrees/task-011` /
  `codex/task-011-weekly-report@1ecd4bc8c6138bab6683a011cbbecddf281263c3`，必须干净并保留。
- Merge first-parent Diff 必须严格为 `handoffs/TASK-011.md`、`reporting.py`、`state.py`、
  `providers/obsidian.py`、`templates/weekly.md`、两份既定周报 tests；锁文件无变化。

## 唯一允许提交范围

1. `agent-prompts/TASK-011-CLOSURE-INTEGRATOR.md`
2. `docs/PROJECT_STATUS.md`
3. `handoffs/TASK-011.md`
4. `tasks/README.md`
5. `tasks/TASK-011-weekly-report.md`

TASK-012 仅可保留既有 `BLOCKED/UNASSIGNED` 状态；不得修改其文件或创建其 worktree。不得暂存产品代码、依赖、锁、Schema、迁移或 source handoff。

## 必须执行

1. 核验 main/source HEAD、merge 双父及顺序、accepted source 为 merge 祖先、身份
   `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、main/source 洁净度、first-parent 精确范围和未变锁文件。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 记录既有整合证据（focused=`15`、full pytest=`414`、mypy、Ruff、CLI、locked sync、offline build、archive 内容）但不得重新运行产品、数据库、网络、Vault、云端、凭据或任何产品文件 I/O 命令。
4. 统一将 TASK-011 在任务卡、任务索引、项目状态和 handoff 写为 `DONE`，记录 merge SHA；不得改 TASK-012 或预写后续任务实现授权。
5. 提交信息：`docs: close TASK-011 after integration`。提交后 main/source 必须干净；不得 push、清理或删除 worktree。

## 回传格式

```text
Task: TASK-011 closure
Base / Head: <base> -> <head>
Merge/source/status: 2ba42c2... / 1ecd4bc... / TASK-011=DONE
Committed files: <exact five>
Checks: <Git-only gates and recorded integration evidence>
TASK-012 untouched: yes
Verdict: INTEGRATED | BLOCKED
```
