# TASK-012 closure — Status Integrator

你是全新的 Codex Status Integrator。只收口已经整合的 TASK-012 控制面 Markdown；不得运行产品命令、改 source、再次合并、推送或清理 worktree。

## 固定对象

- Main base：`main@4841cf87c7cfdaf1cca8606bd1c1bbc2d9b01510`，必须干净。
- Merge：`4841cf87c7cfdaf1cca8606bd1c1bbc2d9b01510`；父提交顺序必须为 execution base
  `a6b311378adbfea9e4fe4680628547a63e1709d8`、accepted source
  `4333b1d2bcd0a4b32162ab2d67f112c92fa7d0a3`。
- Retained source：`/Users/developer/Documents/yia-worktrees/task-012` /
  `codex/task-012-cli-operations@4333b1d2bcd0a4b32162ab2d67f112c92fa7d0a3`，必须干净并保留。
- Merge first-parent Diff 必须严格为 TASK-012 的 12 个批准路径；`pyproject.toml` 仅 source-include，依赖、`uv.lock`、build backend 和工具链无变化。

## 唯一允许提交范围

1. `agent-prompts/TASK-012-CLOSURE-INTEGRATOR.md`
2. `docs/PROJECT_STATUS.md`
3. `handoffs/TASK-012.md`
4. `tasks/README.md`
5. `tasks/TASK-012-cli-operations.md`

TASK-013/014 仅可保留既有 `BLOCKED/UNASSIGNED` 状态；不得修改其文件或创建其 worktree。不得暂存产品代码、依赖、锁、Schema、迁移或 source handoff。

## 必须执行

1. 核验 main/source HEAD、merge 双父及顺序、accepted source 为 merge 祖先、身份 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、main/source 洁净度、first-parent 精确范围及 package/lock 边界。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 记录既有整合证据（operations=`7`、full pytest=`421`、mypy、Ruff、CLI、locked sync、plist lint、offline build、archive hashes）但不得重新运行产品、数据库、网络、Vault、云端、凭据、launchctl、plutil 或任何产品文件 I/O 命令。
4. 统一将 TASK-012 在任务卡、任务索引、项目状态和 handoff 写为 `DONE`，记录 merge SHA；不得改 TASK-013/014 或预写后续任务实施授权。
5. 提交信息：`docs: close TASK-012 after integration`。提交后 main/source 必须干净；不得 push、清理或删除 worktree。

## 回传格式

```text
Task: TASK-012 closure
Base / Head: <base> -> <head>
Merge/source/status: 4841cf8... / 4333b1d... / TASK-012=DONE
Committed files: <exact five>
Checks: <Git-only gates and recorded integration evidence>
TASK-013/014 untouched: yes
Verdict: INTEGRATED | BLOCKED
```
