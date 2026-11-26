# TASK-004 Grok Review-Fix Packet 3

你是 TASK-004 原 Grok Implementer。独立 Codex Reviewer 对 source `9db800fc9f4d01a5b6348c5cc8b567f83dc442aa` 给出 `REJECT`，证据 commit 为 `f34cbb09d628ebb256bf5f2895adfd10dbd61812`。你只修复下列 findings 并补足离线回归/交接；不领取 TASK-003、不启动 Reviewer、不合并 main、不改公共任务状态。

## 固定上下文

- Worktree: `/Users/developer/Documents/yia-worktrees/task-004`
- Branch: `grok/task-004-discovery-metadata`
- Product base: `dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176`
- Required source head before correction: `f34cbb09d628ebb256bf5f2895adfd10dbd61812`
- Reviewer: Codex，已结束；修复完成后等待主控预核验
- Parallel work: TASK-003 Grok Reviewer；不得读取、写入、检查、清理或等待 TASK-003

控制面文档必须从 main 读取，即 `/Users/developer/Documents/youtubek agent/AGENTS.md`、该目录下的 `docs/`、`tasks/TASK-004-discovery-metadata.md` 及 `agent-prompts/`；TASK-004 source worktree 只用于代码、测试和本任务 handoff。完整读取 AGENTS、状态/PRD/System Design 第 3/5/5.2/12 节、ADR-002 C-05、ADR-004 D-01 至 D-08、Reuse Register、任务卡、完整 handoff（尤其 Reviewer 结论）、原 Implementer 包、Correction 2 包和本包。若修复需要新依赖、ErrorCode、公共领域类型、范围外文件或真实网络，立即输出 `DECISION NEEDED`。

## 仅允许修改的 5 个文件

- `src/youtube_intel/discovery.py`
- `src/youtube_intel/providers/youtube.py`
- `tests/unit/test_discovery.py`
- `tests/integration/test_discovery_adapter.py`
- `handoffs/TASK-004.md`

不得修改 `pyproject.toml`、`uv.lock`、`domain.py`、`state.py`、fixtures、CLI、任务状态、docs 或其他文件。

## 必须修复

1. **畸形 yt-dlp payload：** `fetch()` 及 `_map_info_dict_to_video_metadata()` 的所有外部字段/日期转换失败必须封装为安全 `AdapterError(AppError)`：`INVALID_RESPONSE`、nonretryable、METADATA、请求 video ID。不得泄漏 `ValueError`、`TypeError`、payload、路径、Cookie 或原始异常文本。
2. **请求/响应身份：** 映射后必须验证 `VideoMetadata.video_id == requested_video_id`；不一致安全失败为 `INVALID_RESPONSE`，请求 ID 保留，不能交给 DiscoveryService/Repository。
3. **RSS 完整性/游标：** 可解析 entry 缺少或无效 `yt:videoId`、`published` 或必要频道/标题字段时，整个 discovery 必须以 `AdapterError(INVALID_RESPONSE, nonretryable)` 失败；不得静默跳过并提交候选/推进 cursor。覆盖“先不完整、后续修复但发布时间更旧”的回归。
4. **HTTP 分类顺序：** 在宽泛文本匹配前固定：404 → `CONTENT_UNAVAILABLE` nonretryable；403 → `PERMISSION_DENIED` nonretryable；503/5xx → `PROVIDER_UNAVAILABLE` retryable；429 仍为 `RATE_LIMITED`。消息固定安全、无 response body。
5. **关联 P2/P3：** RSS response 无论成功、read timeout、OSError、类型错误、大小限制或 XML 失败都关闭；`availability="needs_auth"` 在 V1 无登录态下映射为 `RESTRICTED`，不能为 `PUBLIC`；公开 Surface 回归哨兵必须把 `Any` 和其他未校验宽类型视为失败，且 Provider 构造面仍只有 `timeout_seconds`。

保持现有标准库 RSS、yt-dlp Python API、离线 Fake、窄 Repository Protocol，及 `skip_download=True`、`noplaylist=True`、`ignoreconfig=True`、`extract_info(..., download=False)`。不得使用 Cookie、账号、remote components、ffmpeg、subprocess，或下载媒体/字幕/缩略图/info JSON。不得删除/弱化现有测试。

## 开始、验证与提交

开始前确认 worktree 干净、HEAD 为 `f34cbb...`、身份 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`。修复后运行：

```bash
uv lock --check
uv sync --locked
uv run python -m pytest tests/unit/test_discovery.py
uv run python -m pytest tests/integration/test_discovery_adapter.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
git diff --check
git status --short
```

独立验证所有 P1/P2/P3 回归。真实 YouTube、Cookie/登录、remote components、ffmpeg、媒体/字幕下载仍不得运行。核对 `dcc7d85...HEAD` 仍只在原批准的 17 文件集合，本 correction commit 仅在以上 5 文件。不得 amend 旧实现/审查提交；创建新 commit，建议：

```text
fix: harden discovery adapter error boundaries
```

在 handoff 新增“Reviewer REJECT 修复”段，逐条记录 finding、回归、命令、最终 SHA、跳过项和风险。TASK-004 保持 `IN_PROGRESS`。

返回：Task、Role、Branch/worktree、Base、Prior head、Code evidence/Branch head、changed files、finding matrix、checks、diff、skipped checks、risks、Decision needed。
