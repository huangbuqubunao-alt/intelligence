# TASK-013 rebuild implementation evidence / review authorization sync — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、修改 source、启动 Reviewer、合并、推送或清理。

## 固定对象

- Main base：`main@9814a1d98c434ce2fbc3c971bba5641111ca6659`，必须干净且为唯一父基线。
- Rebuilt source：`/Users/hua/Documents/yia-worktrees/task-013-rebuild` / `codex/task-013-e2e-acceptance-rebuild@0a9e16887e7dc0b287be941a34e2908766e3992e`，开始时必须干净，唯一父提交为 `2a59dfe3860161a5989f2c08161f03c73aa4ca86`。
- 历史 `/Users/hua/Documents/yia-worktrees/task-013` / `codex/task-013-e2e-acceptance` 为已拒绝审计证据，不得访问、修改或清理。
- 相对 `2a59dfe...` 的 rebuilt source 只允许两份 E2E、`tests/e2e/fixtures/**`、验收报告和 handoff；当前实际改动为两份 E2E、验收报告和 handoff。

## 唯一允许提交范围

1. `agent-prompts/TASK-013-REBUILD-IMPLEMENTATION-EVIDENCE-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-013-REBUILD-REVIEWER-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-013-e2e-acceptance.md`

## 必须执行

1. 核验 main/source identity、`user.useConfigOnly=true`、父链、洁净度、当前 source 四路径/最大五路径范围、锁文件不变与 Diff 空白检查。
2. 对五个准备文件做两轮 SHA-256、LF/EOF、无尾随空白、精确暂存范围和 `git diff --cached --check`；任何字节漂移立即停止。
3. main 将 TASK-013 设为 `IN_REVIEW`，授权全新独立 Codex Reviewer；不得预写 Verdict、ACCEPTED、merge 或 DONE。TASK-014 继续 BLOCKED。
4. 动态 Reviewer authorization 必须解析为本次提交；提交信息为 `docs: authorize TASK-013 real-flow review`。
5. 不运行 uv、pytest、mypy、Ruff、build、imports、数据库、网络、模型、媒体、Vault、凭据或任何产品命令。

## 回传格式

```text
Task: TASK-013 rebuild implementation evidence / review authorization sync
Base / Head: <base> -> <head>
Source / status: <source> / TASK-013=IN_REVIEW
Committed files: <exact five>
Checks: <Git-only gates>
Product commands: not run
Verdict: INTEGRATED | BLOCKED
```
