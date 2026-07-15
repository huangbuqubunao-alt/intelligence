# TASK-004：频道发现与元数据

- Status: `ACCEPTED`
- Assignee: `Grok`
- Reviewer: `Codex`（第五次独立审查 `APPROVE`；review evidence `d4d6d01ceba3b9524305bb41ece81b8783f3db4b`）
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

## 第二次审查 P1 修复核对（五次）

- Checked source head: `54c0ab201388cba35e481d7a511f21575946ad14`，父提交为第二次 review evidence `5d66c28d6bd02a7cf31a27ffe9a31a2479f9da58`。
- Scope evidence: correction 4 精确修改 `providers/youtube.py`、`discovery.py`、两份 discovery 测试与 handoff 五个已批准文件；相对 `dcc7d85...` 的完整范围仍为原 17 文件，worktree 干净，`git diff --check` 通过。
- Static evidence: `_coerce_age_limit()` / `_map_availability()` 接受请求 video ID，非法 age_limit 返回 `INVALID_RESPONSE`、nonretryable、METADATA 且保留身份；RSS entry channelId 缺失或不匹配立即 `INVALID_RESPONSE`，不再回填请求 channel。unit/integration 回归验证不保存候选/不推进 cursor 与较旧条目恢复。
- Status decision: 进入 `IN_REVIEW`；授权一个**全新、独立于所有此前 TASK-004 Implementer 与 Reviewer 会话的 Grok Reviewer**，不得以主控核验取代独立审查。
- Reviewer packet: `agent-prompts/TASK-004-REVIEWER-3-GROK.md`

## 第三次独立审查与主控组合验收

- Reviewed implementation head: `54c0ab201388cba35e481d7a511f21575946ad14`。
- Review evidence: `1883367d313623c42d9d3624b16307ca8d502709`，父提交精确为 reviewed head，范围仅 `handoffs/TASK-004.md`。
- Reviewer verdict: `APPROVE`。`uv lock --check`、`uv sync --locked`、unit 33、integration 6、全量 86、mypy、Ruff、CLI help 与固定 Diff 检查全部通过；AC-1 至 AC-5、ADR-004 D-01 至 D-08 在 TASK-004 独立分支/Fake Repository 范围内全部 PASS，无 P0/P1/P2/P3。Reviewer 未运行真实 YouTube、Cookie/登录、remote components、ffmpeg 或媒体/字幕下载。
- 主控组合契约探针：`SQLiteStateRepository` 不能满足当前 `DiscoveryRepository`。运行时 `isinstance(..., DiscoveryRepository) == False`；TASK-004 需要 `get_cursor`、`upsert_metadata`、`mark_unavailable`，而 main 的 TASK-003 提供 `get_channel_cursor`、`upsert_video_metadata`、`mark_video_unavailable`；双方 `save_discovery_batch` 还在 `expected_revision`、`pipeline_version`、`now` 和返回值上不一致。
- Severity: `P1`。这不是对第三次 Reviewer 已覆盖项目的否定，而是 ADR-004 D-08 明确推迟到两项整合后执行的真实 SQLite 组合契约门禁；当前实现若直接合入，`DiscoveryService` 首次读取 cursor 即无法调用 SQLite Repository。
- Status decision: **不进入 `ACCEPTED`**，回到 `IN_PROGRESS`。原 Grok Implementer 必须先把包含 TASK-003 的最新控制面 main 合入 TASK-004 source 分支，再做 correction 5；不得 rebase、reset、cherry-pick、改写历史或修改 main。
- Correction 5 ownership: 只在 TASK-004 已批准文件中对齐 consumer Protocol/Service/Fake，并在 `tests/integration/test_discovery_adapter.py` 增加真实 `SQLiteStateRepository` 组合测试；不得修改 `state.py`、migration、Schema、`domain.py`、依赖或锁文件。
- Contract rule: 保留单一 Repository 语义和 TASK-003 已接受的具名方法，不新增重复 SQLite wrapper，不让生产 `discovery.py` 导入具体 `SQLiteStateRepository`。应用边界必须显式提供 cursor revision、`pipeline_version` 和 UTC `now`；公共注解不得以 `Any`、宽 `object` 或自由 `dict` 掩盖不兼容。
- Correction packet: `agent-prompts/TASK-004-CORRECTION-5-GROK.md`。

## Repository 兼容修复与 correction 5A 核对

- Source sync merge: `eb9246bf5ce650441aaa2d8b8c7f37f22fe6779d`，父提交为第三次 review evidence `1883367d...` 与控制面 main `58c79af...`；该 merge 只把已完成 TASK-003 与控制面同步到 source，不是 correction 产品提交。
- Correction 5 code evidence: `d87253e4b6203232ccb933604f0523ef6d868ba8`。consumer Protocol/Service/Fake 已改用 TASK-003 的 `get_channel_cursor`、`save_discovery_batch`、`upsert_video_metadata`、`mark_video_unavailable` 具名 API，并增加真实临时 SQLite 组合测试；correction commit 只修改本轮允许文件。
- 主控预审发现固定范围 `58c79af...d87253e...` 的 handoff 有尾随空白，Service CAS 证据直接调用 Repository、Fake 对未知视频 unavailable 的行为与 SQLite 不一致，且缺 naive UTC/空 pipeline version 的无副作用边界测试。该预审不否定已有 Repository API 对齐，但在审查前要求 5A 补证。
- Correction 5A head: `9750df2503a1aee135fdfbcca9f1706bcc9bd8de`，父提交精确为 `d87253e...`，只修改 `discovery.py`、unit/integration discovery tests 与 handoff 四个允许文件；source worktree 干净，Git 身份正确。
- 5A 关闭项：固定范围 `git diff --check 58c79af...9750df...` 返回 0；真实 Service 层竞态使 intervening SQLite commit 保留、stale batch 全不写并抛 `ConcurrencyConflict`；Fake 对未知视频与 SQLite 一致返回 `False` 且不写 unavailable；naive `now`/空 `pipeline_version` 返回 `CONFIG_INVALID` 且 Provider/Repository 零副作用。
- Implementer 自报门禁：state integration 30、discovery unit 35、discovery integration 10、全量 131、mypy、Ruff、CLI、build 全 PASS；sdist/wheel 均含 migration SQL。主控只核验了 Git、Diff 与静态证据，这些数字必须由 Reviewer 独立重跑。
- Scope evidence: `58c79af...9750df...` 的完整产品差异仍精确为原 TASK-004 17 路径；未修改 `domain.py`、`state.py`、migration、依赖范围或锁定版本之外的文件。
- Status decision: 同步后进入 `IN_REVIEW`。原 Grok Implementer 必须停止写入并关闭/暂停会话；授权第四个全新独立 Codex Reviewer，且不得由前三次 Reviewer 或实现者自审替代。
- Reviewer packet: `agent-prompts/TASK-004-REVIEWER-4-CODEX.md`。

## 第四次独立审查拒绝与 Correction 6

- Reviewed implementation head: `9750df2503a1aee135fdfbcca9f1706bcc9bd8de`。
- Review evidence: `d510794ffccf54948f967f010685aef1c0a02f3d`，唯一父提交精确为 reviewed head，范围仅 `handoffs/TASK-004.md`；source/main 均干净。
- Reviewer checks: state integration 30、discovery unit 35、discovery integration 10、全量 131、`mypy src`、Ruff、CLI、build、migration 包含性和固定 Diff 均 PASS；运行时 Protocol、真实 SQLite 原子性/CAS、Fake parity 与 correction 3/4 安全回归通过。
- Verdict: `REJECT`。P0/P2/P3 均为 0，P1 共 2 项：
  1. `ChannelCursorView` / `VideoRecordView` 用可变 Protocol attributes 表达只读字段，导致 TASK-003 frozen records 虽运行时匹配，却不能在真实 mypy wiring 中作为 `DiscoveryRepository` 返回类型；现有 `mypy src` 没有组合调用而漏报。
  2. discovery/metadata Service 只按 truthiness 检查 `pipeline_version`，纯空白值会先调用 Provider，再泄漏 SQLite `IntegrityError`，未满足处理前 `CONFIG_INVALID` 和零副作用。
- Acceptance impact: AC-1 至 AC-5、D-01 至 D-06 继续 PASS；D-07/D-08 因两个 P1 为 FAIL。不得基于 131 tests 全绿提前验收。
- Status decision: 回到 `IN_PROGRESS`，退回原 Grok Implementer；Correction 6 只允许修改 `discovery.py`、两份 discovery 测试与 handoff，不得修改 `state.py`、Schema/migration、domain、Provider、依赖或 lock。
- Required proof: 使用严格只读 Protocol 表达使 frozen records 通过真实 mypy wiring；discovery/metadata 对多种纯空白版本在任何 Provider/Repository 调用前返回安全 `CONFIG_INVALID`，并保留现有全部组合、安全和无下载回归。
- Correction packet: `agent-prompts/TASK-004-CORRECTION-6-GROK.md`。

## Correction 6 主控预核验与第五次审查授权

- Correction 6 head: `7272528a3c5603087446251ee96ae4766fedeb96`，唯一父提交为第四次 review evidence `d510794ffccf54948f967f010685aef1c0a02f3d`；source worktree 干净，Git 身份正确。
- Scope evidence: correction commit 精确修改 `discovery.py`、两份 discovery 测试和 handoff 四个允许文件；`58c79af...HEAD` 完整产品范围仍为原批准 17 路径，固定 Diff check 为 0；无 state/migration/domain/provider/dependency/lock/control-plane 变化。
- Static evidence: `ChannelCursorView` / `VideoRecordView` 的只读字段改为 property，未使用 Any/object/cast/ignore/wrapper 或具体 SQLite import；discovery/metadata Service 在外部调用前以 `pipeline_version.strip()` 拒绝纯空白。
- Implementer self-report: state 30、unit 36、integration 10、全量 132、mypy src、真实 wiring probe、Ruff、CLI、build/migration 全 PASS；这些数字尚待 Reviewer 独立复跑。
- Orchestrator focused pre-review: 同一真实 mypy wiring probe PASS；whitespace focused unit `1 passed`。该预核验只证明可进入审查，不是 `APPROVE` 或最终验收。
- Status decision: 同步后进入 `IN_REVIEW`；Grok Implementer 停止写入。授权第五个全新独立 Codex Reviewer 审查固定 head，不得提前设为 `ACCEPTED/DONE`。
- Reviewer packet: `agent-prompts/TASK-004-REVIEWER-5-CODEX.md`。

## 第五次独立审查与主控验收

- Reviewed implementation: `7272528a3c5603087446251ee96ae4766fedeb96`。
- Review evidence: `d4d6d01ceba3b9524305bb41ece81b8783f3db4b`，唯一父提交为 reviewed implementation，范围仅 `handoffs/TASK-004.md`；source/main 均干净。
- Reviewer verdict: `APPROVE`。state 30、unit 36、integration 10、全量 132、mypy src、真实静态 wiring probe、Ruff、CLI、build/migration 和固定 Diff 全 PASS。
- Independent evidence: frozen Repository records 静态/运行时可替代；五类纯空白版本在两条公开 Service 路径均为 `CONFIG_INVALID`、Provider call count 0、真实 SQLite 无变化；correction 3/4 安全回归通过。
- Acceptance matrix: AC-1 至 AC-5、ADR-004 D-01 至 D-08 全 PASS；P0/P1/P2/P3 均无。跳过项仅为未授权真实 YouTube/字幕、认证和媒体路径。
- 主控验收：Reviewer、范围、红线、复用、许可证记录和命令证据一致；TASK-004 进入 `ACCEPTED`，等待最终 Product Integrator。此状态不是 `DONE`，不得提前解锁 TASK-005。
- Integrator packet: `agent-prompts/TASK-004-INTEGRATOR.md`。
