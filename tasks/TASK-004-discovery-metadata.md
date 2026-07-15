# TASK-004：频道发现与元数据

- Status: `IN_PROGRESS`
- Assignee: `Grok`
- Reviewer: `Codex`（第二次独立审查 `REJECT`，已结束）
- Owner role: 实现 Agent
- Size: M
- Risk: High
- Depends on: TASK-002
- Approval: `APPROVED` — 产品负责人已于 2026-07-14 批准 `ADR-004` D-01 至 D-08、`yt-dlp[default,deno]>=2026.7.4,<2026.8`、必要传递依赖、网络下载、`pyproject.toml`/`uv.lock` 和所列 uv 命令

## 目标

交付第一条垂直切片：从配置频道发现候选视频，获取标准化元数据，并通过接口交给状态仓库；实现必须支持固定离线夹具和可替换 Source Provider。

## 范围

- 按 `DEC-01` 实现频道发现和元数据 Adapter。
- 标准化公开视频、Shorts、已结束直播、直播中/预约和不可用内容的状态。
- “完整保存发现批次”只要求全部候选与 `next_cursor` 在同一事务落库；元数据按视频独立获取和重试。
- TASK-004 只输出有序去重的 `available_languages` 摘要；字幕轨道明细由 TASK-005 重新查询。
- RSS 使用标准库；yt-dlp 只获取元数据/清单，不下载媒体、不读取 Cookie 或登录态。

## 范围外

- 不下载字幕或音频。
- 不评分、不写 Obsidian。
- 不自动读取用户 YouTube 订阅或要求账号登录。
- 不修改 `domain.py` 或 `state.py`，不引入 `httpx`、ffmpeg 或运行时 remote components。

## 验收标准

- [ ] 固定夹具能发现新视频、忽略已见视频，并正确分类直播中、已结束和不可用内容。
- [ ] 重复运行同一发现批次得到相同视频集合，不产生重复持久化记录或错误推进游标。
- [ ] 网络超时、解析失败和内容不可用映射为不同领域错误，且响应正文不会原样写日志。
- [ ] 元数据失败不回滚已原子保存的候选/游标；人工与自动字幕目录只形成稳定语言摘要。
- [ ] yt-dlp 调用选项证明无下载、无 Cookie/登录态、无 remote components。

## 验证

- [ ] `uv lock --check`
- [ ] `uv sync --locked`
- [ ] `uv run python -m pytest tests/unit/test_discovery.py`
- [ ] `uv run python -m pytest tests/integration/test_discovery_adapter.py`
- [ ] `uv run mypy src`
- [ ] `uv run ruff check .`
- [ ] `git diff --check`
- [ ] 可选受控冒烟：对一个已批准频道设置 `--limit 2`，只检查输出和数据库，不进入下载阶段。

## 预计触达文件

- `src/youtube_intel/discovery.py`
- `src/youtube_intel/providers/youtube.py`
- `tests/unit/test_discovery.py`
- `tests/integration/test_discovery_adapter.py`
- `tests/fixtures/youtube/` 下一个最小夹具文件
- `pyproject.toml`
- `uv.lock`
- `handoffs/TASK-004.md`

批准依赖为 `yt-dlp[default,deno]>=2026.7.4,<2026.8`，完整 Adapter、Repository consumer Protocol 和文件所有权以已接受的 `docs/decisions/ADR-004-discovery-ytdlp-contract.md` 为准。真实 YouTube 冒烟、Cookie、账号登录、remote components 和 ffmpeg 仍未授权。

## 复用决定

- 直接复用官方 `yt-dlp` Python API、锁定的 `yt-dlp-ejs` 与 Deno runtime；不自行实现 YouTube 页面解析、JavaScript challenge solver 或字幕目录协议。
- RSS 使用 Python 标准库，不再引入 HTTP/XML 包。
- `video-to-subtitle-summary-skill` 和 `yt2md` 只作为测试、语言排序、缓存与 Markdown 设计参考；本任务不得复制它们的 shell/付费 API/直接 Vault 写入架构。
- `youtube-skills` 依赖 TranscriptAPI 账号、密钥和远程服务，与 V1 本地优先及 DEC-01 冲突，不作为运行时依赖或 fallback。

## 交付证据

- 离线测试结果。
- 锁定的 yt-dlp、yt-dlp-ejs、Deno 和必要传递依赖版本摘要。
- `docs/REUSE_REGISTER.md` 中 TASK-004 复用选择与实际 Diff 一致的检查结果。
- 如运行真实冒烟，记录命令、时间、频道和脱敏结果；未运行则明确说明。
- Provider 页面/响应变更风险说明。

## 分配记录

- Assigned at: 2026-07-15
- Base: `main@dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-004`
- Branch: `grok/task-004-discovery-metadata`
- Implementer: Grok 独立会话，独占该 worktree 写入权。
- Reviewer: Codex 全新独立会话；仅在实现 commit 与交接证据完成后由主控启动。
- Implementer packet: `agent-prompts/TASK-004-IMPLEMENTER-GROK.md`
- Parallel task: TASK-003 Codex Implementer；不得读取或写入其 worktree，不等待其完成。

## 主控预审修复轮

- Pre-review at: 2026-07-15
- Reviewed source head: `392edfb897003c1583b538667d10a2a89926a94b`
- Git evidence: base、单提交父链、17 个允许文件、`git diff --check` 和干净 worktree 均通过；本轮不否定已通过的依赖、离线检查或未授权边界。
- Finding: `src/youtube_intel/providers/youtube.py` 把 `SAFE_YDL_OPTS`、`build_ydl_opts`、`map_info_dict_to_video_metadata` 等含自由 `dict`/`Mapping[str, Any]` 的 Adapter 内部边界显式列入 `__all__`；`YtDlpMetadataProvider` 也公开 `last_opts: list[dict[str, Any]]`。这违反 System Design §5.2、ADR-002 C-05 和本任务包的“外部自由 dict 只限 Adapter 内部”约束。
- Severity: `P1`；必须修复后才能启动 Reviewer。
- Status decision: 保持 `IN_PROGRESS`，退回原 Grok Implementer；不得基于 `392edfb...` 启动 Codex Reviewer。
- Correction packet: `agent-prompts/TASK-004-CORRECTION-GROK.md`

## 主控预审修复核对（二次）

- Checked source head: `10f5ffaaa3e8651a02e2f94c1736b8417acf3021`
- Git evidence: 修复提交仅触及前一轮允许的 3 个文件，`dcc7d85...HEAD` 仍处于原 TASK-004 的 17 文件范围，worktree 干净，`git diff --check` 通过；不否定实现者已报告的离线检查或未授权边界。
- Finding: 首个修复把原始映射的类型注解改为私有并将 `__all__` 收为类名，但仍定义非私有 `map_info_dict_to_video_metadata(info: object)`，并在公开 `YtDlpMetadataProvider.__init__` 保留 `ydl_factory: object | None` 与 `last_opts: object | None`。`__all__` 不是访问控制；用 `object` 包装自由 dict 也不使其成为冻结领域契约。两项均违反首轮修复包要求的“私有命名、不得用 Any/别名/无类型包装伪装公开接口”。
- Severity: `P1`；不得以 `10f5ffa...` 启动 Reviewer。
- Status decision: 保持 `IN_PROGRESS`，由原 Grok Implementer 做第二轮最小修复；这一轮允许更新原任务范围内的 `tests/integration/test_discovery_adapter.py`，以移除其对残余公开映射名的依赖。
- Correction packet: `agent-prompts/TASK-004-CORRECTION-2-GROK.md`

## 主控预审修复核对（三次）

- Checked source head: `9db800fc9f4d01a5b6348c5cc8b567f83dc442aa`
- Git evidence: source worktree 干净；第二轮修复 commit 仅为 `src/youtube_intel/providers/youtube.py`、`tests/unit/test_discovery.py`、`tests/integration/test_discovery_adapter.py`、`handoffs/TASK-004.md` 四个已批准文件；相对 `dcc7d85...` 的完整范围仍精确属于原 TASK-004 17 文件集合，`git diff --check` 通过。
- Public-contract evidence: `YtDlpMetadataProvider.__init__` 只保留 `timeout_seconds: float`；删除残余非私有 `map_info_dict_to_video_metadata`；raw dict、字段映射、factory、时钟和 options sink 都只使用 `_` 私有名称；`__all__` 仅为 `YtDlpMetadataProvider`。离线集成测试不再导入非私有 mapping helper，回归测试检查上述 Surface。
- Status decision: 主控预审 P1 已关闭；同步后状态为 `IN_REVIEW`，由全新独立 Codex Reviewer 审查。此条不是最终验收，不得设为 `ACCEPTED` 或 `DONE`。
- Reviewer packet: `agent-prompts/TASK-004-REVIEWER-CODEX.md`

## 独立审查拒绝与修复轮（三次）

- Review evidence: `f34cbb09d628ebb256bf5f2895adfd10dbd61812`，审查对象为 `9db800fc9f4d01a5b6348c5cc8b567f83dc442aa`；Reviewer 只提交 `handoffs/TASK-004.md`，完整 17 文件范围、依赖、复用、公开 Surface 与安全 options 均通过。
- Verdict: `REJECT`。P1：畸形 yt-dlp payload 逸出原始 `ValueError`；返回 `video_id` 不校验请求 ID；RSS 不完整 entry 被跳过仍推进游标；HTTP 404/403/503 的分类顺序使终态/重试语义反转。P2：RSS read 失败不关闭 response，`needs_auth` 可能标为 `PUBLIC`。P3：公开注解回归哨兵会漏掉 `Any`。
- Status decision: 回到 `IN_PROGRESS`，由原 Grok Implementer 从 source head `f34cbb...` 修复；不得以当前 evidence 启动第二个 Codex Reviewer 或设为 `ACCEPTED`。
- Correction packet: `agent-prompts/TASK-004-CORRECTION-3-GROK.md`

## Reviewer REJECT 修复核对（四次）

- Checked source head: `30932e1742e948683f9e1c0f63236451b8d731bd`，父提交为 review evidence `f34cbb09d628ebb256bf5f2895adfd10dbd61812`。
- Scope evidence: correction commit 只修改 `discovery.py`、`providers/youtube.py`、unit/integration discovery tests 与 handoff 五个已批准文件；相对 `dcc7d85...` 的完整范围仍为原 17 文件，worktree 干净，`git diff --check` 通过。
- Static evidence: safe malformed payload mapping、请求/响应 ID 核验、RSS 完整 entry 原子失败、HTTP 404/403/5xx 优先分类、read failure finally-close、`needs_auth -> RESTRICTED` 及 `Any/object` public-surface 哨兵均有实现和离线回归；未改变依赖、公共领域契约、无下载/无登录边界或 TASK-003。
- Status decision: 已进入 `IN_REVIEW`；不以主控预核验取代独立审查。TASK-003 Reviewer 已结束，现授权一个**全新、独立于首个 TASK-004 Reviewer 的 Codex 会话**审查本 head。
- Second-review packet: `agent-prompts/TASK-004-REVIEWER-2-CODEX.md`

## 第二次独立审查拒绝与修复轮（四次）

- Review evidence: `5d66c28d6bd02a7cf31a27ffe9a31a2479f9da58`，审查对象为 `30932e1742e948683f9e1c0f63236451b8d731bd`；父提交精确为 source head，范围仅 `handoffs/TASK-004.md`。
- Verdict: `REJECT`。P1-1：`providers/youtube.py` 的 `_coerce_age_limit()` 在非法 age_limit 时返回安全 `INVALID_RESPONSE`，但 `AppError.video_id=None`，未保存请求 video ID。P1-2：`discovery.py` 将 entry 缺失的 RSS channelId 回填为请求 channel，绕过完整性失败，仍保存候选并推进 cursor。
- 已独立通过：其他 malformed date/duration、请求/响应 ID mismatch、RSS 缺 videoId/published/title、较旧 entry 恢复、全部 response close、HTTP 404/403/429/503/599、正文脱敏、`needs_auth -> RESTRICTED`、公开 Surface、yt-dlp 安全 options、无下载/无 Cookie/无 remote components。
- Status decision: 回到 `IN_PROGRESS`，只退回原 Grok Implementer 修复上述两个 P1；不得修改依赖、公共契约、task 状态以外的控制面，亦不得启动第三位 Reviewer。
- Correction packet: `agent-prompts/TASK-004-CORRECTION-4-GROK.md`
