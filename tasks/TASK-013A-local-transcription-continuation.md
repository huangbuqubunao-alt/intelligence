# TASK-013A：本地转写持续处理

- Status: `DONE`
- Assignee: `Codex Implementer`
- Owner role: Codex Implementer
- Size: M
- Risk: High
- Depends on: TASK-006, TASK-010
- Approval required: 仅离线 Fake executor、pytest 临时 SQLite/DATA 与既有锁定依赖；模型下载/加载、ffmpeg、媒体/YouTube、网络、真实 Vault、凭据和云端调用继续逐项禁止

## 分配

- Worktree: `/Users/developer/Documents/yia-worktrees/task-013a`
- Branch: `codex/task-013a-local-transcription-continuation`
- Base: `main@d96862f287d523dd524addf79f86c9b0642a4d31`
- Review: 实现提交后，必须由全新独立 Codex Reviewer 审查；不得预写 verdict、ACCEPTED、merge 或 DONE。
- Source: `codex/task-013a-local-transcription-continuation@62d87067af84171a2ee7195f3e7d4c4fddcb9980`（Reviewer 2 APPROVE evidence；parent `d50c78e9502e3f65018b6af323823c98b3a882ba`）。

## Correction 1

- Reviewer evidence: `08542b84d550ca225dece520cf748a2fc654ab58`，Verdict=`REJECT`。
- P1：缓存恢复未证明 canonical Artifact 来自同一视频、同一 pipeline version 且已成功的历史 TRANSCRIPT Job；篡改 `artifacts.job_id` 可推进错误的运行 Job。
- 修复范围仅为 `transcripts.py`、本地转写集成测试和 handoff；必须在 executor 或当前 Job/Pipeline 副作用前 fail-closed。
- Correction 1 已由第二位独立 Codex Reviewer 复跑 provenance 矩阵和全部离线门禁后 APPROVE。

## 验收

- Reviewer 2 evidence: `62d87067af84171a2ee7195f3e7d4c4fddcb9980`，Verdict=`APPROVE`，P0–P3=0。
- AC-1 至 AC-5 与 ADR-012 C-01 至 C-05 的离线矩阵均通过；未运行真实模型、媒体、网络、Vault 或凭据路径。
- 已由 merge `8f70fe34fdaf0788296cdb5aba22f70358462aac` 用 `--no-ff` 整合并关闭；不运行真实资源路径。

## 目标

让无字幕视频的本地 Whisper 转写成为真实、可恢复的 TRANSCRIPT 阶段结果：经验证的转写可供评分、分析、笔记和周报继续使用，而不是只停留在内存文本或测试专用状态。

## 范围

- 增加 Repository-backed 本地转写应用服务，复用既有 MLX Whisper Adapter、Artifact、Provider-call、`complete_stage`、Job/Pipeline 事务和安全 DATA 文件模式。
- 只接受已登记、未删除、哈希匹配、DATA 根内的音频 Artifact；成功后原子写入规范转写 Artifact、Provider-call 和 `METADATA_READY -> TRANSCRIPT_READY`。
- 覆盖缓存复用、身份/哈希/路径验证、阶段 CAS、数据库失败补偿、Fake executor 失败、成功后音频 cleanup 的 at-most-once 边界。

## 范围外

- 不新增依赖、Schema、migration、`state.py`、Pipeline 状态转换、CLI production composition 或真实资源调用。
- 不下载/加载模型，不调用 ffmpeg、媒体/YouTube、网络、Ollama/OpenAI、真实 Vault/用户笔记、凭据或付费服务。
- 不在本任务中重做 TASK-013 端到端验收；其将于本任务整合后重新分配。

## 验收标准

- [ ] 成功的 Fake Whisper 转写在一个既有阶段事务中形成可验证的规范转写 Artifact、Provider-call、Job 成功和 `TRANSCRIPT_READY`，后续评分服务可消费。
- [ ] 相同经验证音频、模型/版本、语言提示和参数策略命中缓存时，Fake executor 零调用且不会生成重复 Artifact/Provider-call。
- [ ] 音频/Artifact/Provider-call/Job/Pipeline 身份、文件哈希或路径不匹配时失败关闭，不推进 Pipeline 或删除外部文件。
- [ ] 数据库阶段完成失败不会留下可见的新转写文件，Provider-call 可按既有重试语义恢复；成功后的音频 cleanup 保留既有 at-most-once best-effort 边界。
- [ ] 默认离线检查、类型/Lint/构建和完整 Diff 均通过；不执行真实资源路径。

## 预计触达文件

- `src/youtube_intel/transcripts.py`
- `tests/integration/test_local_transcription_service.py`
- `tests/unit/test_transcription_policy.py`
- `handoffs/TASK-013A.md`

## 验证

- `uv lock --check`
- `uv sync --locked --offline`
- `uv run python -m pytest tests/integration/test_local_transcription_service.py`
- `uv run python -m pytest tests/unit/test_transcription_policy.py`
- `uv run python -m pytest`
- `uv run mypy src && uv run ruff check .`
- `uv run python -m youtube_intel --help`
- `uv build --offline`
- `git diff --check && git status --short`

## 交付证据

- Artifact/Provider-call/Job/Pipeline 原子完成与缓存恢复矩阵。
- 临时 SQLite/DATA 路径、哈希、失败补偿和 cleanup 边界。
- 复用与许可证：既有锁定 `mlx-whisper` Adapter 与 Python 标准库为 `DIRECT`；不新增依赖；真实模型许可和资源门禁仍由 TASK-014 跟踪。
