# TASK-012 acceptance / final integration authorization sync — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@b77e8656bb7dd42084e833993fe2ab5b6ba5c545`，必须干净且为唯一父基线。
- Accepted source：`/Users/developer/Documents/yia-worktrees/task-012` / `codex/task-012-cli-operations@4333b1d2bcd0a4b32162ab2d67f112c92fa7d0a3`，必须干净。
- Reviewer 2 evidence `4333b1d...` 的唯一父为 Correction 1 `d046c394e3c6bcf47c05231f71dbf50db4c1f5f8`，且只修改 source handoff；完整 source Diff 严格为 12 个批准路径。
- `pyproject.toml` 仅为 `[tool.uv.build-backend].source-include`；依赖、`uv.lock`、build backend 和工具链未变。

## 验收事实

- Reviewer 2 verdict=`APPROVE`，P0/P1/P2/P3=0；ADR-011 O-01..O-06 与 TASK-012 AC 均 PASS。
- 独立证据包含 locked sync、focused=`7`、full pytest=`421`、mypy、Ruff、CLI、两份 plist lint、offline build，及 doctor 零副作用、JSONL 脱敏、root/package-resource archive hashes。
- 上述为既有审查证据；本控制面角色不得重新运行产品命令。

## 唯一允许提交范围

1. `agent-prompts/TASK-012-ACCEPTANCE-INTEGRATION-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-012-INTEGRATOR.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-012-cli-operations.md`

不得访问、修改或创建 TASK-013/014 source/worktree，也不得暂存产品代码、依赖、锁、Schema、迁移或 handoff。

## 必须执行

1. 核验 main/source HEAD、父链、身份 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、empty index/worktree、Reviewer evidence handoff-only scope、完整 12 路径范围与 pyproject/依赖/锁边界。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、凭据、launchctl、plutil 或任何产品文件 I/O 命令。
4. main 将 TASK-012 设为 `ACCEPTED`，授权 Product Integrator；不得预写 merge SHA 或 DONE。TASK-013/014 保持 `BLOCKED/UNASSIGNED`。
5. 提交信息：`docs: accept and authorize TASK-012 integration`。提交后 main/source 必须干净，并确认 Integrator prompt 的动态授权解析为本提交。

## 回传格式

```text
Task: TASK-012 acceptance / final integration authorization sync
Base / Head: <base> -> <head>
Review/source/status: <evidence>; TASK-012=ACCEPTED
Committed files: <exact five>
Checks: <Git-only gates>
TASK-013/014 untouched: yes
Verdict: INTEGRATED | BLOCKED
```
