# TASK-013 read-only preflight authorization sync — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的 TASK-013 只读预检控制面 Markdown；不得启动 Scout、创建 worktree/branch、运行产品命令或修改 source。

## 固定对象

- Main base：`main@7a787fc2817a4efae1f4565cb1196589ee2461c8`，HEAD 必须精确匹配，且新提交必须以它为唯一父提交。
- TASK-011/TASK-012 已 `DONE`；TASK-013/TASK-014 均保持 `BLOCKED/UNASSIGNED`。
- 此包只授权只读产品验收预检；不构成实现、依赖、Schema、夹具、临时 Vault 文件 I/O、真实网络/频道、模型、云端、凭据、launchd 或 worktree 授权。

## 唯一允许提交范围

1. `agent-prompts/TASK-013-PREFLIGHT-INTEGRATOR.md`
2. `agent-prompts/TASK-013-PREFLIGHT-SCOUT.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-013-e2e-acceptance.md`

## 必须执行

1. 核验 main identity 为 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、分支/HEAD 与 empty index。工作树允许存在主控预置的上述五个准备文件；除此以外任何未暂存、暂存或未跟踪路径都必须立即停止，不覆盖并发改动。
2. 仅提交上述五个文件；先确认准备文件的未提交范围精确匹配该列表，再做两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围核验。任何字节漂移立即停止，不覆盖并发改动。
3. 不运行 `uv`、pytest、mypy、Ruff、build、imports、数据库、网络、Vault、云端、模型、凭据、launchctl 或任何产品文件 I/O 命令。
4. 仅登记“TASK-013 read-only Scout 已授权、未启动”；不得预写预检结论、ADR 结论、READY、IN_PROGRESS、Reviewer 或 worktree。
5. 提交信息：`docs: authorize TASK-013 read-only preflight`。提交后 main 必须干净，并确认 Scout prompt 的动态授权解析为本提交。

## 回传格式

```text
Task: TASK-013 preflight authorization sync
Base / Head: <base> -> <head>
Committed files: <exact five>
State: TASK-013=BLOCKED/UNASSIGNED; Scout authorized, not started
Checks: <Git-only gates>
Product commands: not run
Verdict: INTEGRATED | BLOCKED
```
