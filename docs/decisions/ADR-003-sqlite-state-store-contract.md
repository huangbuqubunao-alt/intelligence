# ADR-003：冻结 V1 SQLite 状态存储契约

## 状态

Accepted

## 日期

2026-07-14

## 批准记录

产品负责人在主控对话中明确批准：

```text
批准 ADR-003 S-01 至 S-08。
```

## 背景

`TASK-003` 的只读预检确认，现有系统设计已经批准 SQLite 的逻辑模型、三层状态、租约恢复、游标原子推进和调用缓存方向，但仍不足以直接实现物理 Schema。当前空白包括完整列定义、空值与约束、Pipeline 版本位置、全局 Job 去重、自动重试的逐次审计、Provider call 并发预留和 SQL migration 的打包方式。

这些决定会被 `TASK-004`、`TASK-005`、`TASK-009`、`TASK-010`、`TASK-011` 和 `TASK-012` 共同消费。若由实现者临时决定，将导致并行分支的 Repository 语义不兼容。本 ADR 冻结 V1 的最终物理契约并构成 TASK-003 的任务级 Schema 批准；TASK-003 仍须等待 TASK-002 完成并由主控正式分配后才能写入。

## 决策

### S-01：SQLite 类型、时间与通用约束

- 使用 Python 3.12 标准库 `sqlite3`，不新增 ORM 或数据库依赖。
- 所有时间列使用 UTC RFC 3339 `TEXT`，规范格式为 `YYYY-MM-DDTHH:MM:SS.ffffffZ`；写入前由应用层规范化，测试使用可注入时钟，不依赖 SQLite `CURRENT_TIMESTAMP` 或本机时区。
- 布尔值使用 `INTEGER`，只允许 `0`、`1` 或在字段明确可选时为 `NULL`。
- 枚举使用 `TEXT` 和 `CHECK` 约束；哈希使用小写十六进制 SHA-256 `TEXT`。
- 金额不使用浮点数；Provider 成本使用可空的 `cost_microusd INTEGER`。
- 所有 ID 去除首尾空白后必须非空。V1 不暴露删除业务记录的 Repository 方法；父记录外键统一 `ON DELETE RESTRICT`。
- JSON 只用于 `available_languages_json` 这类有界列表；写入前规范化为紧凑 JSON。SQLite 不保存字幕、模型原始响应或其他正文。

### S-02：最终表、列与索引

#### `schema_migrations`

| 列 | SQLite 定义 | 语义 |
|---|---|---|
| `version` | `INTEGER PRIMARY KEY CHECK (version > 0)` | 单调递增版本 |
| `name` | `TEXT NOT NULL` | migration 名称 |
| `checksum` | `TEXT NOT NULL` | SQL 文件 SHA-256 |
| `applied_at` | `TEXT NOT NULL` | UTC 应用时间 |

#### `videos`

| 列 | SQLite 定义 | 语义 |
|---|---|---|
| `video_id` | `TEXT PRIMARY KEY` | YouTube 稳定身份 |
| `channel_id` | `TEXT NOT NULL` | 发现批次即可提供 |
| `channel_name` | `TEXT` | 元数据成功后填写 |
| `title` | `TEXT` | 元数据成功后填写 |
| `description` | `TEXT` | 完整持久化 `VideoMetadata` |
| `source_url` | `TEXT` | 规范视频 URL |
| `published_at` | `TEXT` | 可空 UTC 时间 |
| `duration_seconds` | `INTEGER CHECK (duration_seconds IS NULL OR duration_seconds >= 0)` | 可空时长 |
| `default_language` | `TEXT` | 与领域字段同名 |
| `available_languages_json` | `TEXT NOT NULL DEFAULT '[]'` | 有序、去重语言列表 |
| `live_status` | `TEXT` + `CHECK` | 可空；非空时只允许 `none/upcoming/live/ended` |
| `availability` | `TEXT` + `CHECK` | 可空；非空时只允许 `public/unavailable/private/deleted/restricted` |
| `pipeline_status` | `TEXT NOT NULL` + `CHECK` | `PipelineStatus` 全部批准值 |
| `pipeline_version` | `TEXT NOT NULL` | 当前业务进度所属 Pipeline 版本 |
| `score` | `REAL CHECK (score IS NULL OR (score >= 0 AND score <= 10))` | 可空最终分数 |
| `should_summarize` | `INTEGER` + 布尔 `CHECK` | 可空策略结果 |
| `discovered_at` | `TEXT NOT NULL` | 首次发现时间，不被 upsert 覆盖 |
| `updated_at` | `TEXT NOT NULL` | 最近状态/元数据更新时间 |
| `completed_at` | `TEXT` | 处置终态时间 |

候选视频刚入库时只要求 `video_id`、`channel_id`、`pipeline_status=DISCOVERED`、`pipeline_version` 和审计时间；不得用空字符串伪造尚未获取的元数据。元数据 upsert 不得让已完成视频倒退状态，也不得覆盖 `discovered_at`。

索引：`(channel_id, published_at, video_id)`、`(pipeline_status, updated_at)`、`(availability, updated_at)`。

#### `channel_cursors`

| 列 | SQLite 定义 | 语义 |
|---|---|---|
| `channel_id` | `TEXT PRIMARY KEY` | 每频道一条 |
| `last_checked_at` | `TEXT` | 最近完整批次时间 |
| `latest_published_at` | `TEXT` | 最近候选发布时间 |
| `latest_video_id` | `TEXT` | 同时间的稳定游标补充 |
| `provider_cursor` | `TEXT` | Provider 不透明游标 |
| `last_error_code` | `TEXT` | 最近安全化错误码 |
| `last_error_message` | `TEXT` | 不含响应正文或密钥 |
| `revision` | `INTEGER NOT NULL DEFAULT 0 CHECK (revision >= 0)` | Repository 内部 CAS 版本 |
| `updated_at` | `TEXT NOT NULL` | UTC 更新时间 |

#### `jobs`

| 列 | SQLite 定义 | 语义 |
|---|---|---|
| `job_id` | `TEXT PRIMARY KEY` | 一次逻辑 Job；人工重跑创建新 ID |
| `scope_key` | `TEXT NOT NULL` | 稳定逻辑范围键 |
| `video_id` | `TEXT REFERENCES videos(video_id) ON DELETE RESTRICT` | 视频 Job 必填；频道/周报 Job 为空 |
| `job_type` | `TEXT NOT NULL` + `CHECK` | `CHANNEL_DISCOVERY/VIDEO_STAGE/WEEKLY_REPORT` |
| `target_stage` | `TEXT NOT NULL` + `CHECK` | `ProcessingStage` 全部批准值 |
| `pipeline_version` | `TEXT NOT NULL` | 活动 Job 去重维度 |
| `status` | `TEXT NOT NULL` + `CHECK` | `PENDING/RUNNING/RETRY_PENDING/SUCCEEDED/FAILED_FINAL` |
| `attempt_count` | `INTEGER NOT NULL DEFAULT 0` | 已开始尝试数，`0..max_attempts` |
| `max_attempts` | `INTEGER NOT NULL CHECK (max_attempts > 0)` | 创建时固化 |
| `available_at` | `TEXT NOT NULL` | 允许重新调度时间 |
| `lease_owner` | `TEXT` | `RUNNING` 时必填 |
| `lease_until` | `TEXT` | `RUNNING` 时必填 |
| `last_error_code` | `TEXT` | 最近错误码 |
| `last_error_message` | `TEXT` | 最近安全化错误 |
| `created_at` | `TEXT NOT NULL` | UTC 创建时间 |
| `updated_at` | `TEXT NOT NULL` | UTC 更新时间 |
| `finished_at` | `TEXT` | `SUCCEEDED/FAILED_FINAL` 时必填 |

约束补充：视频阶段 Job 必须有 `video_id`；频道发现与周报 Job 必须没有 `video_id`。`RUNNING` 必须同时有 `lease_owner/lease_until`，其他状态不得保留租约。终态必须有 `finished_at`。

`scope_key` 由应用层按以下规范生成：

- 频道发现：`channel:<channel_id>:discovery`
- 视频阶段：`video:<video_id>:<processing_stage>`
- 周报：`weekly:<timezone>:<YYYY-Www>:<report_type>`

建立部分唯一索引 `UNIQUE(scope_key, pipeline_version) WHERE status IN ('PENDING','RUNNING','RETRY_PENDING')`，同时覆盖 `video_id IS NULL` 的全局 Job。另建 `(status, available_at, created_at, job_id)` 调度索引和 `(video_id, target_stage, created_at)` 审计索引。

#### `job_attempts`

`attempt_count + last_error` 不能满足“每次尝试可追踪”，因此增加专用审计表：

| 列 | SQLite 定义 | 语义 |
|---|---|---|
| `attempt_id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | 本地审计身份 |
| `job_id` | `TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE RESTRICT` | 所属 Job |
| `attempt_number` | `INTEGER NOT NULL CHECK (attempt_number > 0)` | 从 1 递增 |
| `lease_owner` | `TEXT NOT NULL` | 本次领取者 |
| `started_at` | `TEXT NOT NULL` | UTC 开始时间 |
| `lease_until` | `TEXT NOT NULL` | 本次最后租约时间 |
| `finished_at` | `TEXT` | 未完成时为空 |
| `outcome` | `TEXT` + `CHECK` | 可空；完成后为 `SUCCEEDED/RETRY_PENDING/FAILED_FINAL/LEASE_EXPIRED` |
| `error_code` | `TEXT` | 本次错误码 |
| `error_message` | `TEXT` | 本次安全化错误 |

唯一索引：`(job_id, attempt_number)`；部分唯一索引 `UNIQUE(job_id) WHERE finished_at IS NULL` 防止同一 Job 同时存在两个活动尝试。

#### `artifacts`

| 列 | SQLite 定义 | 语义 |
|---|---|---|
| `artifact_id` | `TEXT PRIMARY KEY` | 记录身份 |
| `artifact_key` | `TEXT NOT NULL UNIQUE` | 操作、范围、输入哈希和生产者版本形成的稳定键 |
| `video_id` | `TEXT REFERENCES videos(video_id) ON DELETE RESTRICT` | 可空 |
| `job_id` | `TEXT REFERENCES jobs(job_id) ON DELETE RESTRICT` | 可空 |
| `kind` | `TEXT NOT NULL` + `CHECK` | V1 产物类型 |
| `storage_root` | `TEXT NOT NULL` + `CHECK` | `DATA/VAULT` |
| `relative_path` | `TEXT NOT NULL` | 对应配置根下的安全相对路径 |
| `content_hash` | `TEXT NOT NULL` | 文件 SHA-256 |
| `provider` | `TEXT` | 可空生产者 |
| `model` | `TEXT` | 可空模型 |
| `producer_version` | `TEXT NOT NULL` | 实现/Prompt/Schema 版本 |
| `retention_class` | `TEXT NOT NULL` + `CHECK` | `EPHEMERAL_AUDIO/RAW_RESPONSE_30D/LONG_LIVED` |
| `created_at` | `TEXT NOT NULL` | UTC 创建时间 |
| `expires_at` | `TEXT` | 按保留策略可空 |
| `deleted_at` | `TEXT` | 文件清理后的审计标记 |

`kind` 固定为：`subtitle_source`、`transcript_canonical`、`audio`、`scoring_raw`、`scoring_structured`、`analysis_raw`、`analysis_structured`、`video_note`、`weekly_report`。路径写入前必须经过 ADR-002 的边界检查；数据库只保存相对路径和哈希。索引：`(video_id, kind, created_at)`、`(retention_class, expires_at, deleted_at)`。

#### `provider_calls`

| 列 | SQLite 定义 | 语义 |
|---|---|---|
| `request_hash` | `TEXT PRIMARY KEY` | 规范请求唯一键 |
| `operation` | `TEXT NOT NULL` | 调用操作 |
| `provider` | `TEXT NOT NULL` | Provider |
| `model` | `TEXT` | 可空模型 |
| `prompt_version` | `TEXT` | 可空 Prompt 版本 |
| `schema_version` | `TEXT` | 可空 Schema 版本 |
| `status` | `TEXT NOT NULL` + `CHECK` | `PENDING/SUCCEEDED/FAILED_RETRYABLE/FAILED_FINAL` |
| `reservation_owner` | `TEXT` | 活动预留者 |
| `lease_until` | `TEXT` | 预留过期时间 |
| `available_at` | `TEXT NOT NULL` | 失败后再次尝试时间 |
| `attempt_count` | `INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0)` | 调用尝试审计摘要 |
| `response_artifact_id` | `TEXT REFERENCES artifacts(artifact_id) ON DELETE RESTRICT` | 原始/结构化响应索引 |
| `input_tokens` | `INTEGER CHECK (input_tokens IS NULL OR input_tokens >= 0)` | 可空用量 |
| `output_tokens` | `INTEGER CHECK (output_tokens IS NULL OR output_tokens >= 0)` | 可空用量 |
| `cost_microusd` | `INTEGER CHECK (cost_microusd IS NULL OR cost_microusd >= 0)` | 可空成本 |
| `last_error_code` | `TEXT` | 最近错误码 |
| `last_error_message` | `TEXT` | 最近安全化错误 |
| `started_at` | `TEXT NOT NULL` | 首次预留时间 |
| `finished_at` | `TEXT` | 成功/终态失败时间 |
| `updated_at` | `TEXT NOT NULL` | UTC 更新时间 |

`request_hash` 必须由操作、规范化输入哈希、Provider、模型、Prompt 版本和 Schema 版本共同生成。`PENDING` 必须持有 owner/lease；终态清空预留字段。建立 `(status, available_at, lease_until)` 索引。

#### `reports`

| 列 | SQLite 定义 | 语义 |
|---|---|---|
| `report_id` | `TEXT PRIMARY KEY` | 稳定报告身份 |
| `timezone` | `TEXT NOT NULL` | 周期时区 |
| `iso_year` | `INTEGER NOT NULL CHECK (iso_year >= 1)` | ISO 年 |
| `iso_week` | `INTEGER NOT NULL CHECK (iso_week BETWEEN 1 AND 53)` | ISO 周 |
| `report_type` | `TEXT NOT NULL CHECK (report_type = 'weekly')` | V1 仅周报 |
| `relative_path` | `TEXT` | Vault 根下相对路径 |
| `content_hash` | `TEXT` | 可空内容哈希 |
| `status` | `TEXT NOT NULL` + `CHECK` | `PENDING/WRITTEN` |
| `created_at` | `TEXT NOT NULL` | UTC 创建时间 |
| `updated_at` | `TEXT NOT NULL` | UTC 更新时间 |

唯一索引：`UNIQUE(timezone, iso_year, iso_week, report_type)`。

### S-03：Migration、版本和打包

- 初始 migration 为 `src/youtube_intel/migrations/001_initial.sql`，通过 `importlib.resources` 从 `youtube_intel` 模块根读取。
- `schema_migrations` 是权威历史；`PRAGMA user_version` 必须镜像最新成功版本，初始化时两者不一致直接失败，不静默修复。
- 每个 migration 文件保存固定 checksum。已应用版本如名称或 checksum 改变，初始化失败；不得重写历史 SQL。
- 每个版本在 `BEGIN IMMEDIATE` 事务中全有或全无应用；失败必须 `ROLLBACK`，不得留下版本记录或半建表。
- `001_initial.sql` 位于模块根之下，按 uv build backend 的默认 wheel 规则可直接进入发行物，不修改 `pyproject.toml`。TASK-003 必须用 `uv build` 验证 sdist 和 wheel 均包含该 SQL；若事实不符，停止并申请范围扩展，不能与 TASK-004 并发修改 `pyproject.toml`。
- V1 不提供 downgrade、破坏性自动迁移或数据库清理命令。

### S-04：连接与 PRAGMA

每个 Repository 连接必须设置并验证：

```text
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
PRAGMA synchronous = NORMAL;
```

数据库初始化时设置并验证 `PRAGMA journal_mode = WAL`。不得启用 `read_uncommitted`。测试不得假设内存数据库具备多连接 WAL 语义；并发测试使用临时文件数据库。

### S-05：冻结 Repository 语义

TASK-003 对外提供具名参数/返回对象，不接收自由 `dict`。最小语义如下，具体 Python 命名可以遵循项目风格，但不得改变事务边界：

1. 初始化、查询 Schema 版本。
2. 读取频道游标；原子保存 `DiscoveryBatch`：校验当前游标与调用方的 expected cursor 一致，插入缺失候选视频，再写 `next_cursor` 并递增 `revision`。
3. upsert 完整 `VideoMetadata`；更新标题等当前元数据，但不倒退 Pipeline、不覆盖首次发现时间。
4. 标记不可用候选：只更新 `availability` 和审计信息，失败终态仍由对应 Job 记录。
5. 按 `expected_status + pipeline_version` CAS 推进 `PipelineStatus`；非法或陈旧转换不产生写入。
6. 创建、领取、续租、完成、失败、到期回收和人工重跑 Job。
7. 幂等 upsert Artifact；预留、读取、完成或失败 Provider call。
8. 按稳定周期键 upsert Report。

“发现候选 + 游标”、“Job 成功 + Artifact/Provider call 索引 + Pipeline 推进”、“迁移版本”和“周报记录”分别使用单一事务；任何一步失败全部回滚。Repository 只持久化调用方给出的重试/保留决定，不实现 Provider、编排、文件删除或退避算法。

### S-06：Job 领取、租约、恢复和时钟

- 所有变更方法显式接收 UTC `now`；生产由应用时钟提供，测试使用受控时钟。
- 领取在 `BEGIN IMMEDIATE` 中按 `(available_at, created_at, job_id)` 稳定排序，选择到期 `PENDING` Job，以 expected status 做 CAS，设置 owner/lease、递增 `attempt_count`，并插入同编号 `job_attempts`。
- 续租只允许当前 owner 对尚未过期的 `RUNNING` Job 操作，并同步更新活动 attempt 的 `lease_until`。
- 过期回收在同一事务把活动 attempt 记为 `LEASE_EXPIRED`，清空租约；仍有次数时 Job 进入 `RETRY_PENDING`，否则进入 `FAILED_FINAL`。
- 到达 `available_at` 的 `RETRY_PENDING` 必须显式转换为 `PENDING` 后才能再次领取，保持 ADR-002 状态机可审计。
- 成功或失败时同时完成活动 attempt。`attempt_count` 必须等于已创建 attempt 的最大编号。
- 人工重跑总是创建新 `job_id`；旧 Job 和 attempts 不修改。活动唯一索引仍防止同一 scope 和 Pipeline 版本存在两个未完成 Job。

### S-07：Provider call 预留与崩溃恢复

- 首个调用方通过插入 `PENDING` 记录获得 request hash 预留；并发调用方只能读取已有记录，不得重复调用。
- 只有匹配 owner 且租约有效的调用方可提交结果。可重试失败记录安全化错误和 `available_at`；终态失败不得自动重调。
- 预留过期后，接管方在调用外部 Provider 前必须先检查确定性 `artifact_key` 对应的本地产物并校验哈希；找到有效产物则直接完成缓存记录。
- 外部调用成功但进程在落库前崩溃时，SQLite 不能凭空保证 exactly-once；V1 的保证是“租约 + 确定性本地产物 + 先查缓存”的 at-most-once best effort。不得声称严格 exactly-once。
- Provider 原始正文只能存在受控文件产物，SQLite 和日志只保存路径、哈希、用量与安全化诊断。

### S-08：TASK-003 范围与验收门禁

允许实现文件：

- `src/youtube_intel/state.py`
- `src/youtube_intel/migrations/001_initial.sql`
- `tests/integration/test_state_store.py`
- `tests/unit/test_state_transitions.py`
- `handoffs/TASK-003.md`

不允许修改 `domain.py`、Provider、编排、`pyproject.toml` 或 `uv.lock`。必须覆盖：初始化/重复迁移/失败回滚、候选与游标原子性、元数据 upsert、合法/非法状态 CAS、活动 Job 唯一性、双领取竞争、续租、租约到期、最大次数、人工重跑、逐次审计、Artifact/Provider call 幂等、阶段完成故障注入和周报唯一性。默认完全离线，只使用临时 SQLite 和受控时钟。

工程门禁统一为：

```bash
uv run python -m pytest tests/integration/test_state_store.py
uv run python -m pytest tests/unit/test_state_transitions.py
uv run mypy src
uv run ruff check .
uv build
git diff --check
```

## 考虑过的替代方案

### 只保留 `jobs.attempt_count`，不建逐次审计表

实现更小，但无法证明租约过期、自动重试和最终失败各自发生在何时，也无法满足“尝试历史仍可追踪”。拒绝。

### 对全局 Job 依赖 `NULL` 唯一语义

SQLite 唯一索引允许多个 `NULL`，不能阻止重复周报或频道 Job。使用非空 `scope_key` 统一解决视频和全局任务的活动去重。

### migration SQL 写入 Python 字符串

可避免资源打包，但审查和 checksum 证据较差。SQL 放在模块根下并在构建产物中验证，更符合迁移可追踪性。

### 使用数据库当前时间

写法较短，但测试不可控，也会混入本机时间语义。拒绝；时钟由应用显式注入。

## 后果

- TASK-003 可在依赖完成并正式分配后独立实现，不需要自行发明 DDL、CAS 或恢复语义。
- TASK-004 只消费冻结的发现批次保存和元数据 upsert 语义，不触碰 SQLite 文件。
- 新增 `job_attempts` 和 `scope_key` 是对原逻辑模型的明确细化，需要产品负责人批准。
- Schema 未来变更必须新增 migration 和 ADR；不得修改已发布的 `001_initial.sql`。
- 本 ADR 不授权真实数据迁移、数据库删除、依赖安装或任何 TASK-003 实现写入。

## 执行门禁

- S-01 至 S-08 已批准；不得由实现者静默改变。
- TASK-003 当前只因 TASK-002 尚未完成而保持 `BLOCKED`。
- 主控将在 TASK-002 `DONE` 后从最新 main 基线生成独立 worktree、Implementer、Reviewer 和 Integrator 执行包。

## 研究依据

- [uv build backend：wheel 默认包含 module root 下的数据文件](https://docs.astral.sh/uv/concepts/build-backend/#file-inclusion-and-exclusion)
- SQLite 官方文档中的事务、约束和 PRAGMA 语义应作为实现时的权威来源；本 ADR 的业务约束优先于实现者临时选择。
