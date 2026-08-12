# YouTube Intelligence Agent 系统设计

- 版本：V1.8
- 状态：`APPROVED`
- 对应产品规格：`docs/PRD.md`
- 配置与领域契约：`docs/decisions/ADR-002-config-domain-contracts.md`
- SQLite 状态契约：`docs/decisions/ADR-003-sqlite-state-store-contract.md`
- 发现与 yt-dlp 契约：`docs/decisions/ADR-004-discovery-ytdlp-contract.md`
- 复用策略：`docs/decisions/ADR-005-reuse-first-delivery-policy.md`
- 字幕获取与缓存契约：`docs/decisions/ADR-006-subtitle-acquisition-contract.md`
- 本地模型与共享契约：`docs/decisions/ADR-007-local-model-pipeline-contracts.md`
- 云分析契约：`docs/decisions/ADR-008-cloud-analysis-contract.md`
- Obsidian 笔记契约：`docs/decisions/ADR-009-obsidian-note-contract.md`
- 本地转写持续处理契约：`docs/decisions/ADR-012-local-transcription-continuation-contract.md`
- 受限公开字幕 smoke 入口契约：`docs/decisions/ADR-013-restricted-public-subtitle-smoke-entry.md`
- 正式 console entry 打包契约：`docs/decisions/ADR-014-console-entrypoint-contract.md`

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

### 3.1 复用边界

- 通用能力优先复用标准库或已批准官方组件：SQLite、yt-dlp/EJS/Deno、MLX Whisper、Ollama、OpenAI SDK 和模板引擎。
- 外部组件只能位于 Adapter/Provider 边界后，不拥有领域对象、Pipeline/Job 状态、重试策略、审计或 Vault 写入规则。
- 完整第三方应用只作为设计/测试参考；直接依赖、选择性适配、许可证和否决证据见 `docs/REUSE_REGISTER.md`。
- 复用不得引入未批准账号、Cookie、远程服务、系统工具、动态代码下载或数据外发。

## 4. 核心组件职责

| 组件 | 只负责 | 不负责 |
|---|---|---|
| Source Provider | 按频道发现候选视频和游标 | 下载字幕、评分 |
| Metadata Provider | 标准化单个视频元数据 | 决定是否值得总结 |
| Transcript Service | 选择字幕或本地转写、验证并持久化规范文本 | 云端总结 |
| Scoring Service | 组装有限输入、解析并验证本地评分 | 写 Obsidian |
| Analysis Service | 对满足策略的视频生成深度分析 | 发现视频 |
| Pipeline Orchestrator | 驱动状态机、任务租约、重试和缓存 | 包含具体 Provider 逻辑 |
| State Repository | 事务化保存状态、任务和产物索引 | 保存密钥 |
| Knowledge Sink | 安全、原子、幂等写入笔记 | 修改 Vault 其他内容 |
| Weekly Reporter | 读取已完成记录并渲染周报 | 重新分析视频 |

Weekly Reporter 按 ADR-010 直接使用 reports upsert 与 Knowledge Sink，不创建 `video_id=None` 的 Pipeline Job；CLI 按 ADR-011 只编排已冻结服务，`weekly` 在周报服务整合后接入。

## 5. Provider 契约

以下为语义契约，不限定具体 Python 语法。

```python
class SourceProvider:
    def discover(channel, cursor) -> DiscoveryBatch: ...

class MetadataProvider:
    def fetch(video_id) -> VideoMetadata: ...

class TranscriptProvider:
    def fetch(video, language_preferences) -> TranscriptFetchResult: ...

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

### 5.2 跨模块输入输出

以下名称和字段为 V1 公共契约。集合在领域层使用只读序列；跨模块不得用自由形状 `dict` 替代具名对象。

| 对象 | 必需字段 | 可选字段与约束 |
|---|---|---|
| `ProviderCallMetadata` | `provider`、`started_at`、`finished_at` | `provider_version`、`model`、`diagnostics`；`diagnostics` 为 `DiagnosticEntry` 序列 |
| `DiagnosticEntry` | `code`、`message` | 消息必须安全化，不含密钥或字幕全文 |
| `DiscoveryCursor` | `channel_id` | `last_checked_at`、`latest_published_at`、`latest_video_id`、`provider_cursor` |
| `DiscoveryBatch` | `channel_id`、`video_ids`、`next_cursor`、`call` | `video_ids` 去重并保持 Provider 顺序；只有完整保存批次后才能推进 `next_cursor` |
| `TranscriptSample` | `head`、`body`、`tail`、`selected_char_count`、`source_content_hash`、`sampling_version` | 不可变；三段不重叠，版本固定为 `sampling-v1` |
| `ScoringInput` | `video`、`sample`、`transcript_content_hash`、`language`、`request_hash` | `sample.source_content_hash` 必须等于完整规范文本哈希；入选元数据的稳定顺序见 ADR-007 L-06 |
| `ScoringDecision` | `threshold`、`final_should_summarize`、`model_disagrees` | 最终值严格由 `score >= threshold` 推导，不覆盖模型建议 |
| `ScoringOutcome` | `result`、`decision`、`call` | `result` 保留模型原始 `should_summarize`；`call` 为对应评分调用元数据 |
| `AnalysisInput` | `video`、`transcript_text`、`transcript_content_hash`、`score`、`language`、`request_hash` | 文本必须已通过云端长度、隐私和预算策略 |
| `NotAvailable` | `reason_code`、`message`、`retryable`、`call` | `reason_code` 为 `NO_MATCHING_LANGUAGE`、`NO_CONTENT` 或 `CONTENT_UNAVAILABLE`；`retry_after_seconds` 仅在 Provider 给出时存在 |
| `TranscriptReady` | `outcome="ready"`、`artifact`、`call` | 只表示规范文本已经通过质量门禁；`call` 为 `ProviderCallMetadata` |
| `TranscriptionRequired` | `outcome="transcription_required"`、`reason`、`call`、`attempted_track_count` | `reason` 只允许 `NO_TRACKS`、`NO_MATCHING_LANGUAGE`、`ALL_CANDIDATES_INVALID`；真正失败继续使用 `AppError` |
| `NoteRef` | `kind`、`relative_path`、`content_hash` | `kind` 为 `video` 或 `weekly`；不得暴露 Vault 之外的路径 |
| `WeeklyReportItem` | `video`、`score`、`note_ref`、`one_sentence_summary` | 仅接受已完成且符合周报策略的项目 |
| `WeeklyReportInput` | `iso_year`、`iso_week`、`timezone`、`items`、`generated_at` | `items` 先按分数降序，再按 `video_id` 稳定排序 |

`request_hash` 由规范化输入、操作、Provider、模型以及 Prompt/Schema 版本共同生成。Provider 返回新对象，不原地修改输入对象。

`TranscriptFetchResult` 是 `TranscriptReady | TranscriptionRequired` 的具名判别联合。字幕格式只允许 `SubtitleFormat.JSON3 | VTT | SRT`；`TranscriptQualityFlag` 只允许 `ROLLING_CUES_DEDUPED`、`SPEAKER_LABELS_PRESENT`、`NON_SPEECH_MARKERS_PRESENT`，且只记录已通过质量门禁的非失败诊断。不得退回自由字符串、自由 `dict`、`Any` 或宽 `object`。`NotAvailable` 保留给其他 Provider 不可用语义；字幕“无轨道/无匹配/候选全无效”必须使用 `TranscriptionRequired`。

### 5.3 发现与字幕清单边界

- `DiscoveryBatch` 的提交点是“全部候选以 `DISCOVERED` 入库且 `next_cursor` 在同一事务提交”；不等待整批元数据成功。
- 元数据按视频独立 Job 获取和重试；单个不可用内容不得阻塞频道游标。
- TASK-004 通过官方 yt-dlp Python API 复用页面解析和 EJS challenge 能力，只公开有序去重的 `available_languages`。
- 人工/自动字幕轨道和临时下载 URL 不进入 `VideoMetadata`；TASK-005 在获取字幕时重新查询轨道明细。
- 完整契约、依赖范围和未授权行为见 ADR-004。

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
- `requested_language`：字幕来源时记录触发匹配的配置语言；Whisper 或无单一匹配语言时允许为空。
- `source_format`：人工/自动字幕为 `JSON3 | VTT | SRT`；Whisper 允许为空。
- `text_path`、可选 `timed_text_path`；两者必须是安全 DATA-relative path。
- `source_content_hash`、`source_byte_count`、`content_hash`、`char_count`、`segment_count`。
- `normalization_version`。
- `provider`、`model`、`created_at`。
- `quality_flags`：只读 `TranscriptQualityFlag` 序列，不使用任意字符串。

Provider 调用元数据属于 `TranscriptReady.call` / `TranscriptionRequired.call`；SQLite artifact key、临时字幕 URL 和本机绝对路径不得进入领域对象。

### 6.3 ScoreResult

- `schema_version`。
- `score`：0 到 10。
- `reason`：去除首尾空白后长度 `1..2000`。
- `topics`：`1..10` 个去重字符串，每项长度 `1..80`。
- `should_summarize`。
- 可选 `dimensions`，字段固定为 `technical`、`business`、`product`、`originality`、`practicality`、`industry_impact`；每项为 `0..10` 或缺省。
- `provider`、`model`、`prompt_version`、`request_hash`。

阈值判断由应用策略完成，不能完全信任模型给出的 `should_summarize`。两者不一致时记录诊断，并以配置策略为准。

### 6.4 AnalysisResult

字段固定如下：

| 字段 | 类型与基数 |
|---|---|
| `one_sentence_summary` | 字符串，长度 `1..500` |
| `core_points` | `AnalysisPoint`，`1..10` 项 |
| `key_facts` | `AnalysisPoint`，`0..20` 项，`kind` 必须为 `fact` |
| `product_opportunities` | `AnalysisPoint`，`0..10` 项 |
| `business_opportunities` | `AnalysisPoint`，`0..10` 项 |
| `actionable_directions` | `AnalysisPoint`，`0..10` 项 |
| `hypotheses_to_validate` | `AnalysisPoint`，`0..10` 项 |
| `action_recommendations` | `AnalysisPoint`，`0..10` 项 |
| `risks` | `AnalysisPoint`，`0..10` 项 |
| `keywords` | `1..20` 个去重字符串，每项长度 `1..80` |
| `evidence` | `EvidenceExcerpt`，`0..20` 项 |

Provider-neutral `AnalysisContent` 只包含上述业务字段；模型不能生成
`provider`、`model`、`prompt_version`、`request_hash` 或调用元数据。Adapter 严格
校验内容后，使用本地可信上下文封装带必需审计元数据的 `AnalysisResult`。

`AnalysisPoint` 包含 `text`、`kind` 和 `evidence_ids`：`text` 长度为 `1..2000`，
`kind` 只能为 `fact | inference | recommendation`，每个 Point 至少一个、
最多 10 个证据引用。证据来源精确到标题、频道、描述或 transcript sample，excerpt
必须是对应最小化输入的精确子串。V1 尚无规范文本到时间戳的稳定映射，
`start_seconds`/`end_seconds` 必须为空。

分析阶段返回不可变 `AnalysisOutcome`：

- `AnalysisCompleted(result, call)`；
- `AnalysisSkipped(reason, call | None, safe_message)`。

跳过原因固定为 `CLOUD_DISABLED`、`CREDENTIAL_UNAVAILABLE`、
`BUDGET_EXHAUSTED`、`INPUT_TOO_LARGE`、`PROVIDER_REFUSAL`；它们是业务结果，不
扩展 ADR-002 的八个 ErrorCode。

## 7. 三层状态模型

状态由不同对象分别承担，不能把同名值复制到多层：

| 类型 | 值 | 职责 |
|---|---|---|
| `PipelineStatus` | `DISCOVERED`、`METADATA_READY`、`DEFERRED`、`TRANSCRIPT_READY`、`SCORED`、`LOW_VALUE_READY`、`ANALYSIS_READY`、`NOTE_WRITTEN`、`COMPLETE`、`SKIPPED_DURATION_LIMIT` | 视频最近成功的业务进度或处置结果 |
| `ProcessingStage` | `DISCOVERY`、`METADATA`、`TRANSCRIPT`、`SCORING`、`ANALYSIS`、`NOTE_WRITE`、`WEEKLY_REPORT` | Job 的目标执行阶段 |
| `JobStatus` | `PENDING`、`RUNNING`、`RETRY_PENDING`、`SUCCEEDED`、`FAILED_FINAL` | 单次任务尝试和调度生命周期 |

`RETRY_PENDING` 和 `FAILED_FINAL` 只属于 `JobStatus`，不属于 `PipelineStatus`。

### 7.1 Pipeline 转换

```text
DISCOVERED
  -> METADATA_READY
  -> TRANSCRIPT_READY
  -> SCORED
       -> LOW_VALUE_READY -> COMPLETE
       -> ANALYSIS_READY -> NOTE_WRITTEN -> COMPLETE

METADATA_READY 且时长超过 180 分钟（无 --force）
  -> SKIPPED_DURATION_LIMIT

未结束直播
  -> DEFERRED
  -> METADATA_READY（条件满足后）
```

允许的成功转换只有：

| 当前 `PipelineStatus` | 可进入 |
|---|---|
| `DISCOVERED` | `METADATA_READY`、`DEFERRED` |
| `DEFERRED` | `METADATA_READY` |
| `METADATA_READY` | `TRANSCRIPT_READY`、`SKIPPED_DURATION_LIMIT` |
| `TRANSCRIPT_READY` | `SCORED` |
| `SCORED` | `LOW_VALUE_READY`、`ANALYSIS_READY` |
| `LOW_VALUE_READY` | `COMPLETE` |
| `ANALYSIS_READY` | `NOTE_WRITTEN` |
| `NOTE_WRITTEN` | `COMPLETE` |
| `COMPLETE`、`SKIPPED_DURATION_LIMIT` | 无；新 Pipeline 版本或显式强制重跑创建新 Job，不篡改历史 |

`ANALYSIS_READY` 表示分析阶段已经按策略完成：可以是 `AnalysisCompleted`，也可以
是 `AnalysisSkipped`。后者必须记录精确跳过原因，并允许 TASK-009 继续高价值笔记
路径，不能把“未调用云端”伪装成云分析成功。

### 7.2 Job 转换与恢复

```text
PENDING -> RUNNING -> SUCCEEDED
                   -> RETRY_PENDING -> PENDING
                   -> FAILED_FINAL
```

- Job 进入 `SUCCEEDED` 后，应用层才按转换表推进视频 `PipelineStatus`。
- Job 进入 `RETRY_PENDING` 或 `FAILED_FINAL` 时，视频保留最近成功的 `PipelineStatus`；`target_stage` 指明恢复阶段。
- 过期 `RUNNING` 租约由恢复逻辑转回可调度状态，并增加尝试审计，不能伪装成成功。
- 人工重跑创建新 `job_id`；旧 Job、错误码、次数和时间戳保持不变。

### 7.3 状态规则

- 状态只能按明确转换表前进；不得用文件存在与否推断完整业务状态。
- 每阶段成功时同时提交产物索引和新状态，或两者都不提交。
- `COMPLETE`、`SKIPPED_DURATION_LIMIT` 是视频处置终态；`SUCCEEDED`、`FAILED_FINAL` 是 Job 终态。
- 数据更新（如标题变化）不应让已完成视频从头重跑；只有输入哈希或 Pipeline 版本变化时按策略失效相关阶段。

## 8. SQLite 状态模型

V1.0 中的 `tasks` 与 `retry_queue` 合并为统一 `jobs`，避免两个队列状态漂移；`transcripts` 统一归入 `artifacts`。ADR-003 S-01 至 S-08 已批准最终物理 Schema、索引、事务、租约和 migration 规则；TASK-003 必须逐项实现，不得自行简化。

### 8.1 `videos`

| 字段 | 说明 |
|---|---|
| `video_id` PK | YouTube 视频 ID |
| `channel_id`, `channel_name` | 频道身份 |
| `title`, `description`, `source_url` | 当前元数据 |
| `published_at`, `duration_seconds` | 时间与时长 |
| `default_language`, `available_languages_json`, `live_status`, `availability` | 标准化状态 |
| `pipeline_status` | 最近成功的 `PipelineStatus`；失败尝试见 `jobs` |
| `pipeline_version` | 当前业务进度所属 Pipeline 版本 |
| `score`, `should_summarize` | 评分摘要 |
| `discovered_at`, `updated_at`, `completed_at` | 审计时间 |

### 8.2 `channel_cursors`

每频道一条游标，包含最后检查时间、最新已见发布时间/视频 ID、Provider 游标和最后错误。只有一次发现批次完整保存后才推进游标。

### 8.3 `jobs`

| 字段 | 说明 |
|---|---|
| `job_id` PK | 任务尝试身份 |
| `scope_key` | 频道、视频阶段或周报的稳定逻辑键 |
| `video_id` nullable | 频道发现和周报等全局任务可为空 |
| `job_type`, `target_stage` | 工作类型与 `ProcessingStage` |
| `pipeline_version` | 活动 Job 去重维度 |
| `status` | `JobStatus` |
| `attempt_count`, `max_attempts` | 尝试控制 |
| `available_at`, `lease_until` | 退避和崩溃恢复 |
| `last_error_code`, `last_error_message` | 诊断信息 |
| `created_at`, `updated_at` | 审计时间 |

部分唯一索引 `scope_key + pipeline_version` 覆盖视频和 `video_id IS NULL` 的全局任务，保证同一逻辑范围最多一个未完成 Job。

### 8.4 `job_attempts`

每次自动领取建立独立 attempt，记录编号、owner、开始/结束、租约、结果和安全化错误。`attempt_count` 是摘要，不能替代逐次历史；租约过期必须记录 `LEASE_EXPIRED`。

### 8.5 `artifacts`

记录字幕、规范文本、评分原始响应、分析结果和笔记等文件的路径、哈希、种类、Provider、模型、版本和创建时间。文件内容不直接塞入 SQLite。

### 8.6 `provider_calls`

以 `request_hash` 做唯一键，记录操作、Provider、模型、状态、响应产物、token/成本（可获得时）和耗时，用于昂贵调用去重与审计。

### 8.7 `reports`

以 `timezone + ISO week + report_type` 唯一，记录周期、路径、内容哈希、状态和更新时间。

### 8.8 `schema_migrations`

记录单调递增版本、名称、SQL checksum 和应用时间；`PRAGMA user_version` 镜像最新成功版本。migration 使用 `BEGIN IMMEDIATE` 全有或全无，历史 SQL 不得重写，V1 不提供 downgrade 或破坏性自动迁移。

## 9. 幂等与并发

- 视频身份只使用 `video_id`，标题不能作为主键。
- Provider 调用缓存键至少包含：操作、规范化输入哈希、Provider、模型、Prompt/Schema 版本。
- Obsidian 笔记文件名包含 `video_id`，先写同目录临时文件，再原子替换。
- 每个 Job 使用带过期时间的租约；默认只运行一个 Worker。未来增加并发时不改变语义。
- 所有写入使用调用方注入的 UTC 时钟；Job 领取、续租、过期回收和状态推进使用 expected-state CAS。
- 连接启用 `foreign_keys=ON`、`busy_timeout=5000`、`synchronous=NORMAL`；文件数据库初始化并验证 WAL。
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
- TASK-005 重新查询人工/自动字幕轨道；TASK-004 的 `available_languages` 只作为能力摘要，不缓存临时 URL。
- TASK-005 候选全局顺序为人工/自动、配置语言顺序、exact/base/variant、实际语言、JSON3/VTT/SRT、轨道名和 Provider 原始位置；候选质量失败时继续下一候选。
- 规范化使用严格 UTF-8、LF、HTML entity 单次解码和 NFC；删除时间行/样式控制内容，保留 speaker 与音效语义，并以 ADR-006 T-08 的资源和质量阈值判定候选。
- 原始请求键与 canonical 键分层版本化；普通缓存命中不联网探测，只有显式 refresh generation 重新枚举并生成新路径。
- 原始字幕与 canonical 文本使用现有 `SUBTITLE_SOURCE` / `TRANSCRIPT_CANONICAL`，同目录临时写、fsync、原子替换并验证 SHA-256；V1 不新增 manifest migration。
- 首次成功以当前 Job 写入 Artifact；缓存命中验证既有记录和文件后，以 `complete_stage(artifacts=(), provider_call=None)` 推进当前 Job/Pipeline，不修改 TASK-003 Repository 语义。
- V1 使用 `mlx-whisper`，默认模型为 `mlx-community/whisper-large-v3-turbo`；model
  revision、权重 hash、解码参数与资源门禁以 ADR-007 L-10、L-11、L-15 为准，运行时
  不得隐式联网。
- 按 ADR-012，成功的本地转写由独立应用服务在既有阶段事务中写入规范 Transcript Artifact、
  Provider-call 与 `METADATA_READY -> TRANSCRIPT_READY`；只接受已登记且哈希验证的 DATA 音频，
  缓存恢复必须验证 Provider-call/Artifact/文件/Job/Pipeline identity。该服务不实现模型下载、
  媒体获取、CLI production composition 或真实资源调用；外部转写与数据库提交之间仅为 at-most-once
  best effort。
- 成功转写后立即删除音频；失败/中断音频最多保留 7 天。删除确认与过期枚举使用
  `mark_artifact_deleted` / `list_expired_artifacts`，只处理 DATA 根下已登记且哈希匹配
  的文件；清理失败只告警，不让已完成转写失败。

字幕获取、质量阈值、错误映射、复用和恢复的完整冻结契约见 ADR-006 T-01 至 T-15。

## 11. 模型调用策略

### 11.1 本地评分

- 输入包括稳定顺序元数据和 `TranscriptSample`；最大内容长度按 Python Unicode code
  point 计，不是 token 限制。`n > M` 时按 ADR-007 L-05 的 `head/body/tail` 长度和
  中心正文规则采样，Prompt 标签不计入内容预算。
- `ScoreResult.should_summarize` 是模型建议；`ScoringDecision.final_should_summarize`
  必须由阈值策略决定，并记录 `model_disagrees`。评分阶段在同一事务写入原始/结构化
  Artifact、Provider call、`videos.score` 与最终 `videos.should_summarize`。
- 默认 `temperature=0.0`、`max_output_tokens=1200`、`max_transcript_chars=30000`，
  最小长度为 3；`max_description_chars=4000`，范围 0..20000。完整哈希维度、Prompt/
  Schema 版本、一次格式修复和错误映射以 ADR-007 L-05、L-06、L-09 为准。
- Ollama 只允许标准库访问受限 loopback `http` base URL；不自动启动、拉取模型、访问
  cloud tag 或远程地址。版本/digest 必须通过 `/api/tags` 预检，实际安装和调用另批。

### 11.2 云端分析

云端分析按 ADR-008 A-01 至 A-17 执行。固定副作用顺序是：验证高价值与上游
provenance、处理关闭、本地采样/token 预算、缓存、run 预算，最后才解析密钥并预留
Provider call。

实际出站只能序列化 `AnalysisPayload`：video_id、标题、频道名、发布时间、时长、
默认语言、最多 4,000 字符公开描述、字幕/输出语言和
`cloud-token-sampling-v1` 样本。禁止发送路径、Vault/用户内容、内部 ID/哈希、
诊断、评分维度、密钥名或自由 metadata。

本地 `tiktoken` 只支持显式 model-to-encoding 映射，使用同一个纯请求构造函数计算
固定 instructions、Schema 和 payload。发送上限 28,000 tokens，为 Responses
framing 预留 2,000；实际 Provider 硬上限 30,000。V1 不调用云端
`/v1/responses/input_tokens`。

`o200k_base` 的 rank 表只能读取包内
`youtube_intel/resources/o200k_base.tiktoken`，固定 SHA-256 为
`446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`。资源缺失、
内容哈希不匹配或无法解析均必须在任何云端副作用前失败关闭；禁止使用 tiktoken
内置的 HTTP 下载或任意缓存/网络回退。该资源的分发许可证结论由 TASK-014 发布门禁
最终确认。

官方 OpenAI Responses Adapter 固定 `store=False`、`max_retries=0`、
`truncation="disabled"`、无 tools/stream/custom base URL、120 秒 timeout，不发送
temperature，输出默认 4,000 tokens（范围 `256..8,000`）。Structured Outputs
失败不做格式修复调用；每视频最多一次推理请求，单 run 最多 5 次真实出站请求。

OpenAI SDK 禁止在主进程导入。TASK-008 的 Adapter 必须通过绝对 Python executable
启动独立子进程；子进程环境不得复制父环境，只允许以固定字面量构造
`PYTHONNOUSERSITE=1`、`PYTHONDONTWRITEBYTECODE=1`、`PYTHONUTF8=1`。禁止传入
`OPENAI_*`、`AZURE_*`、代理变量、`PYTHONPATH` 或任何 `*_TOKEN`、`*_KEY`、
`*_SECRET`、`*_PASSWORD`。子进程先完成 SDK 导入并通过非敏感握手确认，再由父进程
通过专用匿名管道传入临时密钥；密钥不得进入环境变量、argv、文件、Pydantic 对象、
异常、诊断或日志。子进程退出后必须关闭管道并丢弃临时值。

原始响应使用 `ANALYSIS_RAW/RAW_RESPONSE_30D`，结构化结果使用
`ANALYSIS_STRUCTURED/LONG_LIVED`。成功路径复用现有 `complete_stage` 原子完成
Artifact、Provider call、Pipeline 和 Job；关闭/缓存/超限/预算/缺凭据均零调用。

## 12. 错误分类与重试

| 类别 | 示例 | 默认行为 |
|---|---|---|
| `TRANSIENT_NETWORK` | 超时、临时连接失败 | 指数退避 + 抖动，最多 3 次 |
| `RATE_LIMITED` | 429/服务限流 | 尊重 Retry-After 后重试 |
| `PROVIDER_UNAVAILABLE` | Ollama 未启动、云服务 5xx | 重试；达到上限后终态 |
| `INVALID_RESPONSE` | 模型 JSON/Schema/语义不合法 | Ollama 评分最多一次格式修复；OpenAI Structured Outputs 不修复 |
| `CONTENT_UNAVAILABLE` | 私有、删除、地区限制 | 直接终态，不重试 |
| `CONFIG_INVALID` | 路径、阈值、Provider 配置错误 | 本次运行失败，处理前退出 |
| `PERMISSION_DENIED` | Vault 不可写 | 不盲目重试，提示人工处理 |
| `LOCAL_RESOURCE` | 磁盘不足、内存不足 | 停止领取新任务并告警 |

错误日志必须包含 `run_id`、`job_id`、`video_id`、阶段、错误码和安全化消息。

V1 重试配置默认值为：`max_attempts=3`、`base_delay_seconds=2`、`max_delay_seconds=60`、`jitter_ratio=0.2`。`max_attempts` 为正整数，延迟为正数，基础延迟不得大于最大延迟，抖动范围为 `0..1`。通用 HTTP、本地模型和云模型默认超时分别为 `30`、`300`、`120` 秒，均必须为正数。`RATE_LIMITED` 返回有效 `Retry-After` 时以它为准，不受本地指数退避上限截断。

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
- `data_dir`、`logs_dir`、`templates_dir` 必须是相对项目根目录的路径；项目根由应用启动时确定，不能取决于进程当前工作目录。
- `vault_root` 必须是绝对路径；`vault_subdir` 必须是相对路径，且规范化后仍位于 `vault_root` 内。
- 配置加载和每次写入前都重新解析最终目标并检查边界；`..`、绝对子路径和符号链接逃逸必须失败。
- 视频模板固定打包为 `src/youtube_intel/templates/video.md`，使用
  `ImmutableSandboxedEnvironment`、`StrictUndefined`、无任意 loader/include/import/
  globals，只传入预转义且设限的 primitive；不执行用户模板。
- 视频路径固定为 `Videos/<safe-title>--<video_id>.md`；标题按 ADR-009 N-05 做
  NFC、安全字符、Windows 保留名和 120 UTF-8 bytes 处理。首次路径建立后不因标题
  变化自动 rename/delete。
- Vault child 使用 anchored directory FD、`O_NOFOLLOW/O_DIRECTORY` 和前后
  inode/device 复核；只允许创建受管 Videos，拒绝 symlink、路径逃逸、casefold
  冲突、非受管占位和多个 video_id 候选。
- 管理区/用户区使用 ADR-009 N-07 的四个 v1 marker。用户区 bytes 原样保留；
  marker、Frontmatter、UTF-8 或 provenance 异常均失败关闭，不接管旧文件。
- Frontmatter 顺序固定为 type、video_id、title、channel、published、source、
  language、transcript_source、score、topics、processed_at、pipeline_version。
- 同目录临时文件采用 0600、写入/fsync/回读哈希、竞态复核、`os.replace` 和目录
  fsync；失败只清理本次临时文件，绝不删除最终笔记。
- 文件成功后复用现有 `complete_stage` 完成 VIDEO_NOTE Artifact、
  `ANALYSIS_READY -> NOTE_WRITTEN` 和 Job。replace 后数据库失败通过验证完整文件
  补账，只承诺 at-most-once best effort。
- 已 `NOTE_WRITTEN/COMPLETE` 的普通重跑只验证现有 NoteRef；成功笔记主动刷新延期
  到 TASK-010，不为 TASK-009A 修改 `state.py` 或 Schema。

## 14. 配置与密钥

配置层级固定为：内建默认值 < YAML < CLI 参数。每层的未知字段都必须拒绝。密钥值不进入该层级；配置只能保存环境变量名，实际值从进程环境或后续批准的系统密钥存储解析。

### 14.1 V1 配置字段

`channels[]` 来自 `config/channels.yaml`，其余字段来自 `config/settings.yaml`；CLI 只覆盖其明确公开的字段。

| 字段 | 默认值 | 校验与语义 |
|---|---:|---|
| `channels[].channel_id` | 无 | 必填、非空、在列表中唯一 |
| `channels[].enabled` | `true` | 布尔值 |
| `channels[].priority` | `50` | 整数 `0..100`，数值越大越优先 |
| `general.timezone` | `Asia/Shanghai` | 有效 IANA 时区 |
| `general.output_language` | `zh-CN` | 非空语言标签 |
| `general.transcript_languages` | 无 | 必填的非空、有序、去重语言标签列表 |
| `execution.worker_concurrency` | `1` | V1 只接受 `1` |
| `execution.max_video_duration_minutes` | `180` | 正数；只有显式 `--force` 可覆盖 |
| `thresholds.summary_score` | `7.0` | 数值 `0..10` |
| `weekly.top_n` | `10` | 整数 `1..100` |
| `retry.max_attempts` | `3` | 正整数 |
| `retry.base_delay_seconds` | `2` | 正数且不大于 `max_delay_seconds` |
| `retry.max_delay_seconds` | `60` | 正数 |
| `retry.jitter_ratio` | `0.2` | 数值 `0..1` |
| `timeouts.http_seconds` | `30` | 正数 |
| `timeouts.local_model_seconds` | `300` | 正数 |
| `timeouts.cloud_model_seconds` | `120` | 正数 |
| `transcription.model` | `mlx-community/whisper-large-v3-turbo` | 非空模型标识 |
| `transcription.model_revision` | `a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb` | 固定 40 位 revision；权重大小/hash 与 ADR-007 L-11 一致 |
| `transcription.parameter_policy_version` | `mlx-whisper-v1` | 非空；解码参数固定并进入参数哈希 |
| `transcription.min_free_disk_gib` | `8` | 正数资源门禁 |
| `transcription.min_available_memory_gib` | `6` | 正数资源门禁 |
| `transcription.max_audio_bytes` | `2000000000` | 正整数资源门禁 |
| `local_scoring.model` | 无 | 必填的非空 Ollama 模型标识 |
| `local_scoring.base_url` | `http://127.0.0.1:11434` | 仅 `http` loopback；无 userinfo/query/fragment/路径 |
| `local_scoring.expected_model_digest` | 无 | 必填 `sha256:` digest；须与 `/api/tags` 精确匹配 |
| `local_scoring.temperature` | `0.0` | 数值 `0..2` |
| `local_scoring.max_output_tokens` | `1200` | 正整数 |
| `local_scoring.max_transcript_chars` | `30000` | 整数 `>=3`，字符数而非 token 数 |
| `local_scoring.max_description_chars` | `4000` | 整数 `0..20000`，按 Unicode code point 截断 |
| `cloud.enabled` | `false` | 布尔值 |
| `cloud.provider` | `openai` | V1 只接受 `openai` |
| `cloud.model` | 无 | `enabled=true` 时必填 |
| `cloud.api_key_env` | `OPENAI_API_KEY` | 只保存合法环境变量名，不保存值 |
| `cloud.max_calls_per_run` | `5` | 正整数且不得超过 `5` |
| `cloud.max_local_input_tokens_per_video` | `28000` | 正整数，必须小于等于 Provider 硬上限；本地 tiktoken 保守门禁 |
| `cloud.max_input_tokens_per_video` | `30000` | 正整数且不得超过 `30000` |
| `cloud.max_description_chars` | `4000` | 整数 `0..20000`，按 Unicode code point 截断 |
| `cloud.max_output_tokens` | `4000` | 整数 `256..8000`；V1 不发送 temperature |
| `storage.data_dir` | `data` | 项目根相对路径 |
| `storage.logs_dir` | `logs` | 项目根相对路径 |
| `storage.templates_dir` | `templates` | 项目根相对路径 |
| `storage.vault_root` | 无 | 必填绝对路径；示例只能使用占位路径 |
| `storage.vault_subdir` | 无 | 必填安全相对路径 |

同一优先级频道使用 `channel_id` 升序作为稳定次级排序。环境变量名必须匹配 `[A-Za-z_][A-Za-z0-9_]*`。配置对象的 `repr`、校验错误、日志和测试快照不得解析或显示密钥值。

### 14.2 启动校验

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
smoke-public-subtitles --temporary-root ABSOLUTE_NEW_EMPTY_DIR --video-id ID [--video-id ID] [--video-id ID]
```

launchd 只负责按时间启动 CLI，不包含业务重试逻辑。安装、卸载或加载 launchd 配置属于用户明确执行的操作；初始化脚本不得静默注册服务。

ADR-022 增加正式 production composition root：非 `doctor` 业务命令在配置校验后幂等
bootstrap 项目内 DATA/logs/SQLite migration 与既有 Vault 根下的受管子目录，再组合 RSS、
yt-dlp metadata/subtitle、SQLite Planner/Orchestrator、本地 Ollama、Cloud policy、Obsidian
与 weekly 服务。CLI 仍保留 `Operations` 注入点，但正式默认路径不再使用占位实现。
`doctor` 继续零写入；为满足首次用户诊断，它只对配置已限定为 loopback 的 Ollama 执行一次
有界 `/api/tags` 读取并核对模型 digest，不调用业务 Provider、YouTube、云端或凭据。此点由
ADR-022 对 ADR-011 O-02 的“不得探测 loopback”作窄范围替代。

`smoke-public-subtitles` 是 ADR-013 专用的发布 QA 组合入口，不是通用下载或处理命令。它不读取 YAML、
密钥、Cookie 或默认运行目录；只接受 1–3 个显式公开视频 ID 和一个不存在的绝对临时根，创建其中的临时
SQLite、DATA、测试 Vault 与脱敏 JSONL 审计目录。每个 ID 最多一次元数据读取、一次字幕目录读取和一次选中
字幕正文读取，固定 HTTP timeout 为 30 秒，不自动重试，不下载媒体，不推进 Pipeline/Job，不写真实 Vault，
不调用 ffmpeg、模型、Ollama 或 OpenAI。正常 `check/process/retry/weekly/doctor` 的参数和 fail-closed
组合语义保持不变。

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

产品与技术方向见 `docs/PRD.md` 的 `DEC-*`、`docs/PRODUCT_DECISIONS.md` 和
ADR-002 至 ADR-009，均已批准。ADR-008 A-01 至 A-17、ADR-009 N-01 至 N-15 已
批准 TASK-008A/TASK-009A 的
三项精确直接依赖、必要传递依赖、网络包下载、锁文件和离线命令；执行仍须固定
worktree/角色/文件范围。TASK-008A Correction 1 另获一次 OpenAI 官方
`o200k_base.tiktoken` Blob 下载和固定资源提交授权，不构成一般网络授权。以下继续
单独授权：真实密钥或付费云调用、云端 token-count 请求、真实 YouTube/字幕、
Cookie/账号登录、remote components、ffmpeg、媒体下载、写入真实 Vault、最终 Vault
文件删除/移动、加载 launchd，以及任何超出 V1 白名单的改变。

## 19. Intelligence V2 架构

ADR-023 在不新增 Pipeline 状态或 SQLite migration 的前提下，把 `ANALYSIS_READY` 的
产品语义收紧为“存在当前配置下经过验证的 Structured Knowledge”。Cloud disabled 不再
产生空分析成功结果。

所有视频先由 Local Scoring 决定阈值；高价值视频再由 Deep Analysis Router 按
`local-only | hybrid | cloud` 选择 Provider。Local 与 Cloud 返回同一 Knowledge V2，
Renderer、Weekly、Artifact 与 cache 不感知具体 Provider，只消费可信 provenance。

Evidence Registry 由应用从当前 canonical Transcript 建立，模型只能返回 Registry 中的
ID；excerpt 与可选 timestamp 由应用补全。无法从 timed subtitle 稳定映射时必须省略时间，
不得使用模型生成的时间戳。Weekly V2 默认只读取已验证 Structured Knowledge 与其证据
引用，不读取 Obsidian 用户区或发送本周全部 Transcript。

request/execution identity 必须包含 provider、model/digest、requested/executed mode、
output language、Prompt/Schema/sampling/privacy version 与 Transcript/input hash。任何
配置切换都不得绕过 TASK-015 的 provider/model/current-config binding。
