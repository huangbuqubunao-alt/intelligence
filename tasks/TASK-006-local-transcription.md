# TASK-006：本地 Whisper 转写

- Status: `BLOCKED`
- Assignee: `UNASSIGNED`
- Owner role: 实现 Agent；TL 审批实现选择
- Size: M
- Risk: High
- Depends on: TASK-005
- Approval required: Whisper 实现/模型依赖、最大时长、缓存清理策略

## 目标

在无有效字幕时下载受控音频并在 Apple Silicon 本地完成转写，产出与字幕路径相同的 TranscriptArtifact 契约。

## 范围

- 按 `DEC-03` 实现 Whisper Adapter，并按 `DEC-05` 执行时长上限/强制策略。
- 音频下载、转写参数、超时、资源错误和清理均可观察。
- 缓存键包含音频哈希、实现/模型和参数版本，模型升级不会误用旧结果。

## 范围外

- 不使用未批准的云端转写服务。
- 不对已有有效字幕的视频下载音频。
- 不静默下载超出长度或资源策略的视频。

## 验收标准

- [ ] 短音频夹具可在支持环境完成转写；不支持/资源不足时返回明确错误而非崩溃或无限等待。
- [ ] 相同音频和模型参数重复运行命中缓存；模型/参数变化时生成新的可追踪产物。
- [ ] 成功、失败和超长三条路径遵循已审批的音频保留策略，清理失败不丢失已完成转写。

## 验证

- [ ] `python -m pytest tests/unit/test_transcription_policy.py`
- [ ] `python -m pytest tests/integration/test_whisper_provider.py`
- [ ] `mypy src && ruff check .`
- [ ] 受控本机冒烟：记录短音频时长、模型、耗时、峰值资源的可用指标和退出码。

## 预计触达文件

- `src/youtube_intel/transcription.py`
- `src/youtube_intel/providers/whisper.py`
- `tests/unit/test_transcription_policy.py`
- `tests/integration/test_whisper_provider.py`
- `tests/fixtures/audio/` 下一个短且可再分发的夹具

## 交付证据

- 依赖和实现选择审批记录。
- 自动测试与本机冒烟结果。
- 性能/资源基线和未解决风险。
