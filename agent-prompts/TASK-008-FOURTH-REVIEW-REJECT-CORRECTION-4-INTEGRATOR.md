# TASK-008 第四轮审查拒绝与 Correction 4 同步 — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@3c2b6cf4fc11ea20ecdfc3ba9e9b8de58a22c83d`，必须干净且为唯一父基线。
- Source：`/Users/hua/Documents/yia-worktrees/task-008` / `codex/task-008-deep-analysis@19323923057adb0b5a9f59cac5eb7c32cce5888a`，必须干净且无 `.codebase-memory/` 或其他未跟踪工件。
- Reviewer-4 evidence：`19323923057adb0b5a9f59cac5eb7c32cce5888a` 唯一父为 Correction 3 `7a543d0acfe25d1c3d9fd06c4647683ed1487a47`；evidence 只改 `handoffs/TASK-008.md`。
- Original base：`473119704c7638d7afd4e68d84d00e85064ceabd`；完整 Diff 仅为 TASK-008 七个批准路径组中的六个实际路径。
- Source 的任务/项目状态为分配前冻结快照；实时状态仅以 main 本提交为准。

## 审查拒绝事实

- Verdict=`REJECT`；P0=0、P1=1。Reviewer 在首个 P1 停止，未运行全量、build 或其余探针；不得写为通过。
- P1：持久化缓存恢复只以 `ProviderCallStatus.SUCCEEDED` 接受缓存，未校验两类 Artifact 的存在、元数据及内容 SHA-256，也未校验恢复结构化结果的 request hash、provider、model 与本次规范 `ProviderCallRequest` 一致。篡改 structured Artifact 内的 `request_hash` 后仍会推进 `SCORED -> ANALYSIS_READY` 并完成 Job。
- ADR-008 A-06 要求请求 hash、Provider、模型、版本、Artifact 内容 hash 和成功 Provider call 全部匹配，才可命中缓存。任一不匹配必须安全失败、不得推进 Pipeline/Job、不得触发 credential、transport、新 ProviderCall 或新 Artifact。

## 唯一允许提交范围

1. `agent-prompts/TASK-008-FOURTH-REVIEW-REJECT-CORRECTION-4-INTEGRATOR.md`
2. `agent-prompts/TASK-008-CORRECTION-4-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-008-deep-analysis.md`

不得访问或修改 TASK-009 source/worktree，也不得暂存产品代码、依赖、锁、Schema、迁移或 handoff。

## 必须执行

1. 核验 main/source branch、HEAD、父链、身份 `Mozhu <huangbuqubunao@gmail.com>`、`user.useConfigOnly=true`、empty index/worktree、evidence 单文件范围和完整 source 范围。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、凭据或任何产品文件 I/O 命令。
4. main 将 TASK-008 退回原 Codex Implementer 的 `IN_PROGRESS`，冻结 Correction 4；不得预写 Reviewer verdict、ACCEPTED、merge 或 DONE。TASK-009 必须保持 `IN_PROGRESS` 且未触碰。
5. 提交信息：`docs: return TASK-008 for cache integrity correction`。提交后 main/source 必须干净，并确认 Correction prompt 的动态授权解析为本提交。

## Correction 4 边界

- 只授权 source `analysis.py`、`tests/integration/test_summary_provider.py` 和 `handoffs/TASK-008.md`。
- 在现有公开契约和 Repository API 内，于缓存恢复的任何 `complete_stage` 前验证：成功 ProviderCall 的请求身份；`ANALYSIS_RAW` 与结构化分析 Artifact 的存在、预期 kind/retention/关联和 `content_hash`；磁盘内容散列；以及解析结果的 request hash、provider、model 与当前请求完全匹配。不得自行扩展 Schema、Repository 或公共契约。
- 任一缓存证据缺失、篡改、散列或身份不匹配必须 fail-closed，返回现有安全错误，不推进 Pipeline/Job，不读取凭据，不调用 transport，不创建/失败化 ProviderCall，也不写 Artifact。保留完全匹配缓存的零 credential/transport/新 call/new Artifact 与 ADR-008 A-12 `complete_stage` 恢复语义。
- 新增真实临时 SQLite + Fake Resolver/transport 回归：分别篡改 structured request hash、raw/structured 文件内容或哈希、Provider/model、缺失任一 Artifact；逐项断言零外部/新持久化副作用和状态不推进。保留既有关闭、低价值、token、预算、缺凭据、成功、回滚、重排、RAW_RESPONSE_30D、SDK 隔离回归。
- 不得新增依赖/锁、配置/共享契约、`state.py`、Schema/migration、CLI 或真实 OpenAI/密钥/付费/API/网络/云端 token-count/用户内容/媒体/YouTube/Vault/测试目录外 I/O。

## 回传格式

```text
Task: TASK-008 fourth review reject / Correction 4 sync
Base / Head: <base> -> <head>
Source/evidence/status: <chain>; TASK-008=IN_PROGRESS
Committed files: <exact five>
Checks: <git-only gates>
TASK-009 untouched: yes
Verdict: INTEGRATED | BLOCKED
Remaining risks: <P1 / unauthorized paths>
```
