# TASK-005：字幕获取与规范化

- Status: `BLOCKED`
- Assignee: `UNASSIGNED`
- Owner role: 实现 Agent
- Size: M
- Risk: High
- Depends on: TASK-003, TASK-004
- Decision gate: `ADR-006` 为 `Proposed`；T-01 至 T-15 尚待产品负责人批准

## 目标

为单个视频按语言偏好获取人工或自动字幕，保存原始产物并生成可供下游使用的规范文本；无有效字幕时明确返回本地转写需求。

## 范围

- 实现人工字幕 > 自动字幕的选择策略和语言偏好排序。
- 保存原始字幕，规范化为文本并执行空文本、乱码、重复率和最低长度质量检查。
- 以视频、字幕来源、语言和内容哈希建立幂等缓存。
- 在 `domain.py` 使用具名字幕格式、质量、转写原因和判别联合，不使用自由 `dict`。
- 使用现有 `SUBTITLE_SOURCE` / `TRANSCRIPT_CANONICAL`、Provider-call 缓存和 `complete_stage`；V1 不修改 Schema 或 Repository 语义。

## 范围外

- 不实现 Whisper 转写。
- 不做视频评分或总结。
- 不删除用户文件，不把字幕全文写入日志或 SQLite。
- 不修改 `state.py`、migration、`pyproject.toml` 或 `uv.lock`。
- 不访问真实 YouTube/字幕，不使用 Cookie、登录、`.netrc`、remote components、ffmpeg 或媒体下载，除非后续获得精确授权。

## 验收标准

- [ ] 固定夹具覆盖人工字幕优先、自动字幕回退、多语言选择、空字幕和损坏字幕。
- [ ] 同一输入重复处理不重复下载/规范化；原始字幕与规范文本均有哈希和来源元数据。
- [ ] 无有效字幕返回明确 `transcription_required` 结果，网络错误和“确实无字幕”可区分。
- [ ] 缓存命中时验证既有 Artifact 与文件哈希，以空 Artifact stage completion 完成当前 Job；不重新下载、不修改 TASK-003 Repository。
- [ ] 原始字幕与规范文本使用安全 DATA-relative 路径和原子写入；崩溃恢复不相信未验证文件，日志/错误/SQLite 不含临时 URL、正文或绝对路径。

## 验证

- [ ] `uv lock --check`
- [ ] `uv run python -m pytest tests/unit/test_contracts.py`
- [ ] `uv run python -m pytest tests/unit/test_subtitle_policy.py`
- [ ] `uv run python -m pytest tests/integration/test_subtitle_provider.py`
- [ ] `uv run python -m pytest`
- [ ] `uv run mypy src`
- [ ] `uv run ruff check .`
- [ ] `uv run python -m youtube_intel --help`
- [ ] `uv build`
- [ ] `git diff --check <base>...HEAD`
- [ ] 人工检查：日志只包含视频 ID、语言、来源、路径/哈希和计数，不含字幕全文。

## 预计触达文件

- `src/youtube_intel/domain.py`
- `src/youtube_intel/transcripts.py`
- `src/youtube_intel/providers/subtitles.py`
- `tests/unit/test_contracts.py`
- `tests/unit/test_subtitle_policy.py`
- `tests/integration/test_subtitle_provider.py`
- `tests/fixtures/subtitles/` 下最小夹具
- `handoffs/TASK-005.md`

除非新的 ADR 先获批准，预计范围不包含 `state.py`、`migrations/**`、`pyproject.toml` 或 `uv.lock`。

## 交付证据

- 测试矩阵和结果。
- 一个脱敏的 TranscriptArtifact 示例。
- 字幕质量规则的已知误判风险。
- 原始/规范幂等键、原子写入、缓存恢复和空 Artifact stage completion 的离线证据。
- `yt-dlp`/标准库的实际复用与许可证证据；未新增依赖的锁文件核对。

## 并行只读预检

- TASK-005 继续为 `BLOCKED`，不得实现、安装依赖、修改锁文件、下载字幕或访问真实 YouTube。
- TASK-004 correction 5 写入期间，可由独立只读 Scout 针对已提交 Git 对象、main 文档和已冻结领域/状态契约并行盘点字幕选择、规范化、产物、错误、复用和审批空白；不得读取正在变化的 TASK-004 live worktree。
- Preflight packet: `agent-prompts/PREFLIGHT-TASK-005-READONLY.md`。
- Scout 输出仅作为主控补齐 TASK-005 契约和后续审批包的依据，不改变依赖满足状态，不构成 `READY` 或实现授权。

## 只读预检结论与待批准决策

- Scout observed main: `58c79afc8ab9f74d98c8181a6565be5c9246e4a4`；全程只读，主线无变化。
- 预检确认既有领域对象不足以无歧义表达“字幕就绪”与“需要本地转写”，语言/格式/质量/缓存细则也尚未冻结。
- 主控已将建议收敛为 `docs/decisions/ADR-006-subtitle-acquisition-contract.md` 的 T-01 至 T-15；状态为 `Proposed`，等待产品负责人批准。
- 主控不采纳预检中“直接新增 transcript manifest migration”和“修改 complete_stage 支持 job-neutral Artifact”的原建议。推荐方案使用现有两个 Artifact kind、稳定 key/path、Provider-call 记录、文件哈希验证和空 Artifact stage completion；若实现证据证明不足，再单独升级 Schema/Repository ADR。
- TASK-005 继续为 `BLOCKED`：即使 T-01 至 T-15 获批，也必须等待 TASK-004 独立审查、整合并关闭为 `DONE`，再生成正式 worktree、Implementer、Reviewer 与任务级命令/网络授权。
