# TASK-013A — Codex Implementer

你是唯一的 Codex Implementer。当前实现以 main 的动态分配提交为唯一实时控制面；source worktree 中的 `READY/UNASSIGNED` 任务卡是固定 base 快照，不构成冲突。先完整阅读 `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、`docs/PRD.md`、`docs/SYSTEM_DESIGN.md`、`docs/REUSE_REGISTER.md`、`tasks/TASK-013A-local-transcription-continuation.md` 与本包。若它们冲突，停止并报告。

## 产品目标与完成标准

当视频没有可用字幕时，本地转写的成功结果必须成为真实、可恢复的 TRANSCRIPT 阶段：后续评分、分析、笔记和周报能消费已验证的转写，而不是测试直接把 SQLite 状态推进到下一阶段。

完成时，使用 Fake Whisper executor 与临时 SQLite/DATA 的测试应证明：

1. 经登记且验证通过的音频，成功转写后在既有 `complete_stage` 事务中创建规范转写 Artifact、Provider-call 完成记录、成功 Job，并推进 `METADATA_READY -> TRANSCRIPT_READY`。
2. 相同的音频 hash、模型/版本、语言提示和参数策略使用已验证缓存；不调用 executor，不产生重复 Artifact 或 Provider-call。
3. Artifact、Provider-call、Job、Pipeline、DATA 根、路径或文件 hash 不一致时失败关闭：不推进 Pipeline，不删除外部文件。
4. 阶段数据库写入失败时，不遗留可见的新转写文件；Provider-call 能沿既有语义恢复。成功后的音频 cleanup 仅提供已接受的 at-most-once best-effort，不声称 exactly-once。
5. 真实服务流测试通过该生产服务，而不是通用测试 handler 或测试中的手写 `complete_stage` 推进。

## 唯一允许修改范围

1. `src/youtube_intel/transcripts.py`
2. `tests/integration/test_local_transcription_service.py`
3. `tests/unit/test_transcription_policy.py`
4. `handoffs/TASK-013A.md`

允许新增上述两份测试文件。不得创建 `.codebase-memory/` 或其他索引工件；当前没有可用的代码图工具时可用只读 `rg` 进行定位。

## 固定架构边界

- 在 `transcripts.py` 增加 Repository-backed 本地转写应用服务；复用既有 `TranscriptRepository`、`TranscriptJobContext`、`ArtifactWrite`、`ProviderCallRequest`、`ProviderCallCompletion`、安全 DATA 写入/校验 helper 和 `complete_stage`。
- 通过现有 `MlxWhisperAdapter` 及结构化最小 Protocol 调用；不要修改 `providers/whisper.py`、`transcription.py`、`state.py`、Pipeline 或 CLI。Adapter 保持仅负责本地执行和内存缓存，持久化由此服务负责。
- 只处理已登记、未删除、hash 匹配、位于 DATA root 内的音频 Artifact。缓存命中也必须重新验证 Provider-call、Artifact identity/内容和文件 hash 后才可完成恢复。
- 使用临时文件、受控路径、hash 校验和失败补偿；任何未知、目录/符号链接、越界或篡改路径都 fail-closed。只清理本次已确认的受管音频，且只在成功持久化后做 best-effort cleanup。

## 明确禁止

- 不新增依赖或修改 `pyproject.toml`、`uv.lock`、Schema/migration、`state.py`、Pipeline 状态转换、Provider/CLI 组合。
- 不下载/加载 Whisper 模型，不运行 ffmpeg、媒体/YouTube、网络、Ollama/OpenAI、真实 Vault/用户笔记、凭据或付费调用。
- 不重做 TASK-013 E2E；不得修改 TASK-013 任何文件或任务状态。
- 不删除、跳过或弱化既有测试。

## 复用

`mlx-whisper` Adapter 与 Python 标准库为 `DIRECT`，但只使用已锁定的离线代码接口；不执行真实模型。记录在 handoff：未复制第三方代码、未新增依赖；真实模型许可证/资源门禁仍留 TASK-014。

## 必须验证

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
git diff --check <base>...HEAD
git status --short
```

完成后只提交允许范围，工作树必须干净。handoff 记录产品效果、复用/许可证、原子/恢复/缓存证据、所有命令结果、跳过的真实资源及 at-most-once 风险。不得自行启动 Reviewer、合并、推送、清理或改任务状态。
