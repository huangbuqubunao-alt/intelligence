# YouTube Intelligence Agent V1 产品决策提案

- 状态：`ACCEPTED`
- 提案日期：2026-07-14
- 批准日期：2026-07-14
- 决策人：用户（产品负责人）
- 对应任务：`TASK-000`

## 批准记录

产品负责人在主控对话中明确回复：

```text
批准 DEC-01 至 DEC-10 的推荐方案。
```

批准范围为本文档 DEC-01 至 DEC-10 的全部推荐决定。批准只确定 V1 方向；真实密钥、云调用、依赖安装、Schema 变更、真实 Vault 和 launchd 操作仍须遵守任务卡中的具体审批门禁。

## 后续架构与任务级批准

### ADR-008/ADR-009：云分析与 Obsidian 笔记契约

- 批准日期：2026-07-20
- 批准范围：ADR-008 A-01 至 A-15、ADR-009 N-01 至 N-15；先顺序完成
  `TASK-008A -> TASK-009A`，再从同一最新 main 并行实现 TASK-008/TASK-009。
- TASK-008A 依赖授权：`openai>=2.46.0,<2.47`、
  `tiktoken>=0.13.0,<0.14`、必要传递依赖、网络包下载、
  `pyproject.toml`/`uv.lock` 修改和任务卡离线 uv 验证/构建。
- TASK-009A 依赖授权：`Jinja2>=3.1.6,<3.2`、必要传递依赖、网络包下载、
  `pyproject.toml`/`uv.lock` 修改和任务卡离线 uv 验证/构建。
- 依赖动作只可在后续固定 base/worktree/角色/文件范围的共享任务分配包内执行；
  TASK-008A 先进入 `READY/UNASSIGNED`，TASK-009A 等待其 `DONE`。
- 2026-07-20 TASK-008A 正式分配：从
  `main@82d1fd7c7f2f82e77df0518e63755bad0bf240f2` 创建
  `/Users/hua/Documents/yia-worktrees/task-008a`，分支
  `codex/task-008a-cloud-analysis-shared-contracts`；Codex 为唯一 Implementer，
  完成后由全新独立 Codex Reviewer 审查。完整产品 Diff 只允许任务卡列出的 7 个
  路径。
- TASK-008A 可在该固定 worktree 内解析、下载、锁定并安装已批准的 OpenAI SDK、
  tiktoken 和必要传递依赖，执行任务卡离线门禁；不得实现 Provider、读取密钥、
  调用 API 或修改 Schema、migration、`state.py`、`complete_stage`。
- 继续未授权：真实 OpenAI API、环境变量值/密钥、付费调用、云端 token-count、
  真实 Vault/用户笔记、最终文件删除/移动/重命名及其他真实资源路径。
- 原始决定见 `docs/decisions/ADR-008-cloud-analysis-contract.md` 和
  `docs/decisions/ADR-009-obsidian-note-contract.md`。

### ADR-007：本地模型共享契约与分阶段门禁

- 批准日期：2026-07-17
- 批准范围：ADR-007 L-01 至 L-15，包括 `TASK-005A` 共享切片、评分建议与最终
  决定分离、评分摘要原子写入、三段采样、Ollama loopback HTTP、固定模型
  digest、Whisper 参数/模型 revision、音频 Artifact 清理与资源门禁。
- 执行顺序：先建立并完成 `TASK-005A`，再从其 `DONE` main commit 为 TASK-006 和
  TASK-007 创建同一基线的独立 worktree；两项在此之前继续 `BLOCKED`。
- 明确未授权：`mlx-whisper` 解析/锁定/安装、Whisper 权重下载、ffmpeg 安装或调用、
  Ollama 安装/启动、`qwen3:8b` 拉取、任何真实模型/媒体/YouTube 冒烟、Cookie/登录、
  remote components、真实 Vault/密钥。上述每项仍须当次任务级批准。
- `TASK-005A` 不新增 Schema/migration 或依赖；它只冻结共享配置、领域对象与现有
  SQLite 完成/Artifact 索引语义。正式实施的 worktree、角色和命令授权另行记录。
- 2026-07-17 TASK-005A 实施授权：从 `main@82f45a1c04f9eba3264cd743b28bc339d79b34fc`
  创建 `/Users/hua/Documents/yia-worktrees/task-005a` 与
  `codex/task-005a-local-model-shared-contracts`；Codex 为唯一 Implementer，完成后由
  全新独立 Codex Reviewer 审查。只允许任务卡列出的 8 个文件；允许既有锁定依赖的
  `uv sync --locked`（仅缓存缺失包下载）及任务卡离线验证/构建命令。
- 2026-07-19 TASK-006 阶段 A 与 TASK-007 离线实施授权：两项从共同
  `main@6b4d59c882ccdcbd0e5a6069a6661e0672921a80` 分别创建独立 Codex worktree。
  TASK-006 允许 `mlx-whisper>=0.4.3,<0.5`、必要传递依赖、网络包下载、
  `pyproject.toml`/`uv.lock` 修改及任务卡离线验证；TASK-007 只允许任务卡列出的
  离线代码/夹具/测试，不修改依赖或锁文件。两项均由 Codex Implementer 完成后交全新
  独立 Codex Reviewer 审查。
- 此次授权明确不包含 Whisper 模型下载/加载、ffmpeg、媒体或 YouTube 下载、真实转写
  冒烟、Ollama 安装/启动、`qwen3:8b` 拉取、真实模型调用、Cookie/登录、remote
  components、真实 Vault/密钥或文件删除。任何一项仍须单独任务级批准。
- 原始决定见 `docs/decisions/ADR-007-local-model-pipeline-contracts.md`。

### ADR-006：字幕获取、规范化与缓存契约

- 批准日期：2026-07-15
- 批准范围：ADR-006 T-01 至 T-15，包括人工/自动全局排序、语言匹配、JSON3/VTT/SRT、具名结果联合、领域对象扩展、规范化/质量阈值、分层幂等键、原子文件恢复、错误映射、yt-dlp/标准库复用和显式 refresh。
- 明确约束：TASK-005 不新增 Schema/migration，不修改 `state.py` 或 `complete_stage`；使用现有 `SUBTITLE_SOURCE` / `TRANSCRIPT_CANONICAL`、Provider-call、稳定 key/path、文件哈希验证和空 Artifact stage completion。
- 2026-07-16 TASK-005 实施授权：从 `main@b28f52d0e4950f78dba315d4afe211ea5f75b93c` 创建 `/Users/hua/Documents/yia-worktrees/task-005` 与 `codex/task-005-subtitle-pipeline`；Codex 为 Implementer，完成后由全新独立 Codex 会话 Review。实现只可修改 `domain.py`、`transcripts.py`、`providers/subtitles.py`、三份既定测试、`tests/fixtures/subtitles/**` 与 `handoffs/TASK-005.md`。
- 命令/依赖授权：不新增或升级依赖，不修改 `state.py`、migration、`complete_stage`、`pyproject.toml` 或 `uv.lock`；允许已有锁定依赖的 `uv sync --locked`（缓存缺失时仅允许包下载）及任务卡的离线 `uv` 验证/构建命令。
- 继续未授权：真实 YouTube/字幕、Cookie、登录、remote components、ffmpeg、媒体下载、真实 Vault/密钥。
- 原始批准文本见 `docs/decisions/ADR-006-subtitle-acquisition-contract.md`。

## 决策摘要

| ID | 推荐方案 | 主要理由 |
|---|---|---|
| DEC-01 | RSS 增量发现 + yt-dlp 元数据/字幕 | 无 YouTube API Key，MVP 依赖少 |
| DEC-02 | uv + `pyproject.toml` + `uv.lock`，批准最小包白名单 | 环境可复现，限制依赖扩张 |
| DEC-03 | MLX Whisper + large-v3-turbo，模型可配 | 针对 Apple Silicon 的本地路径 |
| DEC-04 | 云分析默认关闭；V1 首个 Adapter 为 OpenAI | 控制范围和成本，保留 Provider 扩展 |
| DEC-05 | 默认最长 180 分钟，超限元数据终止，可手动强制 | 控制转写资源和异常长任务 |
| DEC-06 | 仅高分且显式开启才上云，单次最多 5 条、每条最多 30k 输入 token | 控制隐私与成本 |
| DEC-07 | 成功音频立即删；文本长期保留；原始模型响应/日志保留 30 天 | 平衡恢复、知识留存和磁盘 |
| DEC-08 | 低价值只存 SQLite/产物索引，不写 Obsidian；空周报照常生成 | 遵循原始流程并避免 Vault 噪声 |
| DEC-09 | 深度总结阈值 7.0；周报 Top 10 | 与 V1.0 建议一致且可配置 |
| DEC-10 | 5 个离线固定场景 + OpenAI 官方频道真实冒烟；YC 为备用 | 验收可复现，同时保留真实链路证据 |

## DEC-01：频道发现方式

### 推荐决定

- 使用 YouTube 频道 RSS 做增量候选发现。
- 使用 yt-dlp 获取标准化元数据、字幕清单和必要媒体。
- 频道 ID 由用户在 `channels.yaml` 人工维护。
- 不使用 YouTube Data API，不读取账户订阅，不要求登录态。

### 取舍

- 优点：无需 API Key 和配额管理，符合本地单用户 MVP。
- 代价：RSS 只适合增量发现，历史回填、删除/私有状态仍需 yt-dlp 补充。

### 影响

- 解锁 `TASK-004`。
- 后续若改用 Data API，需新增 ADR，不改变 SourceProvider 契约。
- 产品负责人已于 2026-07-14 批准 ADR-004 D-01 至 D-08：候选与游标先原子落库，元数据按视频独立处理，TASK-004 只公开字幕语言摘要，TASK-005 重查轨道明细。

## DEC-02：Python 工程与依赖边界

### 推荐决定

- 使用 Python 3.12。
- 使用 uv 管理环境、依赖与锁定。
- `pyproject.toml` 为项目清单，`uv.lock` 提交版本库。
- V1 允许的运行时依赖白名单：`pydantic`、`PyYAML`、`yt-dlp`、`mlx-whisper`、
  `httpx`、`openai`、`tiktoken`、`Jinja2`。
- V1 允许的开发依赖白名单：`pytest`、`pytest-cov`、`ruff`、`mypy` 及已使用依赖所需的最小类型包。
- SQLite、CLI、日志、时间、文件和调度优先使用 Python 标准库。
- 具体兼容版本由 `TASK-001` 验证并锁定；新增白名单外包必须返回产品/技术审批。

### 取舍

- 优点：统一安装和锁文件，限制 Agent 随意引入替代库。
- 代价：各运行时依赖在首次引入它的任务中验证 Python 兼容性；`TASK-001` 只验证纯 Python 工程、build backend 和开发工具链。

### 影响

- 批准此项是批准依赖范围，不代表现在执行安装。
- 产品负责人已于 2026-07-14 对 `TASK-001` 的具体版本范围、必要传递依赖、文件范围、uv 命令和网络下载单独授权，解锁其安装步骤。
- 产品负责人已于 2026-07-14 对 `TASK-002` 单独授权 `pydantic>=2.13.4,<2.14`、`PyYAML>=6.0.3,<7`、必要传递依赖、网络下载、`pyproject.toml`/`uv.lock` 写入和任务卡中的 uv 验证命令。Pydantic 使用窄次版本范围，避免公共契约在未复核时自动跨入 2.14；PyYAML 只允许 6.x，并要求使用安全加载接口。
- 产品负责人已于 2026-07-14 对 `TASK-004` 单独授权 `yt-dlp[default,deno]>=2026.7.4,<2026.8`、必要传递依赖、网络下载、`pyproject.toml`/`uv.lock` 写入以及 ADR-004 所列 uv 命令；真实 YouTube 冒烟、Cookie、账号登录、remote components 和 ffmpeg 仍未授权。
- 产品负责人已于 2026-07-20 对 TASK-008A 单独授权
  `openai>=2.46.0,<2.47`、`tiktoken>=0.13.0,<0.14`，对 TASK-009A 单独授权
  `Jinja2>=3.1.6,<3.2`；两项均允许必要传递依赖、网络包下载、
  `pyproject.toml`/`uv.lock` 修改和各任务卡离线 uv 门禁。真实云调用/密钥与真实
  Vault 不包含在依赖授权中。

## DEC-03：本地 Whisper 实现

### 推荐决定

- 首选 `mlx-whisper`，默认模型 `mlx-community/whisper-large-v3-turbo`。
- 模型名、语言提示和设备参数必须可配置。
- 缓存键包含音频哈希、Provider、模型和参数版本。
- `TASK-006` 先用短音频做 Apple Silicon 冒烟；如安装、准确度或资源不达标，停止并提交替代方案 ADR，不静默换库。

### 取舍

- 优点：与目标运行平台一致，默认模型在速度与质量之间取中间值。
- 代价：首次模型下载体积较大，模型生态和包兼容性需要真实本机验证。

### 影响

- 解锁 `TASK-006` 的技术路线。
- 真实模型下载仍在任务执行时单独确认。

## DEC-04：云端深度分析 Provider

### 推荐决定

- 云端分析默认关闭。
- V1 只实现一个正式云 Adapter：OpenAI。
- 具体模型不得硬编码，必须由配置指定并在启动时校验。
- 保留 SummaryProvider 接口；Anthropic Adapter 不进入 V1，除非单独新增任务和依赖审批。
- 无 API Key 时本地流程应正常完成，不得把云端能力作为启动必需项。

### 取舍

- 优点：减少 SDK、契约和集成测试范围，仍保留未来替换空间。
- 代价：V1 不能在运行时直接切换到 Claude；这部分延期而不是删除架构能力。

### 影响

- 解锁 `TASK-008` 的 Provider 范围。
- 批准此项不授权任何真实付费调用或写入 API Key。
- ADR-008 进一步冻结官方 Responses/Structured Outputs、
  `store=False`/`max_retries=0`、一次推理调用、结构化跳过和延迟凭据读取。

## DEC-05：视频最大时长

### 推荐决定

- 默认最大处理时长为 180 分钟。
- 超限视频保存元数据和 `SKIPPED_DURATION_LIMIT` 终态，不下载音频、不转写、不上云。
- 手动单视频命令可通过显式 `--force` 覆盖时长限制，并在日志和状态中记录。
- 已有可用字幕的视频仍遵守 180 分钟上限，避免超长模型输入；是否放宽由后续数据决定。

### 取舍

- 优点：资源和运行时间可预测。
- 代价：超长播客默认不会进入知识库，需要人工选择。

### 影响

- `TASK-006` 与 `TASK-010` 必须覆盖默认跳过和强制路径。

## DEC-06：云端发送范围和预算

### 推荐决定

只有同时满足以下条件才发送云请求：

1. 云端分析显式启用。
2. 本地最终分数不低于配置阈值。
3. 本次运行成功通过预算和隐私预检。
4. 输入来自公开视频元数据和规范字幕，不包含用户 Obsidian 内容。

默认限制：

- `max_cloud_calls_per_run: 5`
- `max_cloud_input_tokens_per_video: 30000`
- 本地 `tiktoken` 发送上限为 28,000 tokens，为 Provider framing 保留 2,000；
  使用固定 head/body/tail 采样，不在 V1 做多轮 Map-Reduce。
- V1 不调用云端 token-count endpoint；它本身会发送内容并消耗调用/隐私预算。
- 周报趋势默认使用已有分析和本地模型，不产生额外云调用。

### 取舍

- 优点：成本上限明确，云端关闭时可完整运行本地链路。
- 代价：超长视频可能因采样遗漏局部内容。

### 影响

- TASK-008A 先冻结最小化 payload、采样/预算和结构化完成/跳过结果；TASK-008 需要
  零调用、一次推理、证据 grounding 和事务恢复测试。

## DEC-07：缓存与保留期

### 推荐决定

- 成功转写后立即删除下载音频。
- 失败/中断音频最多保留 7 天，后续运行执行过期清理。
- 原始字幕和规范文本长期保留，直到用户手动清理。
- 结构化评分、结构化分析和请求哈希长期保留，保证幂等和知识可追溯。
- Provider 原始自由文本响应保留 30 天；到期只删除原文，保留结构化结果和哈希。
- 结构化日志保留 30 天。
- 自动清理只能处理本项目 `data/`、`logs/` 下已登记产物，不触碰 Vault 笔记。

### 取舍

- 优点：保留可复用知识产物，控制音频、日志和原始响应占用。
- 代价：需要安全的过期清理逻辑和清理测试。

### 影响

- `TASK-003` 记录保留元数据；`TASK-006` 处理音频；`TASK-012` 处理日志清理。

## DEC-08：低价值内容与空周报

### 推荐决定

- `score < threshold` 的视频只保留 SQLite 元数据、评分和必要产物索引。
- 低价值视频不写 Obsidian 视频笔记，不进入周报 Top N。
- 周内没有符合条件的视频时仍生成该周文件，明确写“本周无高价值新增”，保留运行统计。
- 用户可通过未来任务增加“手动提升/强制生成笔记”，不进入 V1。

### 取舍

- 优点：遵循 V1.0 的“低价值仅保存元数据”，避免 Vault 被低价值内容淹没。
- 代价：低价值视频不能直接从 Obsidian 搜索，只能从状态数据追溯。

### 影响

- 修改当前 PRD 中“低价值简版笔记”的建议，批准后需同步 PRD。
- `TASK-009` 只为高价值路径写视频笔记；`TASK-011` 覆盖空周。

## DEC-09：评分阈值与周报数量

### 推荐决定

- 默认深度总结阈值：`7.0`。
- 默认周报 Top N：`10`。
- 两者可配置，但必须在启动时校验：阈值 0–10，Top N 为 1–100 的整数。
- 应用层以实际分数与阈值决定是否总结；模型返回的 `should_summarize` 只作诊断建议。

### 取舍

- 优点：简单可解释，与原始设计一致。
- 代价：初期阈值未经真实数据校准，需要在 MVP 运行后复盘。

### 影响

- `TASK-007` 和 `TASK-011` 按此实现并测试边界值。

## DEC-10：真实验收频道与样例

### 推荐决定

- 默认端到端测试使用 5 个完全离线固定场景：人工字幕、自动字幕、Whisper、低分、高分。
- 真实网络冒烟的首选频道为 OpenAI 官方 YouTube 频道，只处理最新 2 个已结束公开视频。
- Y Combinator 官方频道作为备用，只有首选频道无法覆盖或不可访问时使用。
- 执行 TASK-013 时把实际频道 ID、视频 ID、运行日期和结果写入验收报告，保证证据可追溯。
- 真实云端总结和真实 Vault 写入仍分别需要当次明确授权；默认真实冒烟只做到临时 Vault。

### 取舍

- 优点：离线测试稳定，真实冒烟范围和外部影响很小。
- 代价：最新视频内容随时间变化，因此真实冒烟是环境证明，不是稳定回归测试。

### 影响

- 解锁 `TASK-013` 的样例选择；执行仍依赖前序任务完成。

## 批准同步清单

- [x] 本文档状态改为 `ACCEPTED`，记录批准日期与原话。
- [x] `docs/PRD.md` 状态改为 `APPROVED` 并把 DEC 表更新为确定值。
- [x] `docs/SYSTEM_DESIGN.md` 同步依赖、Provider、时长、预算和保留策略。
- [x] `docs/IMPLEMENTATION_ROADMAP.md` 状态改为已审批。
- [x] `tasks/TASK-000-product-decisions.md` 进入主控验收。
- [x] 规划基线已以 `c0f1f553db52b1cb4eb354e5c689c2abc5556223` 进入 Git 主线，`TASK-000` 设为 `DONE`。
- [x] `TASK-001` 已获得本次依赖安装、锁文件和工具链写入授权并设为 `READY`；其他任务继续按依赖保持 `BLOCKED`。
