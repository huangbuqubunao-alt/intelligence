# TASK-004 correction 5A 第四次独立 Codex Reviewer 包

你是与 TASK-004 原 Grok Implementer、前三次 TASK-004 Reviewer 都独立的**全新 Codex Reviewer 会话**。只审查 correction 5/5A 是否真正关闭 Discovery consumer 与已验收 SQLite Repository 的组合契约问题，并确认此前安全/正确性没有回归。不得修改业务代码、测试、依赖、锁文件、任务状态或 main；全部审查结束后只可写入并提交 `handoffs/TASK-004.md` 的 Reviewer 证据。发现任一 P0/P1/P2 时不得自行修复，必须 `REJECT` 并退回原 Grok Implementer。

## 固定上下文

- Source worktree: `/Users/developer/Documents/yia-worktrees/task-004`
- Source branch: `grok/task-004-discovery-metadata`
- Reviewed source head: `9750df2503a1aee135fdfbcca9f1706bcc9bd8de`
- Correction 5A parent: `d87253e4b6203232ccb933604f0523ef6d868ba8`
- Source sync merge: `eb9246bf5ce650441aaa2d8b8c7f37f22fe6779d`
- Source sync parents: `1883367d313623c42d9d3624b16307ca8d502709` 与 `58c79afc8ab9f74d98c8181a6565be5c9246e4a4`
- Product/control comparison anchor: `main@58c79afc8ab9f74d98c8181a6565be5c9246e4a4`
- Git identity: `Mozhu <maintainer@example.invalid>`；`user.useConfigOnly=true`

只有 Status Integrator 返回本包已 `INTEGRATED` 后才能开始。控制面文档从 main worktree `/Users/developer/Documents/youtubek agent` 读取，并用以下命令取得授权 commit：

```bash
review_authorization="$(git -C '/Users/developer/Documents/youtubek agent' log -1 --format=%H -- agent-prompts/TASK-004-REVIEWER-4-CODEX.md)"
test -n "$review_authorization"
test "$(git -C '/Users/developer/Documents/youtubek agent' rev-parse HEAD)" = "$review_authorization"
test "$(git -C '/Users/developer/Documents/youtubek agent' rev-parse HEAD^)" = "58c79afc8ab9f74d98c8181a6565be5c9246e4a4"
```

任一主线/source 基线、分支、父链、身份或洁净度不符，立即停止并报告 `BLOCKED`。不得 stash、reset、rebase、cherry-pick、merge、清理或选择其他 SHA。原 Implementer 必须已经停止写入；同一 worktree 不得存在第二个写入会话。

## 必读与范围门禁

按 `AGENTS.md` 顺序完整阅读控制面文档，并重点复核：

- `docs/decisions/ADR-003-sqlite-state-store-contract.md` S-05 至 S-08
- `docs/decisions/ADR-004-discovery-ytdlp-contract.md` D-01 至 D-08
- `docs/decisions/ADR-005-reuse-first-delivery-policy.md`
- `tasks/TASK-004-discovery-metadata.md`
- `agent-prompts/TASK-004-CORRECTION-5-GROK.md`
- 本包
- source 的完整 `handoffs/TASK-004.md`
- `src/youtube_intel/state.py`、`discovery.py`、`providers/youtube.py`
- `tests/integration/test_state_store.py`、`tests/unit/test_discovery.py`、`tests/integration/test_discovery_adapter.py`

开始前确认：

1. source HEAD 精确为 `9750df...`，父提交精确为 `d87253e...`；`d87253e...` 父提交为 `eb9246b...`；merge 父链精确包含第三次 review evidence 与 main `58c79af...`。
2. correction 5A `d87253e...9750df...` 只修改以下四个文件：
   - `src/youtube_intel/discovery.py`
   - `tests/unit/test_discovery.py`
   - `tests/integration/test_discovery_adapter.py`
   - `handoffs/TASK-004.md`
3. `58c79af...9750df...` 的完整产品差异精确为 TASK-004 原批准 17 路径；没有 `domain.py`、`state.py`、migration、CLI、任务状态、额外依赖或范围外文件。
4. `git diff --check 58c79afc8ab9f74d98c8181a6565be5c9246e4a4...9750df2503a1aee135fdfbcca9f1706bcc9bd8de` 返回 0。
5. source/main 均干净，`yt-dlp[default,deno]` 仍在批准范围，既有 pydantic/PyYAML 未被升级。

若任一项失败，不写 handoff，返回 `BLOCKED`。

## 必须独立复跑

在 source worktree 运行：

```bash
uv lock --check
uv sync --locked
uv run python -m pytest tests/integration/test_state_store.py
uv run python -m pytest tests/unit/test_discovery.py
uv run python -m pytest tests/integration/test_discovery_adapter.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
uv build
git diff --check 58c79afc8ab9f74d98c8181a6565be5c9246e4a4...9750df2503a1aee135fdfbcca9f1706bcc9bd8de
git status --short
```

Implementer 报告的期望基线为 state integration 30、discovery unit 35、discovery integration 10、全量 131；不要只比数字，必须检查实际收集与断言。`uv build` 必须确认 sdist 与 wheel 均包含 `youtube_intel/migrations/001_initial.sql`。网络若仅因 sandbox 阻断 lock 中已批准依赖或隔离构建，可按既有授权原命令重跑；这不授权访问 YouTube。

## 必做独立离线探针

至少独立设计并执行以下四组探针，不能只引用 Implementer 的测试名：

### A. 单一 Repository 公共契约

- 真实初始化的 `SQLiteStateRepository` 在运行时满足 `DiscoveryRepository`，mypy 静态接受它传给 `DiscoveryService`。
- consumer Protocol 使用 `get_channel_cursor`、`save_discovery_batch`、`upsert_video_metadata`、`mark_video_unavailable` 及精确关键字参数。
- 生产 `discovery.py` 不导入具体 SQLite class，不公开 `Any`、宽 `object`、自由 `dict`/`Mapping`，也没有重复 wrapper 或猴子补丁。

### B. 真实 SQLite 原子性与 Service 级 CAS

- 空库经 `DiscoveryService` 写入全部 candidates 与 cursor，revision、pipeline version 和 UTC 审计正确；稳定重跑不重复、不倒退。
- 必须在 Service 已读 cursor、Provider 返回 batch 前插入另一个真实 SQLite commit，证明 stale Service 抛 `ConcurrencyConflict`；intervening candidate/cursor 保留，stale batch 的所有 candidates 均不存在，无部分写入。
- 探针必须经过 `DiscoveryService.discover_and_save`，不得只直接调用 Repository 来冒充 Service 级 CAS。

### C. metadata/unavailable、Fake parity 与边界零副作用

- 真实 SQLite metadata success 更新记录但不倒退 Pipeline；`CONTENT_UNAVAILABLE` 更新已存在视频为非 PUBLIC，并保持安全 `AppError`。
- Fake 与 SQLite 对未知 video ID 的 `mark_video_unavailable` 都返回 `False` 且不创建 unavailable 记录；正常路径使用已发现视频，不以不存在的 ID 获得假阳性。
- naive datetime、空白 `pipeline_version` 在任何 Provider/Repository 调用前返回 `CONFIG_INVALID`；Source/Metadata call count 与 Repository 状态均保持 0/不变。

### D. correction 3/4 安全回归

独立抽查 malformed yt-dlp payload、请求/响应 ID mismatch、非法 age_limit 保留请求 ID、RSS 缺失/空白/不匹配 channelId 全批失败、HTTP 404/403/429/5xx 分类和正文脱敏、`needs_auth -> RESTRICTED`、全部 response close 路径、公开 Provider surface、`skip_download` 与 `download=False`。证明无 Cookie、登录、remote components、ffmpeg、文件/媒体/字幕下载或真实 YoutubeDL 网络调用。

逐项判定 TASK-004 AC-1 至 AC-5、ADR-004 D-01 至 D-08。真实 YouTube、Cookie/登录、remote components、ffmpeg、媒体/字幕下载必须明确记为 `NOT RUN (not authorized)`。

## 范围、复用与许可证审查

- 核对 correction 5/5A 没有修改 TASK-003 Schema/Repository、domain、依赖和锁文件，且没有通过宽类型掩盖兼容问题。
- 核对直接复用仍为 yt-dlp 2026.7.4、yt-dlp-ejs、Deno 与必要传递依赖；没有来源不明代码复制。
- `mutagen` GPL-2.0-or-later 的发布时分发风险继续留给 TASK-014，不因本轮审查扩大或消失。
- 无 `.venv`、cache、dist、数据库、真实响应、字幕、Cookie、密钥或 Vault 内容进入 Git。

## 交接与提交

完成全部审查后，只允许修改 `handoffs/TASK-004.md` 的 Reviewer 部分并创建一个新 review evidence commit；父提交必须精确为 `9750df2503a1aee135fdfbcca9f1706bcc9bd8de`，提交范围仅该 handoff。不得 amend、merge main、修改任务状态或删除/清理分支和 worktree。

记录：授权 SHA、reviewed head、所有复跑、四组探针、AC/D 矩阵、P0-P3、范围/复用/许可证、跳过项、`APPROVE` 或 `REJECT`、剩余风险和最终洁净度。P0/P1/P2 任一存在即 `REJECT`；P3 可记录并由主控判断。

## 返回主控

```text
Task: TASK-004
Role: Fourth Independent Codex Reviewer
Main review authorization:
Reviewed implementation head: 9750df2503a1aee135fdfbcca9f1706bcc9bd8de
Review evidence commit:
Checks rerun:
Independent probes A-D:
Acceptance matrix: AC-1..AC-5 / D-01..D-08
Findings: P0/P1/P2/P3
Scope/red-line/reuse review:
Verdict: APPROVE | REJECT
Skipped checks:
Remaining risks:
Decision needed: None | details
Post-commit status:
```
