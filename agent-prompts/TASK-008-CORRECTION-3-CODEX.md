# TASK-008 Correction 3 — Codex Implementer

你是原 TASK-008 Codex Implementer。只修复独立审查发现的持久化策略顺序 P1；不得重构、合并、推送、修改任务状态或接触任何真实资源。

## 动态授权与固定对象

- Main authorization：`git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-008-CORRECTION-3-CODEX.md` 必须解析为本 Correction 3 控制面提交，且 main 中 TASK-008=`IN_PROGRESS`。
- Worktree/branch：`/Users/hua/Documents/yia-worktrees/task-008` / `codex/task-008-deep-analysis`。
- 起始 source HEAD：`b380a8c87d99a3d2dbf88b28bde3ec5b0de4da0f`，唯一父为 Correction 2 `71e1c24936b0ed1be3a98c49efa7770f7456d85c`；worktree 必须干净，不能有 `.codebase-memory/` 或其他工件。
- 分配前 base：`473119704c7638d7afd4e68d84d00e85064ceabd`。source 任务卡/项目状态的旧 `BLOCKED/UNASSIGNED` 是历史快照；不得修改它们。

## 唯一允许修改

- `src/youtube_intel/analysis.py`
- `tests/unit/test_analysis_policy.py`
- `tests/integration/test_summary_provider.py`
- `handoffs/TASK-008.md`

禁止 Provider、prompt、fixture、依赖/锁、共享契约、配置、`state.py`、Schema/migration、CLI、TASK-009 或 main 变更。不要在 source 运行会写入 `.codebase-memory/` 的索引动作。

## P1 与完成标准

持久化路径必须严格执行 ADR-008 A-03：验证上游高价值/Pipeline/Job/规范字幕有效性 → 云端关闭 → 最小输入、本地采样/token、缓存 → run 预算 → CredentialResolver → ProviderCall 预留/单次推理。不得在任一零调用门禁前预留、读取凭据、调用 transport 或写入 Artifact/Pipeline/Job。

用真实临时 SQLite + Fake Resolver/transport 覆盖关闭、低价值、缓存命中、预算耗尽、本地 token 超限、缺凭据。除缓存重排外，每条均断言 Resolver=0、transport=0、ProviderCall/Artifact=None、Pipeline/Job 不变；缺凭据必须返回既有冻结 `CREDENTIAL_UNAVAILABLE`，不得调用 `fail_provider_call`。缓存命中也必须零 Resolver、零 transport、零新 ProviderCall/Artifact；若当前 Job 尚未完成，可复用已成功的匹配 ProviderCall/Artifact，调用既有 `complete_stage` 原子推进 `SCORED -> ANALYSIS_READY`，这是 ADR-008 A-12 的既有恢复语义。保留无效上游硬错误、成功、回滚、重排、RAW_RESPONSE_30D、SDK 隔离与既有 token/预算行为。

若没有修改公共契约就无法表达现有冻结的高价值/上游资格判断，停止并报告 `DECISION NEEDED`；不得自行添加参数、Schema 或 Repository 方法。

## 强制验证

运行任务卡全部离线命令：lock check、locked sync、两组 focused tests、全量 pytest、mypy、Ruff、CLI help、offline build、sdist/wheel migration/prompt/fixed-tokenizer inclusion、`git diff --check 473119704c7638d7afd4e68d84d00e85064ceabd...HEAD`。审查完整 diff；记录复用和未授权路径未运行。

仅限离线 Fake/合成哨兵、临时 SQLite。严禁真实 OpenAI、密钥、付费/API、网络、云端 token-count、用户内容、媒体、YouTube、Vault 或测试目录外文件操作。

完成后追加 source handoff，创建一个单父提交，父提交严格为 `b380a8c...`，并回报 SHA、范围、检查与剩余风险；不得启动 Reviewer 或修改状态。
