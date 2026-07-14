# TASK-005：字幕获取与规范化

- Status: `BLOCKED`
- Assignee: `UNASSIGNED`
- Owner role: 实现 Agent
- Size: M
- Risk: High
- Depends on: TASK-003, TASK-004

## 目标

为单个视频按语言偏好获取人工或自动字幕，保存原始产物并生成可供下游使用的规范文本；无有效字幕时明确返回本地转写需求。

## 范围

- 实现人工字幕 > 自动字幕的选择策略和语言偏好排序。
- 保存原始字幕，规范化为文本并执行空文本、乱码、重复率和最低长度质量检查。
- 以视频、字幕来源、语言和内容哈希建立幂等缓存。

## 范围外

- 不实现 Whisper 转写。
- 不做视频评分或总结。
- 不删除用户文件，不把字幕全文写入日志或 SQLite。

## 验收标准

- [ ] 固定夹具覆盖人工字幕优先、自动字幕回退、多语言选择、空字幕和损坏字幕。
- [ ] 同一输入重复处理不重复下载/规范化；原始字幕与规范文本均有哈希和来源元数据。
- [ ] 无有效字幕返回明确 `transcription_required` 结果，网络错误和“确实无字幕”可区分。

## 验证

- [ ] `python -m pytest tests/unit/test_subtitle_policy.py`
- [ ] `python -m pytest tests/integration/test_subtitle_provider.py`
- [ ] `mypy src && ruff check .`
- [ ] 人工检查：日志只包含视频 ID、语言、来源、路径/哈希和计数，不含字幕全文。

## 预计触达文件

- `src/youtube_intel/transcripts.py`
- `src/youtube_intel/providers/subtitles.py`
- `tests/unit/test_subtitle_policy.py`
- `tests/integration/test_subtitle_provider.py`
- `tests/fixtures/subtitles/` 下最小夹具

## 交付证据

- 测试矩阵和结果。
- 一个脱敏的 TranscriptArtifact 示例。
- 字幕质量规则的已知误判风险。
