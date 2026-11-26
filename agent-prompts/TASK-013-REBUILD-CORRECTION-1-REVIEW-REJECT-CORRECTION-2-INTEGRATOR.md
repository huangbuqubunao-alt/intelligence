# TASK-013 rebuild Correction 1 review reject / Correction 2 authorization — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、修改 source、启动 Implementer、合并、推送或清理。

## 固定对象

- Main base：`main@001eaa96dfc1737169323a3e4503a9415b0b39c9`，必须干净且为唯一父基线。
- Rejected review evidence：`/Users/developer/Documents/yia-worktrees/task-013-rebuild` / `codex/task-013-e2e-acceptance-rebuild@4aecab7c3f88f0a108ee815c05436d12dd0dfdd8`，开始时必须干净；唯一父提交为 Correction 1 `ae724990f6f3628a054bfca000e9e28d83f3def7`，且只修改 `handoffs/TASK-013.md`。
- Verdict=`REJECT`，P1-1：评分失败后的新组合仍读取旧 `_OfflineMvpFlow` 的内存 `transcripts`、`scores`、`analyses`，无法仅凭持久 SQLite/Artifact 从 `TRANSCRIPT_READY` 与 `RETRY_PENDING` 恢复。
- 历史 `/Users/developer/Documents/yia-worktrees/task-013` / `codex/task-013-e2e-acceptance` 是已拒绝审计证据，禁止访问、修改或清理。

## 唯一允许提交范围

1. `agent-prompts/TASK-013-REBUILD-CORRECTION-1-REVIEW-REJECT-CORRECTION-2-INTEGRATOR.md`
2. `agent-prompts/TASK-013-REBUILD-CORRECTION-2-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-013-e2e-acceptance.md`

## 必须执行

1. 核验 main/source identity、`user.useConfigOnly=true`、父链、洁净度、review evidence handoff-only 范围、完整产品范围、锁文件不变和 Diff 空白检查。
2. 对五个准备文件做两轮 SHA-256、LF/EOF、无尾随空白、精确暂存范围和 `git diff --cached --check`；任何字节漂移立即停止。
3. main 将 TASK-013 设为 `IN_PROGRESS`，退回原 Codex Implementer；不得预写 Reviewer verdict、ACCEPTED、merge 或 DONE。TASK-014 继续 `BLOCKED/UNASSIGNED`。
4. Correction 2 产品范围冻结为原五个路径组：`tests/e2e/test_mvp_flow.py`、`tests/e2e/test_failure_recovery.py`、`tests/e2e/fixtures/**`、`docs/ACCEPTANCE_REPORT.md`、`handoffs/TASK-013.md`。
5. 提交信息：`docs: return TASK-013 for failed-stage restart recovery`。不运行 uv、pytest、mypy、Ruff、build、imports、数据库、网络、模型、媒体、Vault、凭据或任何产品命令。
