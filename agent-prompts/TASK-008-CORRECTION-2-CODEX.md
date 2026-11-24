# TASK-008 Correction 2 — Codex Implementer

你是原 TASK-008 Codex Implementer。只修复独立审查发现的预算门禁 P1；不得重构、合并、推送、修改任务状态或接触任何真实资源。

## 动态授权与固定对象

- Main authorization：`git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-008-CORRECTION-2-CODEX.md` 必须解析为本 Correction 2 控制面提交，且 main 中 TASK-008=`IN_PROGRESS`。
- Worktree/branch：`/Users/developer/Documents/yia-worktrees/task-008` / `codex/task-008-deep-analysis`。
- 起始 source HEAD：`02317f2bc53f4a7e3dcc5ed7210da74f4129c7bf`，唯一父为 Correction 1 `8317cd9c2a13f6c38fa366ab9f40c326e59d8731`；worktree 必须干净，不能有 `.codebase-memory/` 或其他工件。
- 分配前 base：`473119704c7638d7afd4e68d84d00e85064ceabd`。source 任务卡/项目状态的旧 `BLOCKED/UNASSIGNED` 是历史快照；不得修改它们。

## 唯一允许修改

- `src/youtube_intel/analysis.py`
- `tests/integration/test_summary_provider.py`
- `handoffs/TASK-008.md`

禁止 Provider、prompt、fixture、依赖/锁、共享契约、配置、`state.py`、Schema/migration、CLI、TASK-009 或 main 变更。不要在 source 运行会写入 `.codebase-memory/` 的索引动作。

## P1 与完成标准

持久化分析路径在预算已耗尽时，必须在 ProviderCall 预留、CredentialResolver、Provider/transport 与所有 Repository 写入前按固定门禁顺序返回 `AnalysisSkipped(BUDGET_EXHAUSTED)`。不得留下 `PENDING` ProviderCall，或调用凭据解析器；不得消费、回滚或重置预算来改变既有语义。

用临时 SQLite + Fake Provider/Resolver 回归证明普通合成字幕且预算预先耗尽时：Resolver=0、transport=0、ProviderCall/Artifact=None、Pipeline=`SCORED`、已领取 Job=`RUNNING`。保留 token 超限、成功、回滚、重排和 RAW_RESPONSE_30D 行为。

## 强制验证

运行任务卡全部离线命令：lock check、locked sync、两组 focused tests、全量 pytest、mypy、Ruff、CLI help、offline build、sdist/wheel migration/prompt/fixed-tokenizer inclusion、`git diff --check 473119704c7638d7afd4e68d84d00e85064ceabd...HEAD`。审查完整 diff；记录复用和未授权路径未运行。

仅限离线 Fake/合成哨兵、临时 SQLite。严禁真实 OpenAI、密钥、付费/API、网络、云端 token-count、用户内容、媒体、YouTube、Vault 或测试目录外文件操作。

完成后追加 source handoff，创建一个单父提交，父提交严格为 `02317f2...`，并回报 SHA、范围、检查与剩余风险；不得启动 Reviewer 或修改状态。
