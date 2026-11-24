# TASK-011 / TASK-012 preflight authorization sync — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的 preflight 控制面 Markdown；不得启动 Scout、创建 worktree/branch、运行产品命令或修改 source。

## 固定对象

- Main base：`main@654dd4c36015df1db07ddd65e7bb874294c5d4ad`，必须干净且为唯一父基线。
- TASK-010 closure `654dd4c...` 已完成；TASK-011/TASK-012 均保持 `BLOCKED/UNASSIGNED`。
- 这只是读取授权，不构成实现、依赖、Schema、临时 Vault 文件 I/O、launchd、网络、真实云端、凭据或工作树授权。

## 唯一允许提交范围

1. `agent-prompts/TASK-011-012-PREFLIGHT-INTEGRATOR.md`
2. `agent-prompts/TASK-011-012-PREFLIGHT-SCOUT.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-011-weekly-report.md`
6. `tasks/TASK-012-cli-operations.md`

## 必须执行

1. 核验 main identity `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、分支/HEAD、empty index/worktree 与精确六文件范围。
2. 对准备文件做两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围核验；字节漂移立即停止。
3. 不运行 uv、pytest、build、imports、数据库、网络、Vault、云端、凭据、launchctl 或任何产品文件 I/O 命令。
4. 保持 TASK-011/TASK-012=`BLOCKED/UNASSIGNED`，只登记 Scout 已授权未启动；不得预写 ADR 结论、READY、IN_PROGRESS、Reviewer 或 worktree。
5. 提交信息：`docs: authorize TASK-011 and TASK-012 read-only preflights`。提交后 main 必须干净，并确认 Scout prompt 的动态授权解析为本提交。

## 回传格式

```text
Task: TASK-011/012 preflight authorization sync
Base / Head: <base> -> <head>
Committed files: <exact six>
States: TASK-011/TASK-012=BLOCKED/UNASSIGNED
Checks: <Git-only gates>
Product commands: not run
Verdict: INTEGRATED | BLOCKED
```
