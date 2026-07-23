# TASK-008 Correction 5 — Codex Implementer

你是原 TASK-008 Codex Implementer。只修复独立审查发现的隔离 SDK 子进程 timeout/退出收口 P1；不得重构、合并、推送、修改任务状态或接触任何真实资源。

## 动态授权与固定对象

- Main authorization：`git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-008-CORRECTION-5-CODEX.md` 必须解析为本 Correction 5 控制面提交，且 main 中 TASK-008=`IN_PROGRESS`。
- Worktree/branch：`/Users/hua/Documents/yia-worktrees/task-008` / `codex/task-008-deep-analysis`。
- 起始 source HEAD：`78ae101786ada5f04d2b7c734c84a216f8820803`，唯一父为 Correction 4 `bb195a59ddee25cb804b0078676c504e94c44441`；worktree 必须干净，不能有 `.codebase-memory/` 或其他工件。
- 分配前 base：`473119704c7638d7afd4e68d84d00e85064ceabd`。source 任务卡/项目状态的旧 `BLOCKED/UNASSIGNED` 是历史快照；不得修改它们。

## 唯一允许修改

- `src/youtube_intel/providers/cloud_llm.py`
- `tests/integration/test_summary_provider.py`
- `handoffs/TASK-008.md`

禁止 `analysis.py`、prompt、fixture、unit test、依赖/锁、共享契约、配置、`state.py`、Schema/migration、CLI、TASK-009 或 main 变更。不要在 source 运行会写入 `.codebase-memory/` 的索引动作。

## P1 与完成标准

隔离 SDK child 的 handshake、请求写入/flush、response read 和 exit 必须在同一有限 deadline 内完成；禁止无期限 `readline()`。任何 timeout、EOF、畸形 response、写入失败、非零退出或异常，均须关闭管道、终止并 reap child，返回既有安全、脱敏的 Adapter/AppError；不得泄露 response body、credential 或本地路径，不得留下 child 或后台线程。

保持 A-17 冻结策略：SDK 仍只在白名单环境子进程导入；主进程不导入 SDK；credential 不入环境、命令行、文件或日志；不做真实 API/密钥读取。

以离线 Fake child/Popen seam 覆盖至少：永不 handshake、handshake 后永不 response、EOF、畸形 JSON、nonzero exit、normal response。每个失败断言有限 timeout、`kill`/`terminate` 与 `wait` 的 reap 行为，以及现有安全错误映射。保留 Structured Outputs、错误脱敏、缓存完整性、A-03 门禁、成功/回滚/重排与 retention 回归。

若现有依赖和公开 Adapter 契约不能安全表达此收口，停止并报告 `DECISION NEEDED`；不得新增依赖、公共参数或线程池。

## 强制验证

运行任务卡全部离线命令：lock check、locked sync、两组 focused tests、全量 pytest、mypy、Ruff、CLI help、offline build、sdist/wheel migration/prompt/fixed-tokenizer inclusion、`git diff --check 473119704c7638d7afd4e68d84d00e85064ceabd...HEAD`。审查完整 diff；记录复用和未授权路径未运行。

仅限离线 Fake/合成哨兵、临时 SQLite。严禁真实 OpenAI、密钥、付费/API、网络、云端 token-count、用户内容、媒体、YouTube、Vault 或测试目录外文件操作。

完成后追加 source handoff，创建一个单父提交，父提交严格为 `78ae101786ada5f04d2b7c734c84a216f8820803`，并回报 SHA、范围、检查与剩余风险；不得启动 Reviewer 或修改状态。
