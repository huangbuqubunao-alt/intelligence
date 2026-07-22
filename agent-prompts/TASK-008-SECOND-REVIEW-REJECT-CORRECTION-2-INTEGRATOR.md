# TASK-008 第二轮审查拒绝与 Correction 2 同步 — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@5874f4569ced297b6b827735a44959bebc306243`，必须干净且为唯一父基线。
- Source：`/Users/hua/Documents/yia-worktrees/task-008` / `codex/task-008-deep-analysis@02317f2bc53f4a7e3dcc5ed7210da74f4129c7bf`，必须干净且无 `.codebase-memory/` 或其他未跟踪工件。
- Reviewer-2 evidence：`02317f2...` 唯一父为 Correction 1 `8317cd9c2a13f6c38fa366ab9f40c326e59d8731`；evidence 只改 `handoffs/TASK-008.md`。
- Original base：`473119704c7638d7afd4e68d84d00e85064ceabd`；完整 Diff 仅为 TASK-008 七个批准路径组中的六个实际路径。
- Source 的任务/项目状态为分配前冻结快照；实时状态仅以 main 本提交为准。

## 审查拒绝事实

- Verdict=`REJECT`；P0=0、P1=1。
- P1：持久化路径在预算已耗尽时先 `reserve_provider_call`、读取凭据，才调用预算 `try_consume()`；留下 `PENDING` ProviderCall。违反 ADR-008 A-03/A-07/A-08 的固定门禁顺序、零副作用和延迟密钥读取。
- Reviewer 2 的 lock/sync、focused `4/10`、full pytest `341`、mypy、Ruff、CLI、offline build、包资源检查均 PASS；发现 P1 后 B–E 探针停止，不得表述为通过。

## 唯一允许提交范围

1. `agent-prompts/TASK-008-SECOND-REVIEW-REJECT-CORRECTION-2-INTEGRATOR.md`
2. `agent-prompts/TASK-008-CORRECTION-2-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-008-deep-analysis.md`

不得访问或修改 TASK-009 source/worktree，也不得暂存产品代码、依赖、锁、Schema、迁移或 handoff。

## 必须执行

1. 核验 main/source branch、HEAD、父链、身份 `Mozhu <huangbuqubunao@gmail.com>`、`user.useConfigOnly=true`、empty index/worktree、evidence 单文件范围和完整 source 范围。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、凭据或任何产品文件 I/O 命令。
4. main 将 TASK-008 退回原 Codex Implementer 的 `IN_PROGRESS`，冻结 Correction 2；不得预写 Reviewer verdict、ACCEPTED、merge 或 DONE。TASK-009 必须保持 `IN_REVIEW` 且未触碰。
5. 提交信息：`docs: return TASK-008 for persistent budget correction`。提交后 main/source 必须干净，并确认 Correction prompt 的动态授权解析为本提交。

## Correction 2 边界

- 只授权 source `analysis.py`、`tests/integration/test_summary_provider.py` 和 `handoffs/TASK-008.md`。
- 持久化路径必须在任何 ProviderCall 预留、CredentialResolver、Provider/transport、Artifact/Pipeline/Job 写入之前，按既有固定门禁顺序返回 `AnalysisSkipped(BUDGET_EXHAUSTED)`；不得消费、回滚或重置预算以规避该语义。
- 必须新增真实临时 SQLite + Fake Provider/Resolver 回归：预算预先耗尽时 Resolver=0、transport=0、ProviderCall/Artifact=None，Pipeline=`SCORED`、Job=`RUNNING`；保留 token 超限、成功、回滚、重排与 RAW_RESPONSE_30D 行为。
- 不得新增 Schema/migration/Repository 方法、依赖/锁、公共契约、配置、CLI 或真实 OpenAI/密钥/付费/API/网络/云端 token-count/用户内容/媒体/YouTube/Vault/测试目录外 I/O。若既有预算契约不足，报告 `DECISION NEEDED`。

## 回传格式

```text
Task: TASK-008 second review reject / Correction 2 sync
Base / Head: <base> -> <head>
Source/evidence/status: <chain>; TASK-008=IN_PROGRESS
Committed files: <exact five>
Checks: <git-only gates>
TASK-009 untouched: yes
Verdict: INTEGRATED | BLOCKED
Remaining risks: <P1 / unauthorized paths>
```
