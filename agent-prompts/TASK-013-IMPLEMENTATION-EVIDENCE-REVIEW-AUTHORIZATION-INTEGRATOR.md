# TASK-013 implementation evidence / review authorization sync — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的审查授权控制面 Markdown；不得启动 Reviewer、修改 source、创建 worktree/branch、运行产品命令、推送或合并。

## 固定对象

- Main base：`main@20159c911b1f76de5bb09de8c753afc7eedd1437`；HEAD 必须精确匹配，且新提交必须以它为唯一父提交。
- Source：`codex/task-013-e2e-acceptance@fd22c8ced0343a38e4cb8acdde0ef608bc6d8708`，唯一父提交必须为 `9462b6a162a1e9a738b4073fa5e8b2252101f6af`，source 必须干净。
- TASK-013 只授权离线固定夹具和测试内 composition；真实 YouTube、模型、Provider、网络、密钥、真实 Vault/用户笔记与测试目录外文件操作仍未授权。

## 唯一允许提交范围

1. `agent-prompts/TASK-013-IMPLEMENTATION-EVIDENCE-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-013-REVIEWER-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-013-e2e-acceptance.md`

## 必须执行

1. 核验 main/source 的分支、HEAD、父链、身份 `Mozhu <huangbuqubunao@gmail.com>`、`user.useConfigOnly=true`、洁净度、source 的精确五路径范围，以及 source 无依赖/锁/生产代码改动。
2. 初始 index 必须为空。工作树只允许存在上述五个主控准备文件；对其做两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围核验。字节漂移或任何范围外路径立即停止。
3. 不运行 uv、pytest、mypy、Ruff、build、imports、数据库、网络、Vault、云端、模型、凭据、launchctl 或任何产品文件 I/O 命令。
4. main 将 TASK-013 设为 `IN_REVIEW`，只登记全新独立 Codex Reviewer 已授权未启动；不得预写 APPROVE、ACCEPTED、merge SHA 或 DONE。TASK-014 继续 `BLOCKED/UNASSIGNED`。
5. 提交信息：`docs: authorize TASK-013 offline acceptance review`。提交后 main/source 必须干净，并确认 Reviewer prompt 的动态授权解析为本提交。

## 回传格式

```text
Task: TASK-013 implementation evidence / review authorization sync
Base / Head: <base> -> <head>
Source / status: <source> / TASK-013=IN_REVIEW
Committed files: <exact five>
Checks: <Git-only gates>
Product commands: not run
Verdict: INTEGRATED | BLOCKED
```
