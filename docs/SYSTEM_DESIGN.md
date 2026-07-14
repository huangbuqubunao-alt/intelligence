# YouTube Intelligence Agent 系统设计

- 版本：V1.0
- 状态：`APPROVED`
- 对应产品规格：`docs/PRD.md`

## 1. 设计目标

本设计服务于单机、本地优先、可恢复的批处理 Agent。核心原则是：外部 Provider 可替换、核心编排与数据源解耦、昂贵步骤可缓存、重复运行幂等、每个失败可定位。

## 2. 系统上下文

```text
launchd / CLI
      |
      v
Pipeline Orchestrator <----> SQLite State Store
      |
      +--> Source Provider ------> YouTube channel RSS
      +--> Metadata Provider ----> yt-dlp
      +--> Transcript Providers -> subtitles / audio / MLX Whisper
      +--> Scoring Provider -----> Ollama
      +--> Summary Provider -----> optional OpenAI
      +--> Knowledge Sink -------> Obsidian Vault
      +--> Report Generator -----> Weekly Markdown
      |
      +--> Artifact Cache + Structured Logs
```

## 3. 分层与依赖方向

```text
CLI / Scheduler
       |
Application: orchestration, use cases, retry policy
       |
Domain: contracts, entities, state transitions
       |
Ports: repositories and provider protocols
       |
Adapters: SQLite, filesystem, RSS/yt-dlp, MLX Whisper, Ollama, OpenAI, Obsidian
```

依赖只允许向内：Domain 不得导入具体 SDK、文件系统或 SQLite 实现。Adapter 失败必须映射为应用层可识别的统一错误类型。

## 4. 核心组件职责

| 组件 | 只负责 | 不负责 |
|---|---|---|
| Source Provider | 按频道发现候选视频和游标 | 下载字幕、评分 |
| Metadata Provider | 标准化单个视频元数据 | 决定是否值得总结 |
| Transcript Service | 选择字幕或本地转写并产出规范文本 | 云端总结 |
| Scoring Service | 组装有限输入、解析并验证本地评分 | 写 Obsidian |
| Analysis Service | 对满足策略的视频生成深度分析 | 发现视频 |
| Pipeline Orchestrator | 驱动状态机、任务租约、重试和缓存 | 包含具体 Provider 逻辑 |
| State Repository | 事务化保存状态、任务和产物索引 | 保存密钥 |
| Knowledge Sink | 安全、原子、幂等写入笔记 | 修改 Vault 其他内容 |
| Weekly Reporter | 读取已完成记录并渲染周报 | 重新分析视频 |

## 5. Provider 契约

以下为语义契约，不限定具体 Python 语法。

```python
class SourceProvider:
    def discover(channel, cursor) -> DiscoveryBatch: ...

class MetadataProvider:
    def fetch(video_id) -> VideoMetadata: ...

class TranscriptProvider:
    def fetch(video, language_preferences) -> TranscriptArtifact | NotAvailable: ...

class ScoringProvider:
    def score(ScoringInput) -> ScoreResult: ...

class SummaryProvider:
    def summarize(AnalysisInput) -> AnalysisResult: ...

class KnowledgeSink:
    def upsert_video_note(video, transcript, score, analysis) -> NoteRef: ...
    def upsert_weekly_report(report) -> NoteRef: ...
```

所有 Provider 返回结构化对象；不得把未解析的命令输出或模型自由文本直接传入核心流程。

### 5.1 通用约束

- 每次调用接收 `request_id` 或由调用方生成稳定输入哈希。
- 返回值包含 Provider 名称、版本/模型、开始结束时间和可选诊断信息。
- 超时、限流、不可用、无内容、无权限、非法响应必须使用不同错误码。
- Provider 不自行决定全局重试；只报告是否可能重试和建议等待时间。
- Provider 不写 SQLite 状态；由应用层在事务边界更新。

## 6. 核心数据对象

### 6.1 VideoMetadata

- `video_id`：稳定主键。
- `channel_id`、`channel_name`。
- `title`、`description`、`source_url`。
- `published_at`、`duration_seconds`。
- `default_language`、`available_languages`。
- `live_status`：`none | upcoming | live | ended`。
- `availability`：`public | unavailable | private | deleted | restricted`。

### 6.2 TranscriptArtifact

- `video_id`、`language`。
- `source_type`：`manual_subtitle | auto_subtitle | whisper`。
- `text_path`、可选 `timed_text_path`。
- `content_hash`、`char_count`、`segment_count`。
- `provider`、`model`、`created_at`。
- `quality_flags`：空文本、重复率异常、乱码或过短等。

### 6.3 ScoreResult

- `schema_version`。
- `score`：0 到 10。
- `reason`、`topics`、`should_summarize`。
- 可选维度子分。
- `provider`、`model`、`prompt_version`、`request_hash`。

阈值判断由应用策略完成，不能完全信任模型给出的 `should_summarize`。两者不一致时记录诊断，并以配置策略为准。

### 6.4 AnalysisResult

字段遵循 PRD 的深度分析契约，额外包含 `schema_version`、`provider`、`model`、`prompt_version`、`request_hash` 和事实/推断标记。

## 7. Pipeline 状态机

```text
DISCOVERED
  -> METADATA_READY
  -> TRANSCRIPT_READY
  -> SCORED
       -> LOW_VALUE_READY -> COMPLETE
       -> ANALYSIS_READY -> NOTE_WRITTEN -> COMPLETE

METADATA_READY 且时长超过 180 分钟（无 --force）
  -> SKIPPED_DURATION_LIMIT

任一处理中状态
  -> RETRY_PENDING
  -> 原失败阶段

不可恢复或超过重试上限
  -> FAILED_FINAL

未结束直播
  -> DEFERRED
  -> METADATA_READY（条件满足后）
```

### 7.1 状态规则

- 状态只能按明确转换表前进；不得用文件存在与否推断完整业务状态。
- 每阶段成功时同时提交产物索引和新状态，或两者都不提交。
- `COMPLETE`、`FAILED_FINAL`、`SKIPPED_DURATION_LIMIT` 是终态；人工重跑/`--force` 会创建新任务尝试，不篡改历史尝试。
- 数据更新（如标题变化）不应让已完成视频从头重跑；只有输入哈希或 Pipeline 版本变化时按策略失效相关阶段。

## 8. SQLite 逻辑模型

V1.0 中的 `tasks` 与 `retry_queue` 合并为统一 `jobs`，避免两个队列状态漂移；`transcripts` 统一归入 `artifacts`。最终 SQL 由 `TASK-003` 提交并需人工审批。

### 8.1 `videos`

| 字段 | 说明 |
|---|---|
| `video_id` PK | YouTube 视频 ID |
| `channel_id`, `channel_name` | 频道身份 |
| `title`, `source_url` | 当前元数据 |
| `published_at`, `duration_seconds` | 时间与时长 |
| `language`, `live_status`, `availability` | 标准化状态 |
| `pipeline_status`, `failed_stage` | 当前状态 |
| `score`, `should_summarize` | 评分摘要 |
| `discovered_at`, `updated_at`, `completed_at` | 审计时间 |

### 8.2 `channel_cursors`

每频道一条游标，包含最后检查时间、最新已见发布时间/视频 ID、Provider 游标和最后错误。只有一次发现批次完整保存后才推进游标。

### 8.3 `jobs`

| 字段 | 说明 |
|---|---|
| `job_id` PK | 任务尝试身份 |
| `video_id` nullable | 周报等全局任务可为空 |
| `job_type`, `target_stage` | 工作类型 |
| `status` | pending/running/retry_pending/succeeded/failed_final |
| `attempt_count`, `max_attempts` | 尝试控制 |
| `available_at`, `lease_until` | 退避和崩溃恢复 |
| `last_error_code`, `last_error_message` | 诊断信息 |
| `created_at`, `updated_at` | 审计时间 |

同一视频、阶段和 Pipeline 版本最多存在一个未完成逻辑任务。

### 8.4 `artifacts`

记录字幕、规范文本、评分原始响应、分析结果和笔记等文件的路径、哈希、种类、Provider、模型、版本和创建时间。文件内容不直接塞入 SQLite。

### 8.5 `provider_calls`

以 `request_hash` 做唯一键，记录操作、Provider、模型、状态、响应产物、token/成本（可获得时）和耗时，用于昂贵调用去重与审计。

### 8.6 `reports`

以 `timezone + ISO week + report_type` 唯一，记录周期、路径、内容哈希、状态和更新时间。

### 8.7 `schema_migrations`

记录单调递增 Schema 版本和应用时间。迁移必须可在数据库副本上验证；V1 不承诺自动回滚破坏性迁移。

## 9. 幂等与并发

- 视频身份只使用 `video_id`，标题不能作为主键。
- Provider 调用缓存键至少包含：操作、规范化输入哈希、Provider、模型、Prompt/Schema 版本。
- Obsidian 笔记文件名包含 `video_id`，先写同目录临时文件，再原子替换。
- 每个 Job 使用带过期时间的租约；默认只运行一个 Worker。未来增加并发时不改变语义。
- 周报通过稳定周期键 upsert；内容排序固定，保证相同输入得到相同结果。
- 进程在外部调用成功但落库前崩溃时，下次先查本地产物/Provider 调用缓存，再决定是否重调。

## 10. Transcript 决策链

```text
人工字幕（按语言偏好）
  -> 不可用/质量校验失败
自动字幕（按语言偏好）
  -> 不可用/质量校验失败
下载音频
  -> Whisper 本地转写
  -> 文本规范化和质量校验
```

- “永不重复转写”修订为“相同音频哈希 + Whisper 实现/模型 + 参数版本不重复转写”；升级模型后允许显式重建。
- 原字幕和规范文本分开保存，避免清洗规则变化后必须重新下载。
- V1 使用 `mlx-whisper`，默认模型为 `mlx-community/whisper-large-v3-turbo`，模型和参数可配置。
- 成功转写后立即删除音频；失败/中断音频最多保留 7 天。清理失败只告警，不让已完成转写失败。

## 11. 模型调用策略

### 11.1 本地评分

- 输入包括元数据和受配置限制的字幕片段。
- 字幕截取应尽量覆盖开头、正文和结尾，而非只取前 2000 token；具体采样算法由 `TASK-007` 验证。
- 温度、最大输出和超时显式配置。
- JSON 通过严格 Schema 验证；修复失败进入重试。

### 11.2 云端分析

只有同时满足以下条件才调用：

1. OpenAI Provider 显式启用；默认关闭。
2. 分数达到配置阈值。
3. 隐私/长度策略允许当前输入。
4. 本次运行不超过 5 次云调用，单视频发送不超过 30,000 输入 token。

输入只来自公开视频元数据和规范字幕，不包含 Obsidian 内容。短文本完整发送，超限文本按开头/正文/结尾采样。原始响应写入受控缓存，日志只记录路径、哈希和用量；模型名称不写死在核心代码中。

## 12. 错误分类与重试

| 类别 | 示例 | 默认行为 |
|---|---|---|
| `TRANSIENT_NETWORK` | 超时、临时连接失败 | 指数退避 + 抖动，最多 3 次 |
| `RATE_LIMITED` | 429/服务限流 | 尊重 Retry-After 后重试 |
| `PROVIDER_UNAVAILABLE` | Ollama 未启动、云服务 5xx | 重试；达到上限后终态 |
| `INVALID_RESPONSE` | 模型 JSON 不合法 | 一次格式修复，再按可重试处理 |
| `CONTENT_UNAVAILABLE` | 私有、删除、地区限制 | 直接终态，不重试 |
| `CONFIG_INVALID` | 路径、阈值、Provider 配置错误 | 本次运行失败，处理前退出 |
| `PERMISSION_DENIED` | Vault 不可写 | 不盲目重试，提示人工处理 |
| `LOCAL_RESOURCE` | 磁盘不足、内存不足 | 停止领取新任务并告警 |

错误日志必须包含 `run_id`、`job_id`、`video_id`、阶段、错误码和安全化消息。

## 13. 文件与 Obsidian 设计

```text
data/
  state.sqlite
  transcripts/<video_id>/source.<ext>
  transcripts/<video_id>/canonical.txt
  cache/<operation>/<request_hash>.json
logs/YYYY-MM-DD.jsonl

<vault>/<configured-root>/
  Videos/<safe-title>--<video_id>.md
  Weekly/YYYY-Www.md
```

- 所有路径基于配置根目录解析并做边界校验。
- 笔记渲染使用外部模板。
- 自动管理区可使用明确标记；`我的思考` 为用户区，upsert 时必须保留。
- Dataview Frontmatter 值使用稳定类型和 ISO 时间。

## 14. 配置与密钥

建议配置层级：默认值 < YAML < CLI 参数；密钥不进入该层级，只从环境变量/系统密钥存储解析。

启动时完成：

- YAML Schema 校验。
- 阈值、重试、并发、路径和时区校验。
- 启用 Provider 的可用性预检。
- Vault 写入目标的边界与权限预检。
- 云端模式下仅检查密钥是否存在，不输出其值。

批准工程基线为 Python 3.12、uv、`pyproject.toml` 和提交版本库的 `uv.lock`。运行时与开发依赖必须限制在 `docs/PRODUCT_DECISIONS.md` 的白名单；白名单外依赖返回审批。

## 15. CLI 与调度边界

目标命令语义：

```text
check [--channel ID] [--limit N]
process [--video ID] [--resume]
retry [--video ID] [--failed-only]
weekly [--week YYYY-Www]
doctor
```

launchd 只负责按时间启动 CLI，不包含业务重试逻辑。安装、卸载或加载 launchd 配置属于用户明确执行的操作；初始化脚本不得静默注册服务。

## 16. 测试与验证架构

- 核心状态机和策略使用纯函数单元测试。
- Provider 使用契约测试和 Fake Adapter，默认测试不访问网络、真实 Vault 或云端模型。
- SQLite 测试使用临时目录并验证事务、唯一约束、租约回收和迁移。
- 文件测试验证路径穿越、原子替换、冲突标题和用户区保留。
- 端到端夹具覆盖人工字幕、自动字幕、Whisper、低分、高分和阶段失败恢复。
- 真实网络冒烟首选 OpenAI 官方频道最新 2 个已结束公开视频，Y Combinator 备用；实际视频 ID 写入验收报告。
- 真实网络、本地模型、付费云模型测试单独标记并分别获得所需授权。

## 17. 设计风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| YouTube 页面/字幕接口变化 | 发现或下载中断 | Adapter 隔离、固定夹具、清晰错误码 |
| Whisper 在本机资源消耗高 | 超时或磁盘膨胀 | 时长上限、模型可配、音频清理、单并发 |
| LLM 输出漂移 | 解析失败或知识质量不稳 | Schema、Prompt 版本、少量人工黄金样例 |
| 重跑覆盖用户笔记 | 数据损失 | 稳定用户区、原子写、集成测试 |
| SQLite/文件双写不一致 | 状态与产物漂移 | 临时产物、哈希、补偿检查、阶段事务 |
| 成本失控或隐私外发 | 财务/隐私风险 | 显式开关、阈值、预算、最小发送、审计 |

## 18. 已批准基线与仍需任务级审批的事项

产品与技术方向见 `docs/PRD.md` 的 `DEC-*` 和 `docs/PRODUCT_DECISIONS.md`，均已批准。以下动作仍须在对应任务中单独授权：实际安装/升级依赖、最终 SQLite Schema、真实密钥或付费云调用、写入真实 Vault、加载 launchd，以及任何超出 V1 白名单的改变。
