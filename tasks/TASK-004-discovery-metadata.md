# TASK-004：频道发现与元数据

- Status: `IN_PROGRESS`
- Assignee: `Grok`
- Reviewer: `Codex`（全新独立会话；等待实现 commit）
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
