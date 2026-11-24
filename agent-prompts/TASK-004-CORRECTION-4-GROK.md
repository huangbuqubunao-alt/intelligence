# TASK-004 Grok Review-Fix Packet 4

你是 TASK-004 原 Grok Implementer。第二位独立 Codex Reviewer 对 source `30932e1742e948683f9e1c0f63236451b8d731bd` 给出 `REJECT`，证据 commit 为 `5d66c28d6bd02a7cf31a27ffe9a31a2479f9da58`。你只修复下列两个 P1、补充离线回归和交接；不领取 TASK-003、不启动 Reviewer、不合并 main、不改公共任务状态。

## 固定上下文

- Worktree: `/Users/developer/Documents/yia-worktrees/task-004`
- Branch: `grok/task-004-discovery-metadata`
- Product base: `dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176`
- Required source head before correction: `5d66c28d6bd02a7cf31a27ffe9a31a2479f9da58`
- Reviewer: 第二个 Codex Reviewer 已结束；修复完成后等待主控范围核验
- Parallel work: TASK-003 Codex Integrator；不得读取、写入、检查、清理或等待 TASK-003 worktree

控制面文档必须从 main `/Users/developer/Documents/youtubek agent` 读取；TASK-004 source worktree 只用于代码、测试和本任务 handoff。完整读取 `AGENTS.md`、协作/状态/PRD/System Design 第 3、5、5.2、12 节、ADR-002 C-05、ADR-004 D-01 至 D-08、Reuse Register、TASK-004 卡、完整 handoff（特别是 `5d66c28...` Reviewer 结论）、全部前三轮 correction 包和本包。若修复需要新依赖、ErrorCode、公共领域类型、范围外文件或真实网络，立即输出 `DECISION NEEDED`。

## 仅允许修改的 5 个文件

- `src/youtube_intel/providers/youtube.py`
- `src/youtube_intel/discovery.py`
- `tests/unit/test_discovery.py`
- `tests/integration/test_discovery_adapter.py`
- `handoffs/TASK-004.md`

不得修改 `pyproject.toml`、`uv.lock`、`domain.py`、`state.py`、fixtures、CLI、任务状态、docs 或其他文件。

## 必须修复

1. **非法 age_limit 保留请求身份：** 所有由外部 yt-dlp `age_limit` 缺失、类型非法或值非法引起的安全 `AdapterError(AppError)` 必须保留请求 `video_id`。无论通过 `_coerce_age_limit()` 或上层包装实现，最终错误必须为 `INVALID_RESPONSE`、nonretryable、`METADATA` 阶段、`error.video_id == requested_video_id`。不得把原始 age_limit、payload、路径、Cookie 或底层 `ValueError`/`TypeError` 写进错误。补充至少一个直接针对非法 age_limit 的离线回归。
2. **RSS entry channelId 不得回填：** 每个可解析 RSS entry 的 channelId 必须存在、非空且有效；不得用请求 channel ID 回填 entry 缺失值。缺失或无效时整批 discovery 必须安全 `INVALID_RESPONSE`、不可重试，且不保存 candidates、不推进 cursor；随后修复同一较旧 entry 后仍可被发现。补充离线 unit/integration 回归，明确验证 Repository 与 cursor 均未变。
3. **不得回归 correction 3：** 保持 malformed date/duration、请求/响应 ID mismatch、RSS 缺 videoId/published/title、response finally-close、HTTP 404/403/429/503/5xx 分类与正文脱敏、`needs_auth -> RESTRICTED`、公开 surface 以及无下载/无 Cookie/无 remote components/无 ffmpeg 边界。不得新增依赖或公开自由 dict 接口。

开始前确认 worktree 干净、HEAD 为 `5d66c28...`、身份 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`。修复后运行：

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

真实 YouTube、Cookie/登录、remote components、ffmpeg、媒体/字幕下载仍不得运行。核对 `dcc7d85...HEAD` 仍只在原批准 17 文件集合，本 correction commit 仅为上述 5 文件；不得 amend。建议提交：

```text
fix: preserve discovery error identity and RSS integrity
```

在 handoff 增加“Second Reviewer REJECT 修复”段，逐项记录两个 P1、离线回归、命令、最终 SHA、跳过项和剩余风险。TASK-004 保持 `IN_PROGRESS`。

返回 Task、Role、Branch/worktree、Base、Prior head、Code evidence/Branch head、changed files、finding matrix、checks、diff、skipped checks、risks、Decision needed。
