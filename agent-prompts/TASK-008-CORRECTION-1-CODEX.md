# TASK-008 Correction 1 — Codex Implementer

你是原 TASK-008 Codex Implementer。只修复独立审查发现的 P1；不做重构、合并、推送、任务状态修改或任何真实资源操作。

## 动态授权与固定对象

- Main authorization：`git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-008-CORRECTION-1-CODEX.md` 必须解析为本 Correction 1 控制面提交，且 main 中 TASK-008=`IN_PROGRESS`。
- Worktree/branch：`/Users/developer/Documents/yia-worktrees/task-008` / `codex/task-008-deep-analysis`。
- 起始 source HEAD：`b61f46f6bca3303d5590aac76d8c8c9b53ec4131`，唯一父为 reviewed implementation `10478a9083df4eedae061d99d941c88cb4954179`；worktree 必须干净。
- 分配前 base：`473119704c7638d7afd4e68d84d00e85064ceabd`。source 任务卡/项目状态的旧 `BLOCKED/UNASSIGNED` 是历史快照；不得修改它们。

## 唯一允许修改

- `src/youtube_intel/analysis.py`
- `tests/unit/test_analysis_policy.py`
- `tests/integration/test_summary_provider.py`
- `handoffs/TASK-008.md`

除本 P1 必需的最小修复外，禁止 `cloud_llm.py`、prompt、fixture、依赖/锁、共享契约、配置、`state.py`、Schema/migration、CLI、TASK-009 或 main 变更。

## P1 与完成标准

`RepositoryBackedAnalysisService.analyze` 必须在任何 CredentialResolver 调用、Provider/transport 调用或 Repository 写入之前，执行与非持久化路径相同的确定性本地 token 上限判断。超过 `max_local_input_tokens_per_video` 的输入必须零 credential、零 provider/transport、零持久化副作用，并返回已冻结的本地 token-limit 结果；不得依赖远端 token-count。

用临时 SQLite + Fake Provider/Resolver 回归证明 `max_local_input_tokens_per_video=1` 和普通合成 transcript 时：credential call count 为 0、provider/transport call count 为 0、无 ProviderCall/Artifact/Pipeline/Job 写入。保留原成功、预算、缓存、凭据最后读取、回滚、重排和 RAW_RESPONSE_30D 行为。

## 强制验证

运行任务卡全部离线命令：lock check、locked sync、两组 focused tests、全量 pytest、mypy、Ruff、CLI help、offline build、sdist/wheel migration inclusion、`git diff --check 473119704c7638d7afd4e68d84d00e85064ceabd...HEAD`。审查所有完整 diff；记录复用和未授权资源未运行。

仅限离线 Fake/合成哨兵、临时 SQLite。严禁真实 OpenAI、密钥、付费/API、网络、云端 token-count、用户内容、媒体、YouTube、Vault 或测试临时目录外文件操作。

完成后追加 source handoff，创建一个单父提交，父提交严格为 `b61f46f...`，并回报 SHA、范围、检查与剩余风险；不得启动 Reviewer 或修改状态。
