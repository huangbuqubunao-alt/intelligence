# TASK-004 Grok Implementer Task Packet

## 身份

你是 Grok，担任 `TASK-004` 的唯一 Implementer。你只实现频道发现与 YouTube 元数据 Adapter，不领取 TASK-003 或后续任务，不承担 Reviewer、主控验收或整合职责。

## 固定上下文

在 TASK-004 worktree 中按顺序完整读取：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. `docs/PROJECT_STATUS.md`
4. `docs/PRD.md` 第 4、6、8、9、13、14、15 节
5. `docs/SYSTEM_DESIGN.md` 第 3、4、5、6、7、9、12、16、17、18 节
6. `docs/REUSE_REGISTER.md` 全文
7. `docs/decisions/ADR-004-discovery-ytdlp-contract.md` 全文
8. `docs/decisions/ADR-005-reuse-first-delivery-policy.md`
9. `tasks/TASK-004-discovery-metadata.md`
10. `handoffs/TEMPLATE.md`
11. 主线任务包：`/Users/hua/Documents/youtubek agent/agent-prompts/TASK-004-IMPLEMENTER-GROK.md`

如任一文件冲突、公共领域字段需要改变，或实现必须扩大范围，立即停止并输出 `DECISION NEEDED`，不得自行选择解释。

## 开工包

- Task: `TASK-004`
- Role: `Implementer`
- Agent: `Grok`
- Base: `main@dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-004`
- Branch: `grok/task-004-discovery-metadata`
- Reviewer: Codex 全新独立会话；仅在实现 commit 后由主控启动
- Parallel now: TASK-003 Codex Implementer，位于另一个 worktree
- Waiting: TASK-005 及后续任务

基线说明：该 worktree 从任务进入 `READY` 的关闭提交创建，因此本地公共任务卡仍显示 `READY/UNASSIGNED`；角色分配随后只提交到 `main` 控制面，不进入实现分支。这是预期隔离，不是规格冲突。以本任务包的角色、worktree 和 branch 为本轮执行授权；不要 pull、merge 或 cherry-pick 分配状态 commit。

## Reuse decision

- `DIRECT`：官方 `yt-dlp[default,deno]>=2026.7.4,<2026.8` Python API、锁定的 `yt-dlp-ejs`/Deno runtime，以及 Python 标准库 `urllib.request`、`xml.etree.ElementTree`、`datetime`。
- `REFERENCE`：`imlewc/video-to-subtitle-summary-skill@2c794d74` 的无下载防御思路、语言排序测试和夹具设计；不复制其 shell、ffmpeg、付费代理或直接输出架构。
- `REFERENCE`：`hailanlan0577/yt2md@8a845642` 的 URL/ID 规范化与缓存思路；不复制依赖或 Vault 写入。
- `REJECT`：`Xpos587/yt2md` 的 TLS 禁用/页面正则实现，以及 `ZeroPointRepo/youtube-skills` 的 TranscriptAPI 远程账号、密钥和付费依赖。
- 本项目自有：发现游标语义、Repository consumer Protocol、错误映射、Pipeline/Job 边界和审计要求。

交接报告必须记录锁定的直接/传递依赖版本、来源/许可证复核、实际参考了什么、没有复制什么，以及离线 Fake 如何证明 Adapter 可替换。

## 允许范围

只允许提交以下文件/目录范围：

- `src/youtube_intel/discovery.py`
- `src/youtube_intel/providers/youtube.py`
- `tests/unit/test_discovery.py`
- `tests/integration/test_discovery_adapter.py`
- `tests/fixtures/youtube/**` 下完成测试所需的最小固定夹具
- `pyproject.toml`
- `uv.lock`
- `handoffs/TASK-004.md`

测试缓存和虚拟环境可由验证命令生成，但不得提交。不得修改 `src/youtube_intel/domain.py`、`src/youtube_intel/state.py`、CLI、字幕/音频模块、公共任务状态、ADR、其他测试或其他 worktree。若 Python 包结构事实证明必须新增 `providers/__init__.py` 或任何第九个范围，先停止并请求主控批准，不得自行添加。

## 已批准依赖与权限

- 唯一新增直接运行时依赖：`yt-dlp[default,deno]>=2026.7.4,<2026.8`。
- 允许 uv 联网下载并锁定该依赖及其 `default`/`deno` extras 所需传递依赖，允许修改本任务范围内的 `pyproject.toml` 与 `uv.lock`。
- 允许执行：

  ```bash
  uv add 'yt-dlp[default,deno]>=2026.7.4,<2026.8'
  uv lock --check
  uv sync --locked
  ```

- 不新增 `httpx`、XML 库、`youtube-transcript-api`、ffmpeg Python 包或其他直接依赖，不升级现有依赖或工具链。
- 包下载授权不等于真实 YouTube 请求授权。真实 YouTube 冒烟、Cookie、账号登录、浏览器会话、remote components、ffmpeg、字幕/音频/视频下载均未授权。

## 冻结公共边界

直接消费 TASK-002 已冻结的 `ChannelRef`、`DiscoveryCursor`、`DiscoveryBatch`、`ProviderCallMetadata`、`VideoMetadata`、`AppError`、`ErrorCode`、`SourceProvider` 和 `MetadataProvider`。不得修改字段、枚举或 Protocol。

- `SourceProvider.discover(channel, cursor) -> DiscoveryBatch`
- `MetadataProvider.fetch(video_id) -> VideoMetadata`
- `DiscoveryBatch.video_ids` 必须有序、去重；`next_cursor.channel_id` 与请求频道一致。
- `VideoMetadata.available_languages` 只保存人工字幕语言首次出现顺序，再追加自动字幕新增语言；不暴露轨道 URL、格式或 manual/auto 类型。
- Adapter 对外错误必须形成安全、具名的 `AppError` 数据，不新增 `ErrorCode`。如实现需要 task-scope typed exception，可在允许文件内以安全 payload 承载 `AppError`；若必须把新 wrapper 变成跨模块公共契约，则停止并输出 `DECISION NEEDED`。

TASK-004 不拥有 SQLite 实现。`discovery.py` 只能定义窄 consumer Protocol/Fake 所需语义：读取当前 cursor、以 expected cursor 原子保存 `DiscoveryBatch`、upsert `VideoMetadata`、标记不可用候选。不得导入 TASK-003 的具体 Repository 类。

## 实现要求

### RSS Source Adapter

1. 仅使用标准库 `urllib.request`、`xml.etree.ElementTree` 与日期解析；使用配置的 HTTP timeout、明确 User-Agent 和有限响应读取。
2. 正常输出保持 RSS Provider 顺序；批内第一次出现的 `video_id` 保留，重复丢弃。
3. 依据 `published_at + video_id` 与 cursor 判断新候选；同时间以 video ID 打破游标比较平局，但返回集合仍保持 Provider 顺序。
4. 比当前 cursor 旧但数据库未知的条目不自动历史回填；空批次只更新 `last_checked_at`，不清空既有其他 cursor 字段。
5. 超时、HTTP/限流、非法 XML 与非法响应映射为不同批准错误码；异常不得包含原始响应正文、Cookie、本机路径或敏感请求头。
6. `discover` 只返回 `DiscoveryBatch`，不直接写 SQLite 或推进持久化游标。

### 发现批次应用服务

1. 使用窄 Repository consumer Protocol/Fake 保存批次；全部候选以 `DISCOVERED` 落库且 expected cursor CAS 成功后，才能在同一事务推进 `next_cursor`。
2. 任一候选或 cursor 写入失败时整批回滚；重复发现不创建第二条记录或倒退 Pipeline。
3. 元数据按单视频独立处理；一个视频失败不得回滚已提交的候选/游标或其他视频。
4. 不实现 Job 调度、重试算法或具体 SQLite；只证明调用边界与事务语义可由 TASK-003 实现消费。

### yt-dlp Metadata Adapter

1. 使用官方 Python API，不启动 shell/subprocess，不加载用户 Cookie、账号、`.netrc`、浏览器会话或外部 CLI 配置。
2. 固定选项必须等价于单视频、`skip_download=True`、`noplaylist=True`、安静且不写字幕/音频/视频/缩略图；不启用 remote components。
3. 外部自由 `dict` 只存在 Adapter 内部，立即映射为已批准具名 `VideoMetadata`；核心应用不得依赖原始 dict。
4. 正确标准化公开视频、Shorts、upcoming/live/ended、private/deleted/restricted/unavailable；无法形成完整元数据时不得用空字符串伪造对象。
5. 填充标题、频道、描述、URL、发布时间、时长、默认语言、稳定语言摘要、直播状态和 availability。
6. 网络超时、限流、Provider 不可用、非法响应和内容不可用分别映射；Adapter 不自行做全局重试或写 Job 状态。

## 离线测试要求

先写失败测试，再做最小实现。默认检查必须完全离线，至少覆盖：

- RSS 正常顺序、批内重复、已见/新视频、同发布时间平局、旧且未知条目、空批次。
- RSS 超时、HTTP/限流、超出响应大小、非法 XML；安全错误不包含响应正文或本机路径。
- Fake Repository 证明候选与 cursor 全有或全无、expected cursor 冲突回滚、元数据失败不回滚已提交批次。
- yt-dlp 固定 info fixtures 映射全部 `VideoMetadata` 字段、标题更新、Shorts、upcoming/live/ended、public/private/deleted/restricted。
- 人工/自动字幕目录只产生稳定、有序、去重语言摘要，不暴露 URL 或轨道细节。
- 捕获传给 yt-dlp 的选项，证明无下载、无 Cookie/登录态、无 remote components、无 ffmpeg 路径。
- 超时、限流、解析错误和内容不可用得到不同 `ErrorCode`；消息不含原始响应、Cookie、密钥或绝对路径。
- 相同 fixture/cursor 结果稳定；重复批次不产生重复持久化事件。
- 现有 TASK-002 契约测试继续通过，`domain.py` 零修改。

真实网络测试必须标记但本轮不得运行；不得因未授权真实站点波动修改离线断言。

## 执行流程

1. 复述目标、验收标准、Reuse decision、允许范围、唯一依赖和所有未授权行为。
2. 核对：

   ```bash
   pwd
   git branch --show-current
   git rev-parse HEAD
   git status --short
   git config --get user.useConfigOnly
   git var GIT_AUTHOR_IDENT
   ```

   必须位于指定 worktree/branch/base，工作树干净，`user.useConfigOnly=true`，身份为 `Mozhu <huangbuqubunao@gmail.com>`；不符立即停止。

3. 添加唯一批准依赖：

   ```bash
   uv add 'yt-dlp[default,deno]>=2026.7.4,<2026.8'
   ```

   记录直接和传递依赖的实际锁定版本。网络沙箱失败时，可仅对该已批准命令申请联网权限；不得替换 extras 或版本范围。

4. 使用测试驱动的最小增量实现；每个增量后运行最相关的聚焦测试。
5. 从 `handoffs/TEMPLATE.md` 创建 `handoffs/TASK-004.md`，加入 D-01 至 D-08 追踪表、依赖锁摘要、yt-dlp 选项证据、错误安全化证据、复用/许可证证据、未运行真实冒烟声明和剩余风险。
6. 运行全部检查：

   ```bash
   uv lock --check
   uv sync --locked
   uv run python -m pytest tests/unit/test_discovery.py
   uv run python -m pytest tests/integration/test_discovery_adapter.py
   uv run python -m pytest
   uv run mypy src
   uv run ruff check .
   git diff --check
   git status --short
   ```

7. 人工复核捕获的 yt-dlp 参数与错误文本，明确证明未下载媒体/字幕、未读取 Cookie/账号、未启用 remote components、未调用 ffmpeg、未泄露响应正文。
8. 完整复核 `dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176...HEAD` 和所有未提交/未跟踪文件；范围必须精确落在批准文件/目录，无生成物、媒体、真实响应、密钥、Cookie 或私人路径。
9. 全部通过后创建范围明确的 commit，建议消息：`feat: add YouTube discovery and metadata adapters`。不得合并 main 或改变公共任务状态。

同一失败连续出现两次后停止重复方法，保留命令、关键错误、文件和尝试方案。任何公共契约、依赖、范围或真实网络需求必须返回主控，不得自行修改任务卡或 ADR。

## 最终输出

```text
Task: TASK-004
Role: Implementer
Branch/worktree:
Base commit:
Head commit:
Changed files:
Acceptance criteria: PASS/FAIL/BLOCKED per item
Checks: command + result summary
Dependency lock summary: direct/extras/transitive versions
ADR-004 traceability: D-01 through D-08
yt-dlp option evidence:
Error/redaction evidence:
Reuse/license evidence:
Real YouTube smoke: NOT RUN (not authorized)
Diff review:
Skipped checks:
Remaining risks:
Decision needed: None | details
```
