# TASK-008 第三轮审查拒绝与 Correction 3 同步 — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@07aa784629d353492f0546a4dfb114d72010b26f`，必须干净且为唯一父基线。
- Source：`/Users/hua/Documents/yia-worktrees/task-008` / `codex/task-008-deep-analysis@b380a8c87d99a3d2dbf88b28bde3ec5b0de4da0f`，必须干净且无 `.codebase-memory/` 或其他未跟踪工件。
- Reviewer-3 evidence：`b380a8c...` 唯一父为 Correction 2 `71e1c24936b0ed1be3a98c49efa7770f7456d85c`；evidence 只改 `handoffs/TASK-008.md`。
- Original base：`473119704c7638d7afd4e68d84d00e85064ceabd`；完整 Diff 仅为 TASK-008 七个批准路径组中的六个实际路径。
- Source 的任务/项目状态为分配前冻结快照；实时状态仅以 main 本提交为准。

## 审查拒绝事实与固定顺序

- Verdict=`REJECT`；P0=0、P1=1。
- P1：持久化 `RepositoryBackedAnalysisService` 在关闭/低价值/缺凭据门禁之前预留 ProviderCall；缺凭据会把 call 标记为可重试失败。违反 ADR-008 A-03/A-08 的零副作用与凭据最后读取。
- A-03 固定顺序：验证上游高价值/Pipeline/Job/规范字幕有效性；处理关闭；构造最小输入并完成本地采样、token 计算和缓存命中；检查 run 预算；最后读取凭据；最后才预留 ProviderCall/推理。关闭、缓存、低价值、超限、预算耗尽和缺凭据均不得调用 OpenAI，也不得产生 ProviderCall 或其他持久化副作用。
- Reviewer 3 在首个 P1 停止，未运行测试、build 与 B–E 探针；不得写为通过。

## 唯一允许提交范围

1. `agent-prompts/TASK-008-THIRD-REVIEW-REJECT-CORRECTION-3-INTEGRATOR.md`
2. `agent-prompts/TASK-008-CORRECTION-3-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-008-deep-analysis.md`

不得访问或修改 TASK-009 source/worktree，也不得暂存产品代码、依赖、锁、Schema、迁移或 handoff。

## 必须执行

1. 核验 main/source branch、HEAD、父链、身份 `Mozhu <huangbuqubunao@gmail.com>`、`user.useConfigOnly=true`、empty index/worktree、evidence 单文件范围和完整 source 范围。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、凭据或任何产品文件 I/O 命令。
4. main 将 TASK-008 退回原 Codex Implementer 的 `IN_PROGRESS`，冻结 Correction 3；不得预写 Reviewer verdict、ACCEPTED、merge 或 DONE。TASK-009 必须保持 `IN_PROGRESS` 且未触碰。
5. 提交信息：`docs: return TASK-008 for policy ordering correction`。提交后 main/source 必须干净，并确认 Correction prompt 的动态授权解析为本提交。

## Correction 3 边界

- 只授权 source `analysis.py`、`tests/unit/test_analysis_policy.py`、`tests/integration/test_summary_provider.py` 和 `handoffs/TASK-008.md`。
- 使用既有冻结输入/结果/Repository 契约，将持久化路径严格对齐 A-03；不得新增 public 参数、Schema、Repository 方法或改变无效上游硬错误语义。若既有契约无法表达上游高价值门禁，报告 `DECISION NEEDED`。
- 必须用真实临时 SQLite + Fake Resolver/transport 逐项覆盖关闭、低价值、缓存命中、预算耗尽、本地 token 超限、缺凭据。除缓存重排外，每条均 Resolver=0、transport=0、ProviderCall/Artifact=None，Pipeline/Job 不变；缺凭据返回冻结的 `CREDENTIAL_UNAVAILABLE`，不得 fail ProviderCall。缓存命中也必须 Resolver=0、transport=0、零新 ProviderCall/Artifact；但若当前 Job 尚未完成，可复用已成功的匹配 ProviderCall/Artifact，以既有 `complete_stage` 原子推进 `SCORED -> ANALYSIS_READY`，这是 ADR-008 A-12 允许的恢复状态变更。
- 保留成功、回滚、重排、RAW_RESPONSE_30D、SDK 隔离和已修复 token/预算回归。
- 不得新增依赖/锁、配置/共享契约、`state.py`、Schema/migration、CLI 或真实 OpenAI/密钥/付费/API/网络/云端 token-count/用户内容/媒体/YouTube/Vault/测试目录外 I/O。

## 回传格式

```text
Task: TASK-008 third review reject / Correction 3 sync
Base / Head: <base> -> <head>
Source/evidence/status: <chain>; TASK-008=IN_PROGRESS
Committed files: <exact five>
Checks: <git-only gates>
TASK-009 untouched: yes
Verdict: INTEGRATED | BLOCKED
Remaining risks: <P1 / unauthorized paths>
```
