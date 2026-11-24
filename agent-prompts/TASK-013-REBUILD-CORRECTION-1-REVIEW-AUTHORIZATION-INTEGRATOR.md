# TASK-013 rebuild Correction 1 review authorization — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、修改 source、启动 Reviewer、合并、推送或清理。

## 固定对象

- Main base：`main@9ce5bf68bf4c0608fc0a198def9c582f3e2a5389`，必须干净且为唯一父基线。
- Correction 1 source：`/Users/developer/Documents/yia-worktrees/task-013-rebuild` / `codex/task-013-e2e-acceptance-rebuild@ae724990f6f3628a054bfca000e9e28d83f3def7`，开始时必须干净；唯一父提交为 review evidence `3cf8b5fd8e7abec8f8a6595227a8919a7a8804e1`。
- 完整产品范围相对 `2a59dfe3860161a5989f2c08161f03c73aa4ca86` 只允许两份 E2E、`tests/e2e/fixtures/**`、`docs/ACCEPTANCE_REPORT.md` 和 `handoffs/TASK-013.md`；锁文件不变。
- 历史 `/Users/developer/Documents/yia-worktrees/task-013` / `codex/task-013-e2e-acceptance` 是已拒绝审计证据，禁止访问、修改或清理。

## 唯一允许提交范围

1. `agent-prompts/TASK-013-REBUILD-CORRECTION-1-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-013-REBUILD-CORRECTION-1-REVIEWER-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-013-e2e-acceptance.md`

## 必须执行

1. 核验 main/source identity、`user.useConfigOnly=true`、父链、洁净度、完整产品范围、锁文件不变和 Diff 空白检查。
2. 对五个准备文件做两轮 SHA-256、LF/EOF、无尾随空白、精确暂存范围和 `git diff --cached --check`；任何字节漂移立即停止。
3. main 将 TASK-013 设为 `IN_REVIEW`，授权全新独立 Codex Reviewer；不得预写 Verdict、ACCEPTED、merge 或 DONE。TASK-014 继续 `BLOCKED/UNASSIGNED`。
4. 动态 Reviewer authorization 必须解析为本次提交；提交信息为 `docs: authorize TASK-013 correction 1 review`。
5. 不运行 uv、pytest、mypy、Ruff、build、imports、数据库、网络、模型、媒体、Vault、凭据或任何产品命令。
