# TASK-008 Correction 1 审查授权同步 — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@33ab12dc8abe6267c8c011c85822e34c6fbc8274`，必须干净且为唯一父基线。
- Source：`/Users/developer/Documents/yia-worktrees/task-008` / `codex/task-008-deep-analysis@8317cd9c2a13f6c38fa366ab9f40c326e59d8731`，必须干净。
- Correction：`8317cd9...` 唯一父为 review evidence `b61f46f6bca3303d5590aac76d8c8c9b53ec4131`；Correction 仅改 `analysis.py`、`test_summary_provider.py` 和 `handoffs/TASK-008.md`。
- Original base：`473119704c7638d7afd4e68d84d00e85064ceabd`；完整 Diff 仅为 TASK-008 七个批准路径组中的六个实际路径，且无依赖/锁、共享契约、`state.py`、Schema/migration、CLI、TASK-009 改动。
- Source 的任务/项目状态是固定 base 的历史快照；实时状态只能以 main 本提交中 TASK-008=`IN_REVIEW` 为准。

## Correction 关闭目标

- 首轮 evidence `b61f46f...` 为 `REJECT`，P1=1：持久化路径在 token 超限时读取凭据并调用 Fake transport。
- Correction 声称在 SQLite、凭据、Provider/transport 之前完成同一确定性本地 token gate；临时 SQLite/Fake 证明 max token=`1` 时 Resolver=0、transport=0、无 ProviderCall/Artifact，Pipeline 保持 `SCORED`、Job 保持 `RUNNING`。
- 这些只是 Implementer 自报，必须由新 Reviewer 独立复跑；不得预写 `APPROVE`、`ACCEPTED`、merge 或 `DONE`。

## 唯一允许提交范围

1. `agent-prompts/TASK-008-CORRECTION-1-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-008-REVIEWER-2-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-008-deep-analysis.md`

不得访问或修改 TASK-009 source/worktree，也不得暂存产品代码、依赖、锁、Schema、迁移或 handoff。

## 必须执行

1. 核验 main/source branch、HEAD、父链、身份 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、干净 index/worktree、Correction 三路径及完整范围。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 和精确暂存范围必须通过；字节漂移立即停止。
3. 不运行 uv、pytest、build、import、数据库、网络、模型、Vault、凭据或文件删除命令。
4. main 将 TASK-008 标为 `IN_REVIEW`，授权全新独立 Reviewer 2；TASK-009 继续 `IN_REVIEW` 且不触碰。
5. 提交信息：`docs: authorize TASK-008 token gate review`。提交后 main/source 必须干净，并确认 Reviewer 2 prompt 的动态授权解析为本提交。

## 回传格式

```text
Task: TASK-008 Correction 1 review authorization sync
Base / Head: <base> -> <head>
Source/correction/status: <chain>; TASK-008=IN_REVIEW
Committed files: <exact five>
Checks: <git-only gates>
TASK-009 untouched: yes
Verdict: INTEGRATED | BLOCKED
Remaining risks: <P1 verification / unauthorized paths>
```
