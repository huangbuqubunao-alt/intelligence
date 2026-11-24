# TASK-013 rebuild — ACCEPTED / Product Integrator 授权（Status Integrator）

你是 Status Integrator。只提交本次 ACCEPTED 状态与 Product Integrator 授权的控制面 Markdown；不得运行产品测试、`uv`、构建、网络、导入产品包或数据库命令，不得修改 source、合并、推送、启动 Integrator、rebase、reset 或清理任何 worktree。

## 固定对象与 Git 门禁

- main 必须为 `main@d7e1fe8793b8d446257a8a6a0ad5ce88a39bde87`，开始时干净且是本控制面提交的唯一父基线。
- 唯一 accepted source 为 `/Users/developer/Documents/yia-worktrees/task-013-rebuild` / `codex/task-013-e2e-acceptance-rebuild@d76307fcde73631931f61493c30c75dbda02f028`，开始与提交后必须干净。
- 从该 source 的 `git log -- handoffs/TASK-013.md` 精确解析最新 handoff-only Reviewer evidence `d76307fcde73631931f61493c30c75dbda02f028`；其唯一父提交必须为 `f6697fa3064c288a7b688d7dd1fdf82f5d3e2c28`，且本提交只能修改 `handoffs/TASK-013.md`。Verdict=`APPROVE`，P0–P3=0。
- 相对 rebuild base `2a59dfe3860161a5989f2c08161f03c73aa4ca86`，完整产品范围仅为原五组：`tests/e2e/test_mvp_flow.py`、`tests/e2e/test_failure_recovery.py`、`tests/e2e/fixtures/**`、`docs/ACCEPTANCE_REPORT.md`、`handoffs/TASK-013.md`；当前实际路径为前两份 E2E、验收报告和 handoff，fixtures 未改。`pyproject.toml` 与 `uv.lock` 不得改变。
- 核验 Git 身份、`user.useConfigOnly=true`、main/source identity、父链、两个工作区清洁、handoff-only evidence、完整产品范围、锁文件与 `git diff --check`。本角色只运行 Git/文档门禁。

## 唯一允许提交范围

1. `agent-prompts/TASK-013-REBUILD-ACCEPTANCE-INTEGRATION-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-013-REBUILD-INTEGRATOR.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-013-e2e-acceptance.md`

将 TASK-013 设为 `ACCEPTED`，固定 accepted source 和 Reviewer `APPROVE` 证据；不得写 `DONE`、预写 merge SHA 或声称已经整合。TASK-014 继续为 `BLOCKED`。

## Product Integrator 冻结授权

- Product Integrator 动态读取本次授权提交，并确认 main TASK-013=`ACCEPTED`。
- 只能将固定 accepted source `d76307fcde73631931f61493c30c75dbda02f028` 用 `git merge --no-ff` 合并至本次授权 main 基线；不得 rebase、cherry-pick、push、改 source、改任务状态或修复合并冲突以外的问题。
- 合并前后必须核验原五组产品范围、锁文件不变、双父顺序为 execution base + accepted source、accepted source 为 main 祖先、first-parent Diff 无越界。
- 合并结果必须复跑离线 E2E、全量 pytest、mypy、Ruff、CLI help、离线 build 及凭据格式扫描；锁定同步只能离线。真实 YouTube、模型、云 API、网络、媒体、凭据、真实 Vault/用户笔记、付费服务和 launchd 继续未授权。

对五个准备文件做两轮 SHA-256、LF/EOF、无尾随空白、精确暂存与 `git diff --cached --check`；提交信息使用 `docs: accept and authorize TASK-013 integration`。记录提交 SHA，但不启动 Integrator。
