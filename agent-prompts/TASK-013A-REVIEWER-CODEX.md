# TASK-013A — Independent Codex Reviewer

你是全新的、独立的 Codex Reviewer。审查本地转写是否真正成为可恢复的 TRANSCRIPT 阶段，而非测试直接推进 SQLite。不得修改业务代码、测试、依赖、锁文件、任务状态、main 或任何其他任务；只可在 source 的 `handoffs/TASK-013A.md` 追加审查证据并创建一个 handoff-only commit。

## 固定对象与授权

- Main authorization：`git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-013A-REVIEWER-CODEX.md` 必须解析为本审查授权提交，且 main 中 TASK-013A=`IN_REVIEW`。
- Reviewed source：`/Users/developer/Documents/yia-worktrees/task-013a` / `codex/task-013a-local-transcription-continuation@213c9ff42f9321d443e4e470d74a18a0296ad528`；开始时必须干净。
- Source handoff `213c9ff...` 的唯一父提交为 implementation `4c3706a969fb85ff4ec344034444d8607894b36f`，其唯一父提交为 `d96862f287d523dd524addf79f86c9b0642a4d31`。
- 相对 `d96862f...`，完整范围只能是 `src/youtube_intel/transcripts.py`、`tests/integration/test_local_transcription_service.py`、`tests/unit/test_transcription_policy.py`、`handoffs/TASK-013A.md`；当前实现只改其中三个路径。
- 模型下载/加载、ffmpeg、媒体/YouTube、网络、Ollama/OpenAI、真实 Vault/用户笔记、凭据、付费服务和测试目录外写入均未授权，不能运行。

## 必读材料

按 `AGENTS.md` 顺序完整阅读协作、状态、PRD、系统设计、复用登记、TASK-013A 卡、ADR-012 与本 prompt。若没有可用的代码图工具，不得运行会写 `.codebase-memory/` 的索引；可用只读 `rg` 定位代码。

## 独立审查与探针

1. **真实服务流**：证明测试实例化产品 `LocalTranscriptionService`，由服务自身使用既有 Repository 事务完成 `METADATA_READY -> TRANSCRIPT_READY`。不得接受通用 handler 或测试手写 `complete_stage` 作为证据。
2. **原子性与缓存**：用真实临时 SQLite/DATA 与 Fake executor 复核：成功创建可验证 canonical Artifact、Provider-call、成功 Job 和 Pipeline；相同输入第二次 executor 为零调用、无重复记录；缓存的 Provider-call、Artifact 身份、内容 hash、路径、Job/Pipeline 或模型/语言/策略不一致必须 fail-closed。
3. **输入与补偿安全**：音频未登记、删除、hash 不符、根外路径、目录/符号链接、陈旧 Job/Pipeline 都必须在 executor 前拒绝且不影响外部文件。注入 `complete_stage` 失败时，新增 canonical 文件不可见、Pipeline 不推进、Provider-call 具既有可重试语义。确认 cleanup 只发生在成功持久化后，且明确为 at-most-once best effort。
4. **边界与可维护性**：不改 `state.py`、Schema/migration、Provider/CLI/Pipeline composition、依赖或锁文件；不偷偷调用模型或网络。复核 `mlx-whisper` Adapter 与标准库为既有 `DIRECT`，真实模型许可证和资源仍交 TASK-014。
5. **验收矩阵**：分别判定 TASK-013A 的五个验收项及 ADR-012 C-01–C-05；记录 P0–P3、未授权路径和 Verdict。

## 必须复跑的离线门禁

```bash
uv lock --check
uv sync --locked --offline
uv run python -m pytest tests/integration/test_local_transcription_service.py
uv run python -m pytest tests/unit/test_transcription_policy.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
uv build --offline
git diff --check d96862f287d523dd524addf79f86c9b0642a4d31...HEAD
```

若发现 P0/P1，按工作包立即停止尚未开始的无关门禁或探针，记录已执行/跳过项；不得自行修复。审查完成后仅在 handoff 记录矩阵、探针、P0–P3、范围/复用/许可证、未授权路径和 `APPROVE` 或 `REJECT`。如提交证据，唯一父提交必须为 `213c9ff42f9321d443e4e470d74a18a0296ad528`，且只修改 `handoffs/TASK-013A.md`。
