# TASK-013 first review reject / Correction 1 sync — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的 Correction 1 控制面 Markdown；不得修改 source、启动 Worker、创建 worktree/branch、运行产品命令、推送或合并。

## 固定对象

- Main base：`main@9ca25cce8119cf6e9ee91489cc845585d55f5fd0`；HEAD 必须精确匹配，且新提交必须以它为唯一父提交。
- Reviewer evidence：`codex/task-013-e2e-acceptance@2afd95a8dde9ae2d907480fd190bcb2c54efccb4`，唯一父必须为 `fd22c8ced0343a38e4cb8acdde0ef608bc6d8708`，且 evidence 只修改 `handoffs/TASK-013.md`。
- Verdict=`REJECT`：P1 是 E2E 以通用 handler 直接推进 SQLite 状态，未真正驱动字幕、Whisper、评分与云分析服务；P2 是 PRD 10.7 无可复现的凭据扫描证据。

## 唯一允许提交范围

1. `agent-prompts/TASK-013-FIRST-REVIEW-REJECT-CORRECTION-1-INTEGRATOR.md`
2. `agent-prompts/TASK-013-CORRECTION-1-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-013-e2e-acceptance.md`

## Correction 1 冻结范围

仅允许 `tests/e2e/test_mvp_flow.py`、`tests/e2e/test_failure_recovery.py`、`tests/e2e/fixtures/**`、`docs/ACCEPTANCE_REPORT.md`、`handoffs/TASK-013.md`。不得修改生产源码、CLI/composition、配置、Schema/migration、依赖、锁文件、测试配置、既有测试、任务状态或真实资源边界。

## 必须执行

1. 核验 main/source identity、`user.useConfigOnly=true`、父链、洁净度、review evidence handoff-only 范围、完整 source 五路径范围和无依赖/锁/生产代码变动。
2. 初始 index 必须为空。工作树只允许存在上述五个主控准备文件；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；漂移或范围外路径立即停止。
3. 不运行 uv、pytest、mypy、Ruff、build、imports、数据库、网络、Vault、云端、模型、凭据、launchctl 或任何产品文件 I/O 命令。
4. main 将 TASK-013 设为 `IN_PROGRESS`，退回原 Codex Implementer；不得预写 Reviewer、APPROVE、ACCEPTED、merge SHA 或 DONE。TASK-014 保持 `BLOCKED/UNASSIGNED`。
5. 提交信息：`docs: return TASK-013 for real service-flow correction`。提交后 main/source 必须干净，并确认 Correction prompt 的动态授权解析为本提交。

## 回传格式

```text
Task: TASK-013 first review reject / Correction 1 sync
Base / Head: <base> -> <head>
Source / status: <evidence> / TASK-013=IN_PROGRESS
Committed files: <exact five>
Checks: <Git-only gates>
Product commands: not run
Verdict: INTEGRATED | BLOCKED
```
