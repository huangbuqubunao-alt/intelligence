# TASK-008 Correction 4 — Codex Implementer

你是原 TASK-008 Codex Implementer。只修复独立审查发现的持久化缓存完整性 P1；不得重构、合并、推送、修改任务状态或接触任何真实资源。

## 动态授权与固定对象

- Main authorization：`git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-008-CORRECTION-4-CODEX.md` 必须解析为本 Correction 4 控制面提交，且 main 中 TASK-008=`IN_PROGRESS`。
- Worktree/branch：`/Users/developer/Documents/yia-worktrees/task-008` / `codex/task-008-deep-analysis`。
- 起始 source HEAD：`19323923057adb0b5a9f59cac5eb7c32cce5888a`，唯一父为 Correction 3 `7a543d0acfe25d1c3d9fd06c4647683ed1487a47`；worktree 必须干净，不能有 `.codebase-memory/` 或其他工件。
- 分配前 base：`473119704c7638d7afd4e68d84d00e85064ceabd`。source 任务卡/项目状态的旧 `BLOCKED/UNASSIGNED` 是历史快照；不得修改它们。

## 唯一允许修改

- `src/youtube_intel/analysis.py`
- `tests/integration/test_summary_provider.py`
- `handoffs/TASK-008.md`

禁止 Provider、prompt、fixture、unit test、依赖/锁、共享契约、配置、`state.py`、Schema/migration、CLI、TASK-009 或 main 变更。不要在 source 运行会写入 `.codebase-memory/` 的索引动作。

## P1 与完成标准

在既有缓存恢复路径调用 `complete_stage` 前，必须确认缓存为 ADR-008 A-06 所定义的完整匹配成功缓存：

1. 成功的 ProviderCall 与本次规范请求 identity（request hash、provider、model、冻结版本）相同；
2. `ANALYSIS_RAW` 与结构化分析 Artifact 都存在，关联/kind/retention/元数据正确，索引 `content_hash` 与实际文件 SHA-256 相符；
3. 结构化结果可安全解析，且其 request hash、provider、model 与本次请求相同。

任一缺失、篡改、hash/身份不匹配必须 fail-closed：安全错误、Pipeline/Job 不变、Resolver/transport=0、无新增或失败化 ProviderCall、无 Artifact 写入。不得把这些失败降级为重新调用云端。仅完全匹配缓存可以保持零 Resolver/transport/新 call/Artifact，并按 ADR-008 A-12 以既有 `complete_stage` 原子恢复当前 `SCORED -> ANALYSIS_READY` Job。

用真实临时 SQLite + Fake Resolver/transport 覆盖：篡改 structured request hash、raw/structured 文件内容、Artifact hash、Provider/model、缺失 raw 或 structured Artifact；每个反例须证明 fail-closed 和零副作用。保留关闭、低价值、token、预算、缺凭据、成功、回滚、重排、RAW_RESPONSE_30D、SDK 隔离与现有缓存恢复回归。

若既有接口不能安全验证任一 required identity 而必须扩展公共契约、Schema 或 Repository API，停止并报告 `DECISION NEEDED`；不得自行扩大范围。

## 强制验证

运行任务卡全部离线命令：lock check、locked sync、两组 focused tests、全量 pytest、mypy、Ruff、CLI help、offline build、sdist/wheel migration/prompt/fixed-tokenizer inclusion、`git diff --check 473119704c7638d7afd4e68d84d00e85064ceabd...HEAD`。审查完整 diff；记录复用和未授权路径未运行。

仅限离线 Fake/合成哨兵、临时 SQLite。严禁真实 OpenAI、密钥、付费/API、网络、云端 token-count、用户内容、媒体、YouTube、Vault 或测试目录外文件操作。

完成后追加 source handoff，创建一个单父提交，父提交严格为 `19323923057adb0b5a9f59cac5eb7c32cce5888a`，并回报 SHA、范围、检查与剩余风险；不得启动 Reviewer 或修改状态。
