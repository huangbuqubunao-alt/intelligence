# TASK-008 验收与最终整合授权同步 — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@da535fb9cf337e37d8179862e2086015166d0c3f`，必须干净且为唯一父基线。
- Accepted source：`/Users/developer/Documents/yia-worktrees/task-008` / `codex/task-008-deep-analysis@6914312eaac0e3d65f1d2895ea2e3c0c2c39f4d8`，必须干净且无 `.codebase-memory/` 或其他未跟踪工件。
- Reviewer-6 evidence：唯一父为 Correction 5 `dcbbd38fe8bab79fd6db1679f43a8ca48fb472ea`，仅修改 source handoff，Verdict=`APPROVE`，P0–P3=0。
- Original base：`473119704c7638d7afd4e68d84d00e85064ceabd`；完整 source Diff 精确为六个实际批准路径：`analysis.py`、`providers/cloud_llm.py`、`prompts/summary.md`、两份既定测试、source handoff。
- Source 的任务/项目状态为分配前冻结快照；实时状态仅以 main 本提交为准。

## 审查结论与整合门禁

- Reviewer 6 独立复跑：locked sync、focused=`4/30`、full pytest=`361`、mypy、Ruff、CLI、offline build、sdist/wheel prompt/fixed-tokenizer/migration inclusion、Diff/范围检查均 PASS。
- A-03 零副作用与 A-06 缓存完整性、A-17 隔离 child 有限 deadline/terminate/reap，以及成功、回滚、重排、RAW_RESPONSE_30D 等离线探针均通过；真实 OpenAI、凭据、网络、付费、Vault/用户内容仍未运行且未授权。
- Product Integrator 只可在本提交后按固定 source 执行 `--no-ff` merge、重跑 TASK-008 离线门禁和 package inclusion；不得修代码或扩大范围。TASK-008 只能设为 `ACCEPTED`，不得提前写 merge SHA 或 `DONE`。

## 唯一允许提交范围

1. `agent-prompts/TASK-008-ACCEPTANCE-INTEGRATION-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-008-INTEGRATOR.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-008-deep-analysis.md`

不得访问或修改 TASK-009 source/worktree，也不得暂存产品代码、依赖、锁、Schema、迁移或 handoff。

## 必须执行

1. 核验 main/source branch、HEAD、父链、身份 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、empty index/worktree、review handoff-only evidence 和完整 source 范围。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、凭据或任何产品文件 I/O 命令。
4. main 将 TASK-008 设为 `ACCEPTED`，记录 Reviewer 6 `APPROVE`；不得预写 merge SHA 或 `DONE`。TASK-009 必须保持 `IN_PROGRESS` 且未触碰。
5. 提交信息：`docs: accept and authorize TASK-008 integration`。提交后 main/source 必须干净，并确认 Integrator prompt 的动态授权解析为本提交。

## 回传格式

```text
Task: TASK-008 acceptance / final integration authorization sync
Base / Head: <base> -> <head>
Review/source/status: <review SHA> APPROVE; TASK-008=ACCEPTED
Committed files: <exact five>
Checks: <git-only gates>
TASK-009 untouched: yes
Verdict: INTEGRATED | BLOCKED
Remaining risks: <real-resource / release risks>
```
