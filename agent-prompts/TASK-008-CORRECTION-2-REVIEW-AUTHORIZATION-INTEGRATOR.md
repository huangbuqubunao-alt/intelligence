# TASK-008 Correction 2 审查授权同步 — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@14585b834b342b8db3b6d70730a1639fc2fb1eff`，必须干净且为唯一父基线。
- Source：`/Users/developer/Documents/yia-worktrees/task-008` / `codex/task-008-deep-analysis@71e1c24936b0ed1be3a98c49efa7770f7456d85c`，必须干净且无 `.codebase-memory/` 或其他未跟踪工件。
- Correction：`71e1c249...` 唯一父为 reviewer-2 evidence `02317f2bc53f4a7e3dcc5ed7210da74f4129c7bf`；Correction 仅改 `analysis.py`、`test_summary_provider.py` 与 `handoffs/TASK-008.md`。
- Original base：`473119704c7638d7afd4e68d84d00e85064ceabd`；完整 Diff 仅为 TASK-008 七个批准路径组中的六个实际路径，无依赖/锁、共享契约、`state.py`、Schema/migration、CLI、TASK-009 改动。
- Source 的任务/项目状态为分配前冻结快照；实时状态只能以 main 本提交中 TASK-008=`IN_REVIEW` 为准。

## Correction 关闭目标

- Reviewer-2 evidence `02317f2...` 为 `REJECT`：预算耗尽路径先预留 ProviderCall 并读取凭据，留下 `PENDING` 状态。
- Correction 自报在一切 Repository/credential/Provider 副作用前返回 `AnalysisSkipped(BUDGET_EXHAUSTED)`；临时 SQLite/Fake 证明 Resolver=0、transport=0、ProviderCall/Artifact=None、Pipeline=`SCORED`、Job=`RUNNING`。
- 这些只是 Implementer 自报，必须由新 Reviewer 独立复跑；不得预写 `APPROVE`、`ACCEPTED`、merge 或 `DONE`。

## 唯一允许提交范围

1. `agent-prompts/TASK-008-CORRECTION-2-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-008-REVIEWER-3-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-008-deep-analysis.md`

不得访问或修改 TASK-009 source/worktree，也不得暂存产品代码、依赖、锁、Schema、迁移或 handoff。

## 必须执行

1. 核验 main/source branch、HEAD、父链、身份 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、干净 index/worktree、Correction 三路径及完整范围。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 不运行 uv、pytest、build、import、数据库、网络、模型、Vault、凭据或文件删除命令。
4. main 将 TASK-008 标为 `IN_REVIEW`，授权全新独立 Reviewer 3；TASK-009 继续 `IN_PROGRESS` 且未触碰。
5. 提交信息：`docs: authorize TASK-008 budget gate review`。提交后 main/source 必须干净，并确认 Reviewer 3 prompt 的动态授权解析为本提交。

## 回传格式

```text
Task: TASK-008 Correction 2 review authorization sync
Base / Head: <base> -> <head>
Source/correction/status: <chain>; TASK-008=IN_REVIEW
Committed files: <exact five>
Checks: <git-only gates>
TASK-009 untouched: yes
Verdict: INTEGRATED | BLOCKED
Remaining risks: <P1 verification / unauthorized paths>
```
