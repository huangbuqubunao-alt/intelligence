# TASK-013A — Codex Implementer, Correction 1

你是原 Codex Implementer。先完整阅读 `AGENTS.md`、协作/状态/PRD/System Design/Reuse Register、TASK-013A 卡、ADR-012、本包和 source handoff。main 的动态 Correction 1 授权是唯一实时控制面；若文件冲突或权限不一致，停止并报告。

## 要修复的产品风险

用户重新运行任务时，系统必须只复用真正由同一视频、同一转写流程生成的可信缓存。当前缺陷允许被篡改的缓存产物关联到另一条仍在运行的任务，从而把错误任务标为成功。这会让用户看到不属于该任务的“已完成”结果，必须 fail-closed。

## 唯一允许修改范围

1. `src/youtube_intel/transcripts.py`
2. `tests/integration/test_local_transcription_service.py`
3. `handoffs/TASK-013A.md`

不得修改 `state.py`、Schema/migration、`providers/whisper.py`、`transcription.py`、Pipeline/CLI composition、依赖/锁文件、TASK-013 或任务状态；不得创建 `.codebase-memory/` 索引工件。

## 修复完成标准

1. 在任意 persisted-cache 命中、当前 Job 推进或 executor 调用之前，验证 canonical Artifact 的 `job_id` 指向真实的历史 Job；该 Job 必须属于同一 video、目标为 `TRANSCRIPT`、状态为 `SUCCEEDED`、有完成时间且 pipeline version 与当前 context 一致。
2. 缺失/空白/篡改 Artifact `job_id`、不存在/运行中/失败/错误 stage/错误 video/错误 pipeline version 的历史 Job 均返回安全错误，Fake executor 为零调用，当前 Job/Pipeline 不推进，且不清理任何音频或外部文件。
3. 正常的已验证缓存仍可恢复：executor 零调用、无重复 Artifact/Provider-call，并允许当前已领取的重排 Job 通过既有事务完成其 `METADATA_READY -> TRANSCRIPT_READY` 状态。
4. 保留现有成功、数据库失败补偿、受控 cleanup 和 at-most-once 边界；不要因修复删除或弱化任何测试。

## 固定边界

- 这是 `LocalTranscriptionService` 内的缓存来源校验，不是新的 Provider、状态机或 Schema 设计。
- 继续只使用临时 SQLite/DATA、Fake Whisper executor 和锁定离线依赖。
- 不下载或加载模型；不运行 ffmpeg、媒体/YouTube、网络、Ollama/OpenAI、真实 Vault、凭据或付费调用。

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
git diff --check d96862f287d523dd524addf79f86c9b0642a4d31...HEAD
git status --short
```

在 handoff 记录 Reviewer RED 用例、每种 provenance 反例的 GREEN 结果、正常重排缓存不回归、完整命令与风险。提交必须以 `08542b84d550ca225dece520cf748a2fc654ab58` 为唯一父提交，且只包含允许范围。不得自行启动 Reviewer、合并、推送、清理或修改状态。
