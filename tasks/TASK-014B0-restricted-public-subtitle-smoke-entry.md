# TASK-014B0：受限公开字幕 smoke 组合入口

- Status: `IN_PROGRESS`
- Assignee: `Original Codex Implementer — Correction 1 (authorized; not started)`
- Owner role: PO + TL + QA
- Size: M
- Risk: High
- Depends on: TASK-013; ADR-013 Accepted

## 目标

实现 ADR-013 的生产拥有、受限 CLI 组合入口，供后续 TASK-014 Phase B-1 进行一次公开发布 QA。入口只能读取
最多三个预列公开视频的元数据、字幕目录与一条选中字幕正文，并在全新临时根中产生脱敏审计；它不是通用下载或处理能力。

## 固定分配

- 控制面基线：`main@28223cc98f9da18fc877289231a92e240cc711d0`。
- 实施 worktree：`/Users/hua/Documents/yia-worktrees/task-014-phase-b0-restricted-public-subtitle-smoke`。
- 分支：`codex/task-014-phase-b0-restricted-public-subtitle-smoke`。
- 正式包：`agent-prompts/TASK-014B0-RESTRICTED-PUBLIC-SUBTITLE-SMOKE-IMPLEMENTER-CODEX.md`。
- Reviewer：全新独立 Codex Reviewer（本包不启动）。
- Reuse decision：`DIRECT` — 已锁定的 yt-dlp Metadata/Subtitle Adapter、SQLite migration、JSONL logger 和 Python 标准库；
  不新增或复制第三方代码。

## 独立审查授权

- 主线控制面基线：`main@c62310ab79f01f5f311c9f54bb28365905f5a81a`。
- 唯一 source：`/Users/hua/Documents/yia-worktrees/task-014-phase-b0-restricted-public-subtitle-smoke`，分支
  `codex/task-014-phase-b0-restricted-public-subtitle-smoke`，待审 HEAD
  `4e506847854f20a43011b0a15db3a1c8e320656d`，唯一父提交
  `c62310ab79f01f5f311c9f54bb28365905f5a81a`。
- 正式 Reviewer 包：`agent-prompts/TASK-014B0-RESTRICTED-PUBLIC-SUBTITLE-SMOKE-REVIEWER-CODEX.md`。
- Reviewer 只能向 source 的既有 `handoffs/TASK-014B0.md` 追加审查证据；不得改变 source 的其他路径、main
  控制面、依赖或 Schema。此授权本身不启动 Reviewer。

## Correction 1（第一轮审查 `REJECT`）

- 主线控制面基线：`main@40df8093fe67a8a0fe3bfe4175acbb42ede2286e`。
- 唯一 source 的最新 Reviewer evidence：`f8e336a8c3b09a8c0c0e5857148495f2cb2281aa`，其唯一父提交为
  `4e506847854f20a43011b0a15db3a1c8e320656d`，且仅追加 `handoffs/TASK-014B0.md`。Correction 1 必须从该 evidence
  开始，实施提交必须是其唯一非 merge 后继。
- 第一轮 Reviewer Verdict：`REJECT`。P1：顶层 `--project-root`、`--settings`、`--channels` 仍可被
  `smoke-public-subtitles` 接受，违背该入口只接受临时根与显式视频 ID 的契约。P2：Implementer handoff 的基线、
  提交 SHA 与状态仍是过期占位信息。
- 正式 Correction 1 包：`agent-prompts/TASK-014B0-CORRECTION-1-IMPLEMENTER-CODEX.md`。本包只登记授权，不启动
  Implementer。

### Correction 1 唯一允许修改范围

1. `src/youtube_intel/cli.py`
2. `tests/integration/test_public_subtitle_smoke.py`
3. `handoffs/TASK-014B0.md`

禁止修改原 B0 其余三条路径、任何 Adapter、`state.py`、domain/config、Schema/migration、依赖、锁文件、任务状态、
控制面、项目 LICENSE 或 B-1 source evidence。范围不足时停止并报告 `DECISION NEEDED`。

### Correction 1 验收

- [ ] `smoke-public-subtitles` 无论三项全局选项在命令行中的位置或 `--name=value` 形式，均拒绝
  `--project-root`、`--settings`、`--channels`，且在 runner/Adapter/临时根初始化前以既有参数错误退出；其他命令原有
  解析与默认 fail-closed 语义不变。
- [ ] 仅保留新临时根与 1–3 个显式公开视频 ID 的输入表面，以及单次调用、无重试、正文不落盘、脱敏审计、零业务记录
  与所有禁止资源边界。
- [ ] handoff 明确记录实际初始基线 `c62310…`、实现 `4e506…`、第一轮 evidence `f8e336…`、Correction 1 提交和
  当前状态；不得保留 `pending` 或把离线 Fake 写成真实 B-1 smoke。

## 验收标准

- [ ] 新命令仅接受一个新建绝对临时根和 1–3 个不同的显式视频 ID；无 channel/URL/playlist/discovery、无环境或配置读取。
- [ ] 每个 ID 最多一次 metadata、字幕目录和选中正文读取，固定 30 秒 timeout、无自动重试、无并发；不下载媒体，
  不调用 ffmpeg/模型/Ollama/OpenAI/真实 Vault。
- [ ] 临时根中仅有初始化 SQLite、DATA、空测试 Vault 和脱敏 JSONL；不创建 Pipeline/Job/ProviderCall/Artifact 业务记录，
  不持久化字幕正文、临时 URL、密钥或绝对路径。
- [ ] 现有 `check/process/retry/weekly/doctor` 参数和默认 fail-closed 语义不变；退出码保持 ADR-011 定义。
- [ ] 离线 Fake 测试覆盖输入上限、一次调用、失败不重试、根隔离、正文不落盘/不入日志、默认命令无回归和安全选项。

## 唯一允许修改范围

1. `src/youtube_intel/cli.py`
2. `src/youtube_intel/public_subtitle_smoke.py`（可新建）
3. `tests/integration/test_operations.py`
4. `tests/integration/test_public_subtitle_smoke.py`（可新建）
5. `docs/operations.md`
6. `handoffs/TASK-014B0.md`（可新建）

不得修改任何其他路径，包括 Provider Adapter、`state.py`、domain/config、Schema/migration、依赖、锁文件、
任务状态、控制面、项目自身 LICENSE 或 B-1 source 证据。范围不足时停止并报告 `DECISION NEEDED`。

## 绝对禁止

- 不联网、不运行真实 smoke、不查询公开视频、不使用 Cookie/登录/API key/凭据/真实 Vault/用户数据。
- 不运行 ffmpeg、媒体下载、Whisper、Ollama、OpenAI、付费调用、launchd 或任何模型。
- 不新增依赖、不改 Schema/迁移、默认 CLI 行为、Pipeline/Job/Repository 语义或发布结论。
- 不合并、push、rebase、reset、清理或启动 Reviewer。

## 验证（仅在后续 Implementer 正式启动后）

- `uv run python -m pytest tests/integration/test_operations.py tests/integration/test_public_subtitle_smoke.py`
- `uv run mypy src && uv run ruff check .`
- `uv run python -m youtube_intel --help` 和离线 Fake 入口探针；不得调用网络。
- `git diff --check && git status --short`。
