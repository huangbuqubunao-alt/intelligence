# TASK-005：字幕获取与规范化

- Status: `IN_REVIEW`
- Assignee: `Codex`
- Reviewer: `Codex`（全新独立会话；不得复用 Implementer 对话，已授权但尚未启动）
- Owner role: 实现 Agent
- Size: M
- Risk: High
- Depends on: TASK-003, TASK-004
- Decision gate: `ADR-006` 为 `Accepted`；产品负责人已于 2026-07-15 批准 T-01 至 T-15
- Execution gate: TASK-003/004 已在 main `DONE`；产品负责人已授权固定 worktree、角色、范围、既有锁定依赖的离线 `uv` 命令和构建。ADR-006 设计批准不授权真实产品网络

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

- TASK-005 只读预检已完成；全程未修改仓库、安装依赖、下载字幕或访问真实 YouTube。
- Preflight packet: `agent-prompts/PREFLIGHT-TASK-005-READONLY.md`。
- Scout 输出已经主控收敛为 ADR-006；预检本身不改变依赖满足状态，不构成 `READY` 或实现授权。

## 只读预检结论与待批准决策

- Scout observed main: `58c79afc8ab9f74d98c8181a6565be5c9246e4a4`；全程只读，主线无变化。
- 预检确认既有领域对象不足以无歧义表达“字幕就绪”与“需要本地转写”，语言/格式/质量/缓存细则也尚未冻结。
- 主控已将建议收敛为 `docs/decisions/ADR-006-subtitle-acquisition-contract.md` 的 T-01 至 T-15；产品负责人已全部批准，ADR 状态为 `Accepted`。
- 主控不采纳预检中“直接新增 transcript manifest migration”和“修改 complete_stage 支持 job-neutral Artifact”的原建议。推荐方案使用现有两个 Artifact kind、稳定 key/path、Provider-call 记录、文件哈希验证和空 Artifact stage completion；若实现证据证明不足，再单独升级 Schema/Repository ADR。
- 2026-07-16 正式分配：base 为 `main@b28f52d0e4950f78dba315d4afe211ea5f75b93c`；worktree 为 `/Users/hua/Documents/yia-worktrees/task-005`；branch 为 `codex/task-005-subtitle-pipeline`；Codex 为唯一 Implementer，完成后由全新独立 Codex Reviewer 审查，Reviewer 不得复用 Implementer 对话。
- 实施只允许任务卡列出的 8 个路径：`domain.py`、`transcripts.py`、`providers/subtitles.py`、三份既定测试、`tests/fixtures/subtitles/**` 与 `handoffs/TASK-005.md`。不新增/升级依赖，不改 `state.py`、migration、`complete_stage`、`pyproject.toml` 或 `uv.lock`。允许 `uv sync --locked` 仅为已有锁定依赖的缓存缺失下载，以及全部离线 `uv` 验证/构建命令。
- 真实 YouTube/字幕、Cookie、登录、remote components、ffmpeg、媒体下载、真实 Vault/密钥仍未授权；Implementer 不得启动或访问这些路径。

## 实现证据与审查授权

- Implementation commit：
  `98d19700818bcae14efc412aaaaeb6eed97a1535`
- Parent/base：
  `b28f52d0e4950f78dba315d4afe211ea5f75b93c`
- Source branch/worktree：
  `codex/task-005-subtitle-pipeline` /
  `/Users/hua/Documents/yia-worktrees/task-005`
- 完整 Diff 精确为 11 个文件，全部属于批准的 8 个路径组；source worktree 干净，
  `git diff --check` 通过，身份为 `Mozhu <huangbuqubunao@gmail.com>`。
- Implementer 自报 contracts 50、policy 24、integration 31、全量 191、mypy、
  SQLite wiring、Ruff、CLI、lock/sync、offline build 全 PASS；该记录不是独立
  Reviewer 结论。
- 变更共 4,384 行，其中 `transcripts.py` 1,664 行、integration test 1,020 行。
  Reviewer 必须独立审查职责边界、复杂度、测试质量、安全与性能；不得只按行数拒绝，
  也不得只因测试通过而批准。
- Reviewer packet：`agent-prompts/TASK-005-REVIEWER-CODEX.md`。
- Reviewer 只可在 source handoff 记录结论并创建单文件 evidence commit；不得修改
  业务代码、测试或 main。
