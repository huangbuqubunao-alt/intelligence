# YouTube Intelligence Agent 产品需求文档

- 版本：V1.1（2026-09-04 Local Product Workspace amendment）
- 日期：2026-07-14
- 文档负责人：产品/项目经理
- 依据：用户提供的 V1.0 PRD + Technical Design
- 状态：`APPROVED`

## 1. 文档定位

本文档将 V1.0 的产品方向补充为可验收规格。V1.0 中“自动发现值得学习的内容，并形成可检索知识库”的目标保持不变；新增内容主要用于消除开发 Agent 在边界、状态、失败恢复、隐私和验收上的歧义。

本文档已由产品负责人批准。开发 Agent 仍必须等待对应任务进入 `READY` 并获得任务级红线审批，不能仅凭 PRD 批准自行开工。

## 2. 产品目标

为单个产品经理构建本地优先的 YouTube 知识采集 Agent，自动完成：

1. 检查人工维护的频道是否发布新视频。
2. 获取视频元数据和最优可用字幕；无可用字幕时本地转写。
3. 使用本地模型进行价值评分。
4. 仅对达到阈值的内容调用已启用的云端模型做深度分析。
5. 将视频笔记写入 Obsidian，并按周生成趋势汇总。
6. 在重复执行、进程中断和外部服务失败时保持可恢复、可追踪、不重复产出。

## 3. MVP 范围

### 3.1 必须包含

- 人工维护频道清单，可启用、停用并配置优先级。
- 每日、每周和手动三种运行入口。
- 新视频发现、元数据获取和去重。
- 字幕优先级：人工字幕 > 自动字幕 > 本地 Whisper 转写。
- Ollama 本地评分，输出结构化结果。
- 可选的 OpenAI 云端深度总结，默认关闭；模型可配置，Provider 接口保留扩展能力。
- Obsidian Markdown 视频笔记和 ISO 周报。
- SQLite 状态、幂等、重试、断点恢复和结构化日志。
- 单元测试、集成测试、端到端固定样例和本地初始化说明。

### 3.2 明确不包含

- 自动读取 YouTube 账号订阅。
- 多用户、账号体系、权限系统。
- 远程数据库、后台管理系统或云端常驻服务。
- V2 数据源：GitHub、Hacker News、Product Hunt、arXiv、Reddit、X、RSS。
- 自动发布、评论、点赞或修改 YouTube 上的任何内容。

### 3.3 已批准的本地产品工作台（2026-09-04 amendment）

产品已演进为本地优先、可配置、可自动运行的 YouTube Intelligence
工作台。以下现有本地工作台表面属于批准范围：Dashboard、Sources、Source
Detail Drawer、Videos、Video Detail、Weekly、Automation、Activity 和 Settings。
前端仅通过受控的本地 application-service/API 边界消费既有 authoritative
runtime/read models；它不获得新的 authority。

因此，GUI/Web 页面不再作为整体排除项，但本 amendment 不授权：

- direct DB authority bypass、provider SDK bypass、credential bypass、scoring
  trust bypass、Note authority bypass、Weekly authority bypass 或 Deep Analysis
  gate bypass；
- public SaaS/web hosting、multi-user accounts、remote cloud dashboard、public
  deployment、mobile app、credential management UI、arbitrary provider execution
  或 unqualified provider use；
- TASK-016G、new Note authority、new Weekly V2 authority、public release 或
  package publication。

下列真实产品状态必须如实呈现，而不是由 GUI 推断或修复：没有 persisted
authoritative NoteRef association 时 Note V1 为 `UNAVAILABLE`；Note V2 为
`UNAVAILABLE`；当前 authority 无法证明时 Weekly version 为 `UNKNOWN`；Weekly
V2 为 `UNAVAILABLE`；Weekly video linkage 为
`UNAVAILABLE_IN_CURRENT_AUTHORITY`；未同时具备 qualified live provider 与 PO
acceptance 时 Deep Analysis 为 `BLOCKED`。

## 4. 目标用户与运行环境

- 用户：一名产品经理，同时是本机操作者和 Obsidian Vault 所有者。
- 平台：macOS Apple Silicon。
- Python：3.12 或更高版本；具体上限由依赖兼容性决定。
- 时区：默认 `Asia/Shanghai`，可配置。
- 输出语言：默认中文；保留视频原始语言、原文专有名词和可追溯引用。
- 网络：发现和下载需要联网；评分应可本地运行；云端总结可关闭。

## 5. 核心用户流程

1. 用户在 `config/channels.yaml` 维护频道。
2. 调度器或用户启动一次检查。
3. 系统发现新视频并记录，不重复创建已有 `video_id`。
4. 系统获取元数据和可用字幕；必要时下载音频并本地转写。
5. 本地模型返回评分、理由、主题和是否建议深度总结。
6. 低价值视频只保存 SQLite 元数据、评分和必要产物索引，不写 Obsidian 视频笔记。
7. 高价值视频调用已启用的云端 Provider，生成结构化洞察。
8. 系统以原子写入方式创建或更新 Obsidian 视频笔记。
9. 每周任务聚合本周已完成内容，生成或幂等更新周报。

## 6. 功能需求

| ID | 优先级 | 需求 | 可验收结果 |
|---|---|---|---|
| FR-01 | P0 | 加载和校验配置 | 缺失必填字段或非法阈值时，运行在处理视频前失败并给出字段级错误 |
| FR-02 | P0 | 发现频道新视频 | 连续运行两次时，同一 `video_id` 只保留一条记录 |
| FR-03 | P0 | 获取元数据 | 至少记录标题、频道、发布时间、时长、URL、语言和直播状态 |
| FR-04 | P0 | 获取最佳字幕 | 按人工、自动、本地转写的顺序选择，并记录来源与语言 |
| FR-05 | P0 | 本地评分 | 返回通过 Schema 校验的分数、理由、主题和 `should_summarize` |
| FR-06 | P0 | 云端深度分析 | 仅在开关开启且满足阈值时调用；结果符合固定结构并可缓存 |
| FR-07 | P0 | 写入高价值视频笔记 | 文件名安全、Frontmatter 有效、重复执行不生成重复文件 |
| FR-08 | P0 | 状态与恢复 | 任一步失败后可从最近成功阶段恢复，不重复执行已缓存的昂贵步骤 |
| FR-09 | P0 | 重试与终态 | 可重试错误指数退避，达到上限后进入人工可见终态 |
| FR-10 | P0 | 周报 | 同一 ISO 周重复执行时更新同一文件，并正确链接视频笔记 |
| FR-11 | P1 | 可观测性 | 每次运行有 `run_id`，日志可按视频和阶段定位成功、失败与耗时 |
| FR-12 | P1 | 手动控制 | 支持全量检查、单频道检查、单视频重跑、仅周报和失败任务重试 |

## 7. 内容与输出契约

### 7.1 评分结果

评分范围为 `0.0` 到 `10.0`，至少包含：

- `score`
- `reason`
- `topics`
- `should_summarize`
- 各评分维度的可选子分：技术、商业、产品、原创性、实操、行业影响

若模型输出无法通过 Schema 校验，系统最多做一次格式修复；仍失败则按可重试错误处理，不得凭空补值。

### 7.2 深度分析结果

至少包含：

- 一句话总结
- 核心观点
- 关键事实
- 产品机会
- 商业机会
- 可落地方向
- 值得验证的假设
- 行动建议
- 风险
- 关键词
- 引用案例或带时间信息的证据（输入可支持时）

事实、推断和建议应在表述上可区分；无法从文本确认的信息不得写成事实。

### 7.3 Obsidian 视频笔记

Frontmatter 至少包含：

- `type`
- `video_id`
- `title`
- `channel`
- `published`
- `source`
- `language`
- `transcript_source`
- `score`
- `topics`
- `processed_at`
- `pipeline_version`

正文至少包含 V1.0 定义的总结、观点、机会、建议和标签。`我的思考` 保留为用户编辑区，系统更新笔记时不得覆盖用户已有内容。

### 7.4 周报

- 路径默认为 `Weekly/YYYY-Www.md`。
- 汇总周期使用配置时区的 ISO 周。
- 包含本周新增数、Top N、评分、一句话总结、推荐原因、双链、趋势、重复关键词和值得持续关注方向。
- Top N 默认 10；不足 10 条时展示全部。

## 8. 边界与特殊情况

| 情况 | V1 默认行为 |
|---|---|
| 正在直播、预约或首映未结束 | 记录并延后，不下载或分析 |
| 已结束直播 | 按普通公开视频处理 |
| Shorts | 按普通视频处理，不以时长自动过滤 |
| 私有、删除、地区限制且不可访问 | 记录不可用终态和原因，不无限重试 |
| 字幕为空或明显损坏 | 视为无字幕，进入本地转写 |
| 多语言字幕 | 按配置语言偏好选择并记录最终语言 |
| 视频标题后来修改 | 更新元数据；笔记文件身份仍以 `video_id` 为准 |
| 超长视频 | 默认上限 180 分钟；超限保存元数据并进入 `SKIPPED_DURATION_LIMIT`，手动 `--force` 可覆盖 |
| Obsidian 内同名标题 | 文件名必须包含稳定的 `video_id` 或等价唯一后缀 |
| 周内无高价值视频 | 仍生成周报，明确记录“本周无高价值新增”和运行统计 |

## 9. 非功能需求

### 9.1 可靠性

- SQLite 和文件写入不得留下业务上可见的半成品。
- 同一阶段使用稳定输入哈希缓存结果。
- 进程异常退出后，下次运行可回收过期任务租约并继续。
- 单个视频失败不得阻断其他视频。

### 9.2 性能与成本

- 默认串行或低并发，避免触发 YouTube、Ollama 和云端服务限制。
- 云端调用必须受开关、阈值和可选单次运行预算控制。
- 日志记录调用次数、模型、耗时和可获得的 token 用量；不得记录密钥。

### 9.3 隐私与安全

- API 密钥只从环境变量或系统密钥存储读取，不进入 YAML、日志、测试夹具或版本库。
- 云端总结关闭时，字幕不得发送到云端。
- 写入路径必须规范化并验证位于配置的 Vault 子目录内，防止目录穿越。
- 日志中的字幕和 Provider 原始响应默认只记录路径/哈希，不记录全文。

### 9.4 可维护性

- 外部能力通过 Provider 接口隔离。
- 配置、Prompt 和 Markdown 模板外置。
- 核心编排不依赖具体 YouTube/LLM/Obsidian 实现。
- V2 新数据源应通过新增 Source Provider 接入，不修改核心状态机语义。

## 10. MVP 验收标准

使用固定测试样例和一个经人工批准的真实频道完成以下验收：

1. 能发现并处理至少 5 个样例：人工字幕、自动字幕、无字幕、低分、高分各至少 1 个。
2. 同一批次连续运行两次，数据库视频记录、云端调用缓存、视频笔记和周报均无重复。
3. 在字幕、转写、评分、云端总结和 Obsidian 写入阶段分别注入一次失败，均可观察、重试或进入明确终态。
4. 云端总结关闭时，端到端流程仍能完成到本地评分和约定的低价值产物。
5. 重新启动进程后可继续未完成任务，已成功的昂贵步骤不重复执行。
6. 所有单元、集成和端到端测试通过；类型检查、Lint 和构建/安装检查通过。
7. 仓库扫描不包含真实密钥，日志不包含字幕全文或 Provider 凭证。
8. Obsidian 视频笔记 Frontmatter 可解析、双链有效，更新时保留 `我的思考`。

## 11. 目标项目结构

```text
config/                  用户配置示例
docs/                    PRD、系统设计、路线图和运维说明
prompts/                 评分、总结、周报 Prompt
src/youtube_intel/       应用代码
src/youtube_intel/providers/ 外部 Provider 适配器
templates/               Obsidian Markdown 模板
data/                    运行状态、缓存和转写；默认不入库
logs/                    运行日志；默认不入库
tests/unit/              纯逻辑和单模块测试
tests/integration/       SQLite、文件和 Provider 契约测试
tests/e2e/               固定夹具端到端测试
tasks/                   可领取任务卡和状态索引
```

## 12. 目标工程命令

以下命令应由脚手架任务建立；在此之前只是验收契约：

```bash
uv sync
uv run python -m youtube_intel --help
uv run pytest
uv run ruff check .
uv run mypy src
```

uv、依赖白名单和锁文件方向已在 `TASK-000` 批准；实际安装、版本锁定和工具链文件仍须由 `TASK-001` 在明确分配后落地并保留兼容性证据。

## 13. 测试策略

- 单元测试：配置校验、状态转换、评分解析、文件名、周计算和模板渲染。
- Provider 契约测试：对每个接口复用同一组行为测试。
- 集成测试：临时 SQLite、临时 Vault、缓存、任务租约和失败恢复。
- 端到端测试：默认完全离线，使用录制/伪造响应与短音频夹具；真实网络测试单独标记且不进入默认测试。
- 回归原则：不得删除、跳过或弱化失败测试来通过门禁。

## 14. 项目边界

### 必须始终做到

- 每项实现关联一个 `tasks/TASK-*.md`。
- 先测试或明确验收，再实现，再检查 Diff。
- 配置、模型输出和外部数据均视为不可信输入并验证。
- Schema、Prompt 和输出模板变更必须更新版本或迁移策略。

### 必须先询问

- 新增或升级依赖、修改锁文件或工具链。
- 修改数据库 Schema 或迁移策略。
- 修改云端数据发送范围、成本上限或隐私策略。
- 修改 MVP 范围、验收标准、调度方式或 Vault 目录结构。

### 绝对禁止

- 提交密钥、真实 token、私人字幕全文或个人 Vault 内容。
- 为通过检查而删除测试、跳过测试或降低覆盖标准。
- 在未审批时自动写入用户真实 Vault 或注册 launchd 服务。
- 实现 V2 数据源或 GUI 等范围外功能。

## 15. 已批准决策

完整决定、取舍和批准记录见 `docs/PRODUCT_DECISIONS.md`。下表是 V1 实现约束；涉及真实密钥、付费调用、依赖安装、Schema、真实 Vault 或 launchd 时仍需任务级具体授权。

| ID | 已批准决定 | 落地任务 |
|---|---|---|
| DEC-01 | RSS 增量发现，yt-dlp 补元数据/字幕，不使用 Data API 或登录态 | TASK-004 |
| DEC-02 | Python 3.12；uv + `pyproject.toml` + `uv.lock`；仅允许已批准依赖白名单 | TASK-001 |
| DEC-03 | `mlx-whisper`，默认 `mlx-community/whisper-large-v3-turbo`，模型可配 | TASK-006 |
| DEC-04 | 云分析默认关闭；V1 仅实现 OpenAI Adapter，模型不硬编码 | TASK-008 |
| DEC-05 | 默认最长 180 分钟；超限元数据终止，可显式 `--force` | TASK-006/010 |
| DEC-06 | 仅高分且显式开启才上云；每次最多 5 条，每条最多 30k 输入 token | TASK-007/008 |
| DEC-07 | 成功音频立即删除；失败音频 7 天；文本长期；原始响应/日志 30 天 | TASK-003/006/012 |
| DEC-08 | 低价值只存 SQLite/产物索引，不写 Obsidian；空周报照常生成 | TASK-009/011 |
| DEC-09 | 总结阈值 7.0，周报 Top 10，均可配置并校验 | TASK-007/011 |
| DEC-10 | 5 个离线场景；OpenAI 官方频道最新 2 条真实冒烟，YC 备用 | TASK-013 |
| DEC-11 | Cloud OFF 不等于 Analysis OFF；Local/Hybrid/Cloud 均先本地评分，高价值视频使用统一 Knowledge V2；Local-only-first 前置门禁已由 ADR-027 / TASK-016 Correction R1 对 Deep Analysis 全局 supersede | TASK-016；ADR-023；ADR-027 |

## 16. 变更规则

- `TASK-000` 记录以上决策及审批人、日期和理由。
- 改变用户价值、MVP 边界或验收结果时，先更新本文档。
- 改变接口、Schema、状态机或异常语义时，先更新 `docs/SYSTEM_DESIGN.md`。
- 改变任务顺序、负责人角色或并行关系时，更新 `docs/IMPLEMENTATION_ROADMAP.md` 和 `tasks/README.md`。

## 17. TASK-016 Intelligence Output 扩展

- `local-only`、`hybrid`、`cloud` 均先本地快速评分；低价值视频不执行昂贵分析。
- Cloud 仅是显式、隐私受限的可选 Provider；Local 模式保留，但 Local-only 不再是
  Deep Analysis 交付的全局前置条件（ADR-027 / TASK-016 Correction R1）。
- Hybrid 为推荐模式，但新安装与升级不得自动启用外发或付费调用。
- 所有用户可见 AI 叙述遵守 `general.output_language`；默认 `zh-CN`。
- Local/Cloud 共享 Knowledge V2；无可靠机会时明确表达不足，禁止为了填字段而幻觉。
- Weekly V2 使用 `VerifiedNoteV2Artifact` 中已验证 Structured Knowledge 和
  artifact-bound metadata 做跨视频综合；普通 `NoteV2` 不是 authority，且不默认发送全文 Transcript。
- Historical Local-only-first sequencing is superseded globally for Deep
  Analysis by the provider-neutral P0--P7 gate in ADR-027 / TASK-016
  Correction R1; no provider implementation is thereby authorized.
