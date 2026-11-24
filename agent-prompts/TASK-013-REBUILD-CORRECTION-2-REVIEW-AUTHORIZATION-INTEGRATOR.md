# TASK-013 rebuild — Correction 2 独立 Reviewer 授权（Status Integrator）

你是 Status Integrator。只创建本次 Reviewer 授权的控制面 Markdown 提交；不得运行产品测试、`uv`、构建、网络、导入产品包或数据库命令，不得修改 source、启动 Reviewer、合并、推送、rebase、reset 或清理任何 worktree。

## 固定谱系与预检

- main 必须为 `main@9b5c4b53537ba0dfd2319f849d5269a1a033c568`，且开始时干净。
- 唯一 source 为 `/Users/developer/Documents/yia-worktrees/task-013-rebuild` / `codex/task-013-e2e-acceptance-rebuild@f6697fa3064c288a7b688d7dd1fdf82f5d3e2c28`；开始及提交后必须干净。
- source 提交的唯一父提交必须精确为 `4aecab7c3f88f0a108ee815c05436d12dd0dfdd8`。禁止访问、修改或清理历史 `/Users/developer/Documents/yia-worktrees/task-013` worktree。
- 相对 `2a59dfe3860161a5989f2c08161f03c73aa4ca86`，source 产品 Diff 只能落在：`tests/e2e/test_mvp_flow.py`、`tests/e2e/test_failure_recovery.py`、`tests/e2e/fixtures/**`、`docs/ACCEPTANCE_REPORT.md`、`handoffs/TASK-013.md`；依赖/锁文件不得改变。
- 核验 Git 身份、`user.useConfigOnly=true`、分支/HEAD/父提交、两个工作区清洁状态、产品范围、锁文件、`git diff --check`。本角色不运行任何产品命令。

## 唯一控制面范围

本次提交只能新增或修改：

1. `agent-prompts/TASK-013-REBUILD-CORRECTION-2-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-013-REBUILD-CORRECTION-2-REVIEWER-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-013-e2e-acceptance.md`

将 TASK-013 设为 `IN_REVIEW`，分配给全新独立 Codex Reviewer；不得预写 `APPROVE`、`REJECT`、`ACCEPTED`、merge 或 `DONE`。TASK-014 继续为 `BLOCKED`。Reviewer 的动态 main 授权必须解析为本次提交。

## Reviewer 冻结授权

- Reviewer 只能在唯一 source 的 `handoffs/TASK-013.md` 追加审查证据，证据提交的唯一父提交必须为 `f6697fa3064c288a7b688d7dd1fdf82f5d3e2c28`；不得修改业务代码、测试、报告、任务卡、main 或其他 source 文件。
- Reviewer 必须独立验证评分失败后彻底销毁初次服务/Repository/Fake Provider/内存组合，并在同一临时 SQLite/DATA/Vault 上重建全新组合。新组合不得依赖旧 `_OfflineMvpFlow` 或任何旧内存 transcript、score、analysis、Repository、Fake Provider 或计数器。
- 审查必须验证新组合的字幕与 Whisper 昂贵调用均为 `0`，评分与必要分析各恰好一次，后续笔记和周报完成，稳定重跑无重复 Artifact、Provider-call、笔记或周报；不得直接推进 SQLite 状态、直接 `complete_stage`、直接 SQL 更新或伪造阶段完成。
- 真实 YouTube、模型、云 API、网络、媒体、凭据、真实 Vault/用户笔记、付费服务均未授权。

提交前后精确核对允许路径、内容哈希、LF/末尾换行、无尾随空白与 staged Diff；提交信息使用 `docs: authorize TASK-013 correction 2 review`。记录提交 SHA，但不启动 Reviewer。
