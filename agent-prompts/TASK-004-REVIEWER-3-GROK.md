# TASK-004 Third Independent Grok Reviewer Packet

你是与 TASK-004 原 Grok Implementer、两位此前 Codex Reviewer 都独立的**全新 Grok Reviewer 会话**。你的职责是审查 correction 4 是否真正关闭第二次独立审查留下的两个 P1，同时复核既有 correction 3 的关键安全边界。不得修改业务代码、测试、依赖、锁文件、任务状态或 main；只有在全部审查结束后，才可写入并提交 `handoffs/TASK-004.md` 的 Reviewer 部分。发现任一 P0/P1/P2 时不得自行修复，输出 `REJECT` 并退回原 Grok Implementer。

## 固定上下文

- Worktree: `/Users/hua/Documents/yia-worktrees/task-004`
- Branch: `grok/task-004-discovery-metadata`
- Product base: `dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176`
- Reviewed source head: `54c0ab201388cba35e481d7a511f21575946ad14`
- Previous review evidence: `5d66c28d6bd02a7cf31a27ffe9a31a2479f9da58`
- Main review authorization: 主控将在 Status Integrator 成功提交后随启动指令提供；不要在自己的提交中自引用它
- Implementer 已停止写入；开始审查时 source worktree 必须干净
- TASK-003 已 `DONE`；不得读取、写入、检查、清理或等待 TASK-003 worktree

控制面文档必须从 main `/Users/hua/Documents/youtubek agent` 读取；TASK-004 source worktree 只用于代码、测试和本任务 handoff。完整读取 `AGENTS.md`、协作/状态/PRD/System Design 第 3、5、5.2、12 节、ADR-002 C-05、ADR-004 D-01 至 D-08、Reuse Register、TASK-004 卡、完整 handoff（特别是 `5d66c28...` 的 REJECT 与 correction 4 记录）、前三个 Reviewer 包、四个 correction 包和本包。

## 开始前门禁与范围

确认分支 `grok/task-004-discovery-metadata`、HEAD 精确 `54c0ab2...`、worktree 干净、身份为 `Mozhu <huangbuqubunao@gmail.com>`、`user.useConfigOnly=true`；确认 `54c0ab2...` 父提交为 `5d66c28...`，correction 4 精确仅改五个文件：`providers/youtube.py`、`discovery.py`、两份 discovery 测试与 handoff。完整 Diff `dcc7d85...54c0ab2...` 仍只能属于原批准 17 文件集合；否则停止，不写 handoff。

复核 `yt-dlp[default,deno]` 仍在已批准范围、无额外直接依赖或既有直接依赖升级；没有真实 YouTube、Cookie/登录、remote components、ffmpeg、媒体/字幕下载、Vault、密钥、真实响应或缓存；不得改变 `domain.py`、`state.py`、CLI 或 TASK-003 接口。

## 独立复跑

必须重新运行：

```bash
uv lock --check
uv sync --locked
uv run python -m pytest tests/unit/test_discovery.py
uv run python -m pytest tests/integration/test_discovery_adapter.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
git diff --check dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176...54c0ab201388cba35e481d7a511f21575946ad14
```

## 必做独立、离线、非写入探针

至少设计并执行三项；记录命令、预期与实际：

1. **age_limit 身份完整性：** 以缺失、字符串、嵌套对象或其他非法 age_limit 走直接 mapping 与 `Provider.fetch()`/Service 路径。每一错误都必须是安全 `INVALID_RESPONSE`、nonretryable、METADATA，`video_id` 精确为请求 ID；不得逸出 `ValueError`/`TypeError` 或泄漏 raw payload，Repository 不得写入。
2. **RSS channel 完整性与事务边界：** entry 缺失、空白或不匹配 channelId 必须使全批安全失败，candidate、cursor、既有 Repository 状态均不变；补齐相同较旧 entry 后必须仍可发现。确认不以 expected/request channel 回填 entry 值。
3. **既有安全回归：** 独立覆盖请求/响应 ID mismatch、HTTP 404/403/429/503 分类与正文脱敏、`needs_auth -> RESTRICTED`、response close、公开 Provider surface 和 yt-dlp `skip_download`/`download=False`，确保 correction 4 未倒退。

逐项判定 AC-1 至 AC-5、ADR-004 D-01 至 D-08。真实 YouTube、Cookie/登录、remote components、ffmpeg、媒体/字幕下载不得运行，必须明确记为跳过项。

## 交接与提交

完成后只允许修改并提交 `handoffs/TASK-004.md`。review evidence commit 必须以 `54c0ab2...` 为父提交，范围仅一份 handoff；不得 amend 实现/修复/旧审查提交。记录 base/source、复跑、探针、AC/D 矩阵、P0-P3、范围/复用/许可证、`APPROVE` 或 `REJECT`、跳过项与风险。回传 review evidence SHA、最终 HEAD 与干净 worktree。
