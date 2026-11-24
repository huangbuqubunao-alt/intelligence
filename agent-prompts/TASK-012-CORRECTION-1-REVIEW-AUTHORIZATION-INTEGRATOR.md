# TASK-012 Correction 1 review authorization sync — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@2752ea6d70a1a031a26146909a76efafe04dbb19`，必须干净且为唯一父基线。
- Source：`/Users/developer/Documents/yia-worktrees/task-012` / `codex/task-012-cli-operations@d046c394e3c6bcf47c05231f71dbf50db4c1f5f8`，必须干净。
- Correction 1 唯一父为 Reviewer 1 evidence `9b5dec5d24e87ab942dff4268f7a95c35947d411`，后者唯一父为 implementation `7c83283eac83b01c88a7625b4a216790d14514b2`，且只修改 source handoff。
- Original base：`8e322f362d2ff0972ee987b7c06c8453a9dce73d`；完整 source Diff 仍严格为 12 个批准路径，`pyproject.toml` 例外、依赖/锁和 build backend 边界不变。

## Correction 1 证据与复审边界

- Implementer 报告 doctor 仅在内存生成 UUID4 run_id 并绕过 logger；不存在的 logs/Vault 保持不存在，Fake operations 为零调用。
- 自报 focused=`7`、full pytest=`421`、mypy、Ruff、CLI、plist lint、locked sync、offline build 与 archive hash PASS。这些均为待独立复跑证据，不得预写 Reviewer verdict。
- Reviewer 2 只能追加 source `handoffs/TASK-012.md`，必须复跑离线门禁、ADR-011 O-01..O-06、AC、P1 反例与五轴审查；不得改业务代码、依赖、锁、main 或任务状态。

## 唯一允许提交范围

1. `agent-prompts/TASK-012-CORRECTION-1-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-012-REVIEWER-2-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-012-cli-operations.md`

不得访问、修改或创建 TASK-013/014 source/worktree，也不得暂存产品代码、依赖、锁、Schema、迁移或 handoff。

## 必须执行

1. 核验 main/source HEAD、父链、身份 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、empty index/worktree、Correction/完整 12 路径范围与未变依赖/锁。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、凭据、launchctl、plutil 或任何产品文件 I/O 命令。
4. main 将 TASK-012 设为 `IN_REVIEW`，授权全新独立 Reviewer 2；不得预写 Verdict、ACCEPTED、merge 或 DONE。TASK-013/014 保持 `BLOCKED/UNASSIGNED`。
5. 提交信息：`docs: authorize TASK-012 doctor review`。提交后 main/source 必须干净，并确认 Reviewer prompt 的动态授权解析为本提交。

## 回传格式

```text
Task: TASK-012 Correction 1 review authorization sync
Base / Head: <base> -> <head>
Source/correction/status: <chain>; TASK-012=IN_REVIEW
Committed files: <exact five>
Checks: <Git-only gates>
TASK-013/014 untouched: yes
Verdict: INTEGRATED | BLOCKED
```
