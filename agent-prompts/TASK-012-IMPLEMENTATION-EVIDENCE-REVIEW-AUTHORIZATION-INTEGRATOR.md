# TASK-012 implementation evidence / review authorization sync — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@1cfafce694b9248ec381ea75d5e342d0553e65d9`，必须干净且为唯一父基线。
- Source：`/Users/hua/Documents/yia-worktrees/task-012` / `codex/task-012-cli-operations@7c83283eac83b01c88a7625b4a216790d14514b2`，必须干净。
- Source implementation 唯一父为固定 base `8e322f362d2ff0972ee987b7c06c8453a9dce73d`；完整 Diff 严格为 12 个批准路径。
- `pyproject.toml` 例外仅为 `[tool.uv.build-backend].source-include` 的 plist/docs 归档包含配置；`[project].dependencies`、build backend、工具链和 `uv.lock` 均不得变化。

## 实现证据与审查边界

- Implementer 自报 CLI 五个命令/退出码、UUID4 JSONL 脱敏、doctor 零昂贵副作用、两份静态 plist、运维说明与 root/package-resource 归档字节一致性；focused=`6`、full pytest=`420`、mypy、Ruff、CLI、locked sync、offline build 与 archive checks PASS。这些仅为待独立复跑证据。
- Reviewer 1 只可追加 source `handoffs/TASK-012.md`，复跑离线门禁与 ADR-011 O-01..O-06/AC/五轴审查；不得改业务代码、依赖、锁、main 或任务状态。

## 唯一允许提交范围

1. `agent-prompts/TASK-012-IMPLEMENTATION-EVIDENCE-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-012-REVIEWER-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-012-cli-operations.md`

不得访问、修改或创建 TASK-013/014 source/worktree，也不得暂存产品代码、依赖、锁、Schema、迁移或 handoff。

## 必须执行

1. 核验 main/source HEAD、父链、身份 `Mozhu <huangbuqubunao@gmail.com>`、`user.useConfigOnly=true`、empty index/worktree、12 路径 source 范围、pyproject 例外和未变依赖/锁。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、凭据、launchctl、plutil 或任何产品文件 I/O 命令。
4. main 将 TASK-012 设为 `IN_REVIEW`，授权全新独立 Reviewer；不得预写 Verdict、ACCEPTED、merge 或 DONE。TASK-013/014 保持 `BLOCKED/UNASSIGNED`。
5. 提交信息：`docs: authorize TASK-012 independent review`。提交后 main/source 必须干净，并确认 Reviewer prompt 的动态授权解析为本提交。

## 回传格式

```text
Task: TASK-012 implementation evidence / review authorization sync
Base / Head: <base> -> <head>
Source/status: <source>; TASK-012=IN_REVIEW
Committed files: <exact five>
Checks: <Git-only gates>
TASK-013/014 untouched: yes
Verdict: INTEGRATED | BLOCKED
```
