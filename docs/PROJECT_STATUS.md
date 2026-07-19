# YouTube Intelligence Agent 项目状态

- 更新时间：2026-07-18
- 当前阶段：Phase 2 — TASK-006 阶段 A 与 TASK-007 离线实现并行进行；真实本地模型资源保持分阶段门禁
- 主控状态：ACTIVE
- 规划基线 commit：`c0f1f553db52b1cb4eb354e5c689c2abc5556223`
- 实现任务基线：分配时取最新已验收的 `main` commit，并写入任务包
- 活动 worktree：`/Users/hua/Documents/yia-worktrees/task-006`（`codex/task-006-local-transcription`）与 `/Users/hua/Documents/yia-worktrees/task-007`（`codex/task-007-local-scoring`）；TASK-005/TASK-005A worktree 保留为审计证据，不是当前写入目标
- 活动任务：`TASK-006` 第一轮审查发现 Artifact 清理 P1，已退回原 Codex Implementer
  Correction 1；`TASK-007` 离线评分正由隔离的独立 Codex Reviewer 审查
- TASK-007 第一轮独立审查现已结束并发现 Ollama 异常脱敏与 SQLite 原子完成两个 P1；
  原 Codex Implementer 正在执行 Correction 1。
- Agent 资源策略：Grok 当前不可用；所有新分配的 Implementer、Reviewer、Integrator 和 Scout 均使用 Codex。历史 Grok 审计记录保留，不重写证据。

## 已完成或已批准

- DEC-01 至 DEC-10 已由产品负责人全部批准。
- `docs/PRD.md`、`docs/SYSTEM_DESIGN.md` 和 `docs/IMPLEMENTATION_ROADMAP.md` 已批准。
- 多 Agent 协作模式 ADR-001 已接受并生效。
- C-01 至 C-08 已由产品负责人批准，配置与领域契约 ADR-002 已接受并同步到 System Design；ADR-006 字幕契约也已同步，当前系统设计版本为 V1.3。
- `TASK-000` 已整合到 `main` 并通过整合后检查，状态为 `DONE`。
- `TASK-001` 已由 Codex 实现、Grok 独立审查、主控验收，并以 merge commit `5273e069aa34392db957e82b8803a709bdd1ab1f` 整合到 `main`；整合后全部门禁通过，状态为 `DONE`。
- 产品负责人已批准 `TASK-002` 使用 `pydantic>=2.13.4,<2.14`、`PyYAML>=6.0.3,<7`；实现、修复、独立审查及整合后检查均通过，并以 merge commit `823d68a2dffc1745e04cbbe54c817bf0c117a6fa` 进入 `main`，状态为 `DONE`。
- `TASK-003`/`TASK-004` 只读预检已完成且未修改仓库；产品负责人已批准 ADR-003 S-01 至 S-08 与 ADR-004 D-01 至 D-08。
- `TASK-004` 已获任务级授权：`yt-dlp[default,deno]>=2026.7.4,<2026.8`、必要传递依赖、网络下载、`pyproject.toml`/`uv.lock` 和所列 uv 命令；真实 YouTube 冒烟、Cookie、账号登录、remote components、ffmpeg 仍未授权。
- 产品负责人已授权“复用优先”交付策略，ADR-005 已接受；附件候选和其他组件的 `DIRECT/ADAPT/REFERENCE/REJECT` 结论记录于 `docs/REUSE_REGISTER.md`。
- 产品负责人已于 2026-07-15 批准 ADR-006 T-01 至 T-15；TASK-005 的选择、格式、领域结果、规范化、质量、缓存、错误与 Artifact 恢复契约已冻结，V1 明确不新增 Schema/migration、不修改 `state.py` 或 `complete_stage`。
- TASK-006/TASK-007 Codex 只读 Scout 已在 `main@b335b12358bbbc9dada1abfafc5a2fe9a68494be` 完成预检且仓库无变化；其结论为 `DECISION NEEDED`，不构成任何实现、依赖、模型、服务或系统工具授权。
- 产品负责人已于 2026-07-17 批准 ADR-007 L-01 至 L-15，并已授权 TASK-005A 从
  `main@82f45a1c04f9eba3264cd743b28bc339d79b34fc` 在独立 Codex worktree 实施。该任务
  不实现 Provider 或安装模型；完成、独立审查并整合为 `DONE` 后，TASK-006/TASK-007
  才可从同一 main 基线并行分配。

## 当前阻塞

- TASK-006 仅获 `mlx-whisper` 包/锁定与离线实现授权；Whisper 模型下载/加载、ffmpeg、
  媒体/YouTube 下载和真实转写冒烟仍未授权。TASK-007 仅获离线 Fake/标准库实现授权；
  Ollama 安装/启动、`qwen3:8b` 拉取和真实模型调用仍未授权。

## 下一步

1. 原 TASK-006 Implementer 仅修复 Artifact 预检/删除/post-delete CAS 顺序，并补充真实
   SQLite 冲突回归；不得改变 Repository/Schema 契约。
2. 原 TASK-007 Implementer 仅在既有评分/Adapter 与测试范围内修复完整异常链脱敏、短读
   分类，并用已有 Repository 的 Provider Call 与 `complete_stage` 完成原子评分持久化；
   不得改变 Schema、依赖或共享领域契约。
3. 两项 Correction 均完成后，各自再进入全新独立 Codex Reviewer；在此之前继续不批准模型
   下载、Ollama、ffmpeg、媒体或凭据操作。

## 当前并行调度

| 分组 | 工作 | 写入权限 |
|---|---|---|
| 已完成可关闭 | TASK-005 closure sync | 已以 5 个控制面 Markdown 文件关闭为 `DONE`；未重跑产品门禁或清理 |
| 已完成可关闭 | TASK-006/007 Read-only Scout | 预检已回传且仓库无变化；无需保持终端 |
| 已完成可关闭 | TASK-005 第二次独立 Codex Reviewer | evidence 已提交且 Verdict=`REJECT`；不得修代码 |
| 已完成可关闭 | TASK-005 第三次独立 Codex Reviewer | evidence 已提交且 Verdict=`REJECT`；不得修代码 |
| 已完成可关闭 | TASK-005 Implementer、第四次 Reviewer 与 Product Integrator | evidence 已合并为 `cfc302...`；不得修改代码或重新分配 |
| 已完成可关闭 | TASK-004 Product Integrator、第五次 Reviewer 与 TASK-005 Scout | 证据已保留，无活跃写入 |
| 已完成可关闭 | TASK-005A 第一轮独立 Codex Reviewer | evidence `3cec2d6...` 已 `REJECT`；不得修代码 |
| 已完成可关闭 | TASK-005A Codex Implementer Correction 1 与第二轮 Reviewer | evidence `e726656...` 已 `APPROVE`；不得继续写入 source |
| 已完成可关闭 | TASK-005A Product Integrator | merge `865f4fed...` 已通过整合后门禁；不得继续写入 source |
| 正在修复 | TASK-006 原 Codex Implementer（Correction 1） | P1：CAS 冲突前不得删除；仅 4 个允许路径 |
| 正在修复 | TASK-007 原 Codex Implementer（Correction 1） | P1：异常链不可泄漏，评分必须使用已有 SQLite 原子完成；仅评分/Adapter、既有测试、夹具与 handoff |
| 等待资源授权 | TASK-006/TASK-007 后续真实资源阶段 | 模型、服务、ffmpeg、媒体和凭据继续单独审批 |

## 授权边界

- `TASK-001` 已授权：本机 Python 3.12、uv、`uv_build>=0.11.28,<0.12`、`pytest>=9.1.1,<10`、`ruff>=0.15.21,<0.16`、`mypy>=2.3,<3`、必要传递依赖、网络下载和锁文件/工具链写入。
- `TASK-002` 已授权：`pydantic>=2.13.4,<2.14`、`PyYAML>=6.0.3,<7`、uv 解析出的必要传递依赖、网络下载、修改 `pyproject.toml`/`uv.lock`，以及执行 `uv add`、`uv lock --check`、`uv sync --locked` 和任务卡验证命令；不包含可选 extras 或其他运行时依赖。
- 已批准 OpenAI 作为 V1 首个云 Adapter；尚未授权写密钥或真实付费调用。
- 已批准 MLX Whisper；尚未授权下载模型。
- `TASK-003` 已批准 ADR-003 最终 SQLite Schema、migration、租约、逐次尝试审计和任务卡验证；授权在正式开工包后生效。
- `TASK-004` 已批准 ADR-004 与 `yt-dlp[default,deno]>=2026.7.4,<2026.8`、必要传递依赖、网络下载、`pyproject.toml`/`uv.lock` 和所列 uv 命令；不含真实网络冒烟、Cookie、账号、remote components 或 ffmpeg。
- ADR-005 允许主控决定普通复用方式，但新增依赖、系统工具、远程服务、密钥、付费、许可证义务和真实数据操作仍需原有具体审批。
- ADR-006 已批准 TASK-005 使用现有 yt-dlp/标准库和既有 Artifact/Repository 语义；不授权新增依赖/锁文件、Schema/migration、`state.py`/`complete_stage`、真实 YouTube/字幕或其他红线操作。
- TASK-005 已获正式实施授权：Codex Implementer、全新独立 Codex Reviewer、固定 base/worktree/8 文件范围、已有锁定依赖的 `uv sync --locked`（仅缓存缺失的包下载）与离线检查/构建。该授权不改变上述真实网络、认证、媒体、Vault 或依赖/Schema 红线。
- ADR-007 已接受；TASK-005A 已获固定 worktree、代码写入和既有锁定依赖离线门禁的
  独立授权，但不得新增 Schema/migration、依赖或锁文件，也不授权模型/系统工具、
  服务或真实资源命令。TASK-006/007 的独立资源门禁继续生效。
- 2026-07-19 已分配 TASK-006 阶段 A 和 TASK-007 离线实现。TASK-006 可解析、锁定并
  安装 `mlx-whisper>=0.4.3,<0.5` 与必要传递依赖；TASK-007 不改依赖/锁文件。真实
  模型、Ollama、ffmpeg、媒体、YouTube、认证、Vault/密钥和文件删除仍未授权。
- TASK-006 第一轮独立 Reviewer evidence `f1c15ed6eb854a4a8ed2299bbbf89e1cb6266426` 仅改
  handoff，Verdict=`REJECT`：真实 SQLite 证明未知 Artifact id 或陈旧 CAS 时清理路径会在
  index confirmation 前删文件。产品负责人批准的 Correction 1 维持 `state.py` 的
  post-delete index-only 语义，要求先以现有 Artifact 读取验证删除前置条件；最终 CAS
  竞态明确只是 at-most-once cleanup 风险，不引入 reservation/Schema 或 exactly-once 声明。
- TASK-007 第一轮独立 Reviewer evidence `266c488c17fc82cb648053b5e1066211a7bea9a9` 仅改
  handoff，Verdict=`REJECT`：`OllamaScoringProvider` 的修复响应、短读和部分畸形/超限响应
  可经异常链泄漏或逃逸；`ScoringService` 只使用内存缓存，未复用既有 `ProviderCall`、
  `ArtifactWrite`、`ScoringSummaryWrite` 与 `complete_stage` 的原子完成契约。Correction 1
  仅限补齐该既有契约与离线真实 SQLite 回归，禁止 Schema、依赖、领域契约和真实 Ollama 路径。
- 真实 Obsidian Vault 和 launchd 操作均未授权。

## 当前风险

- TASK-001 的 `.gitignore` 使用未锚定 `data/`、`logs/`，会忽略任意同名嵌套目录；不违反当前 AC-3，已登记为 `TASK-014` 发布门禁检查项。
- TASK-001 的 build backend 由隔离构建环境按批准范围解析，不作为运行依赖写入 `uv.lock`；实现者、主控和 Reviewer 均实测为 `uv-build==0.11.28`。
- TASK-002 已冻结配置与跨模块领域接口；后续任务不得为了减少文件量退回自由形状 `dict`，如需改变公共契约必须先回到主控决策。
- TASK-002 修复提交已关闭原预审发现的密钥错误回显、公共自由 `dict`、可变公共状态表和额外 `ErrorCode`；Reviewer 已独立重跑哨兵、公开 API、运行时不可变性及完整 AC-1 至 AC-8。
- TASK-002 的 Provider request correlation/调用元数据已由 Reviewer 对照 System Design §5.1/§5.2 复核，未发现必须新增 Wrapper 或公共字段的冲突。
- TASK-002 Reviewer 已判定 Provider request correlation/调用元数据与冻结字段一致；剩余 P3 为 `MappingProxyType` 对私有 backing dict 的 live view，公共写入仍被拒绝，不阻断 V1 整合。
- TASK-003 已通过独立 Grok 审查并以 merge commit `072511f20b587f973b29437d79080f6cb7863f1a` 整合到 main：两组 focused tests、全量 86、mypy、Ruff、`uv build` 及 migration SQL 包含性全部通过。无 P0/P1/P2；非阻断 P3 为路径脱敏可能裁去 URL 片段、周报 `scope_key` 的周号正则略宽但表级 `iso_week` 仍限制 `1..53`。TASK-003 仅提供 at-most-once best effort，不声称跨外部 Provider 与数据库提交的严格 exactly-once；这些风险随发布门禁保留。
- TASK-004 独立 Reviewer 证据 `f34cbb...` 为 `REJECT`：P1 包括 yt-dlp 畸形 payload 逸出 `ValueError`、请求/响应 video ID 不一致、RSS 不完整 entry 静默跳过且推进游标、HTTP 404/403/503 的终态/重试语义反转；P2 包括 RSS read 失败未关闭 response 与 `needs_auth` 误标 PUBLIC，P3 为公开注解测试遗漏 `Any`。范围、依赖、公开 Surface 和安全 options 均通过，但上述 P1 阻断合并。
- TASK-004 第三轮修复 `30932e1...` 已关闭 Reviewer 列出的 4 个 P1、2 个 P2 与 1 个 P3：静态核验确认 malformed mapping 在 Adapter 边界安全封装、返回 ID 与请求 ID 交叉校验、RSS 不完整 entry 使全批失败并不推进 cursor、HTTP 状态在宽泛文本前分类、response 在 finally 关闭、`needs_auth` 为 `RESTRICTED`、公开注解哨兵拒绝 `Any/object`。完整 17 文件范围与 correction 5 文件范围均通过；该结论不替代第二次独立审查。
- TASK-004 第二次独立 Codex 审查 `5d66c28...` 重新运行全部门禁仍发现两个 P1：`_coerce_age_limit()` 处理非法值时虽返回 `INVALID_RESPONSE`，但 `AppError.video_id` 为 `None` 而未保留请求身份；RSS entry 缺 channelId 时实现以请求 channel 回填，仍保存候选并推进 cursor。其他 correction 3 覆盖项均通过。TASK-004 回到 `IN_PROGRESS`，correction 4 必须只修复这两项及其离线回归。
- TASK-004 correction 4 `54c0ab2...` 仅改原允许的 5 文件：静态核验确认 age_limit 映射路径将请求 ID 传入安全错误，RSS entry channelId 不再回填且缺失/不匹配立即整批失败；unit/integration 回归覆盖候选/游标不变和较旧条目修复后可发现。该结论不替代全新独立 Grok Reviewer 的复跑与探针。
- TASK-004 第三次独立 Grok Reviewer evidence `1883367d313623c42d9d3624b16307ca8d502709` 已对 correction 4 给出 `APPROVE`：unit 33、integration 6、全量 86、mypy、Ruff、CLI、lock/sync 与三组独立探针全部通过，无 P0/P1/P2/P3；该 review commit 仅修改 TASK-004 handoff。
- 主控随后按 ADR-004 D-08 执行真实组合 Surface 探针，得到 `runtime_protocol_match=False`，并确认 `SQLiteStateRepository` 缺少 TASK-004 Protocol 要求的 `get_cursor`、`upsert_metadata`、`mark_unavailable`；同名 `save_discovery_batch` 也缺少 consumer 侧未传递的 `expected_revision`、`pipeline_version`、`now`。若直接整合，`DiscoveryService` 无法以真实 SQLite Repository 运行，因此作为新 P1 退回 correction 5；修复必须对齐 TASK-003 已接受 API，不能改 Schema/state 或用宽类型/重复 wrapper 隐藏不兼容。
- TASK-004 source 以 merge `eb9246b...` 同步 main/TASK-003 后，correction 5 `d87253e...` 已把 consumer Protocol/Service/Fake 对齐四个 TASK-003 具名方法，并加入真实 SQLite 组合测试；未修改 state、migration、domain 或新依赖。主控预审又要求固定范围无尾随空白、真实 Service 级 CAS 竞态、Fake/SQLite 未知视频 parity 和 naive UTC/空 pipeline version 零副作用边界。
- TASK-004 correction 5A `9750df2...` 静态关闭上述补证：相对 `d87253e...` 仅改四个允许文件，`58c79af...HEAD` 固定 Diff check 为 0，完整产品范围仍为原 17 路径；Implementer 自报 state 30、unit 35、integration 10、全量 131、mypy/Ruff/CLI/build 全 PASS。该自报不替代第四次独立 Codex Reviewer，任务保持 `IN_REVIEW`。
- TASK-004 第四次 Reviewer 在恢复后完成审查，evidence `d510794ffccf54948f967f010685aef1c0a02f3d` 仅修改 handoff，Verdict=`REJECT`。P1-1 是可变 Protocol attributes 使 frozen `ChannelCursorRecord`/`VideoRecord` 无法通过真实 mypy wiring；P1-2 是纯空白 `pipeline_version` 在 Source/Metadata Provider 调用后才触发 SQLite CHECK。Correction 6 必须以只读严格类型和应用边界零副作用测试关闭，不能用宽类型、cast/ignore、wrapper 或修改 TASK-003 掩盖。
- TASK-004 correction 6 `7272528a3c5603087446251ee96ae4766fedeb96` 只改四个允许文件：Protocol 只读字段改为 property，Service 在外部调用前拒绝纯空白版本；主控独立复跑真实 mypy wiring probe 和 whitespace focused unit 均 PASS。完整 17 路径与固定 Diff check 通过；仍须第五次 Reviewer 独立复跑 132 tests、build、真实 SQLite 零副作用和全部 AC/D 门禁。
- TASK-004 第五次 Reviewer evidence `d4d6d01ceba3b9524305bb41ece81b8783f3db4b` 只修改 handoff，Verdict=`APPROVE`：132 tests、mypy src、精确静态 wiring、真实 SQLite 空白零副作用、correction 3/4 安全回归、AC-1 至 AC-5 与 D-01 至 D-08 全 PASS，无 P0/P1/P2/P3。剩余 YouTube 字段漂移、`mutagen` GPL 分发和非严格 exactly-once 风险不阻断整合，继续由真实冒烟/TASK-014/编排边界跟踪。
- TASK-004 已由 Codex Product Integrator 以 merge commit `dc3f097ce125bc8390b04d0913b5d00f44eae3e8` 整合到 main；双父精确为 `da469f54...` 与 `d4d6d01...`，第一父差异精确为 17 个批准路径。整合后 lock/sync、state 30、unit 36、integration 10、全量 132、mypy/wiring、Ruff、CLI、build 与 migration 包含性均 PASS。真实 YouTube/字幕、Cookie/登录、remote components、ffmpeg、媒体/字幕下载、真实 Vault/密钥仍未运行且未获授权。
- TASK-005 只读 Scout 确认的字幕输出、选择、格式、质量、缓存与恢复空白已由 Accepted ADR-006 T-01 至 T-15 关闭。V1 使用现有两个 Artifact kind、稳定 key/path、Provider-call/文件哈希验证及空 Artifact stage completion，不新增 manifest migration 或 job-neutral Artifact 语义；若实现证据否定该路径，必须停止并新建 ADR。
- TASK-005 实现 commit `98d19700818bcae14efc412aaaaeb6eed97a1535` 为 base 的单一非 merge 后继，11 个变更文件精确属于批准的 8 个路径组，source clean 且固定 Diff check 通过。Implementer 自报 191 tests、mypy、Ruff、CLI、静态 SQLite wiring、lock/sync 和 offline build PASS；这些证据仍须独立 Reviewer 复跑。
- TASK-005 变更规模为 4,384 行，其中 `transcripts.py` 1,664 行、integration test 1,020 行。Reviewer 必须判断职责、复杂度、外部行为测试、安全与性能，不能以行数自动拒绝，也不能以测试数量自动批准。
- TASK-005 第一次独立 Codex Reviewer evidence `515c34894bb138115a4658d962fb5ef0aa7d9d80` Verdict=`REJECT`。规定 191 tests、mypy/wiring、Ruff、CLI、offline build、lock/sync 与 Diff 均通过，但独立探针发现 5 个 P1：异常链泄漏正文、VTT speaker/cue 语义丢失、Adapter 短读/格式/payload 边界不完整、Provider-call 幂等与恢复错误、canonical-only 失效不能从 verified raw 重建；另有职责聚合 P2。范围、依赖、许可证与红线审查通过。
- TASK-005 Correction 1 `55156f9f53a610ccbf9c8806f19f19f2c16bb1cf` 为 review evidence 的单一后继，精确修改 5 个允许文件、约 1,489 行；Implementer 自报五个 P1 均有 RED/GREEN，contracts 50、policy 30、integration 53、全量 219、两项 mypy、Ruff、CLI、lock/sync、offline build 与 Diff 全 PASS。该自报随后由第二个全新独立 Reviewer 复核，结果见下一条 evidence。
- TASK-005 第二次独立 Codex Reviewer evidence `5bb750e8d2f1336b321dbca64e7c409f66853b0f` 只修改 handoff，Verdict=`REJECT`：规定的 focused 50/30/53、全量 219、两项 mypy、Ruff、CLI、offline build、包内容和 Diff 均 PASS，但 R1/R4/R5 仍发现 3 个 P1。具体为 Adapter/Service 与 canonical decode 的异常图仍持有正文/临时 URL/绝对路径；非 all-invalid 终态错误码漂移、reservation 后文件失败遗留 lease 且真实竞态重复目录枚举；raw metadata token/current language、canonical model 与 symlink cache 分类验证不足。R2 VTT 与 R3 HTTP/目录 fail-closed 已独立 PASS；另保留职责/私有 hook 和嵌套 metadata 资源放大两个 P2。
- TASK-005 Correction 2 `f95bdb1b5ac0fcdc8906b2daa7138f2f6d60138f` 为 second review evidence 的单一非 merge 后继，精确修改 5 个允许文件；Implementer 记录 Reviewer 2 的独立反例先 RED 11 failed 后 GREEN，并自报 contracts 50、policy 30、integration 68、全量 234、两项 mypy、Ruff、CLI、offline build、包内容与固定 Diff 全 PASS。静态证据显示 reservation 已前移至目录枚举前、异常安全转换与 provenance 校验已加强；这不构成 Reviewer APPROVE，两个 P2 仍保留。
- TASK-005 第三次独立 Codex Reviewer evidence `30c665181db77607648aa1a6fdbb1d5502b71d7d` 只修改 handoff，Verdict=`REJECT`：规定的 focused 50/30/68、全量 234、两项 mypy、Ruff、CLI、offline build、包内容和 Diff 均 PASS；Q2 reservation/CAS/终态/lease/2 秒恢复与 Q4 VTT/HTTP/安全回归 PASS，但 Q1/Q3/Q5 发现 3 个 P1。具体为公共 SubtitleAdapter 的敏感 message 与错误 stage/video 穿透 Service；raw source type/actual language 和 canonical rolling flag 可被自洽篡改后命中；500,000 name runs 与 200,000 空 language buckets 触发无界处理，原资源 P2 升级为 P1。Service 职责/私有 hook 聚合继续保留为单一 P2。
- TASK-005 Correction 3 `abf2acba25f9732a9511ecd54c4b92ef6c0d68e1` 为 third review evidence 的单一非 merge 后继，精确修改 `transcripts.py`、`providers/subtitles.py`、integration tests 与 handoff 4 文件；Implementer 记录 Service 对 enumerate/read 的公共 Adapter 错误重建、成功 Provider-call/response Artifact/key/SHA 的 provenance binding 及第 1001/513 项的流式资源拒绝，并自报 contracts 50、policy 30、integration 77、全量 243、mypy/wiring、Ruff、CLI、offline build、包内容与固定 Diff 全 PASS。该证据尚未经第四次独立审查；Service/私有 hook 聚合 P2 仍保留。
- TASK-005 第四次独立 Codex Reviewer evidence `d5268ef08b360e932b5dda9d0fb70d71b13587a4` 只修改 handoff，Verdict=`APPROVE`：独立复跑 lock/sync、focused 50/30/77、全量 243、mypy/wiring、Ruff、CLI、offline build、包内容与固定 Diff 全 PASS；P1 probe A 公共 Adapter 边界、B 可信 provenance、C streaming bounds 以及 Q2/Q4、AC-1 至 AC-5、ADR-006 T-01 至 T-15 全部 PASS。无 P0/P1/P3；Service/私有 test hook 聚合 P2 保留，不阻断验收或整合。真实网络、认证、媒体与 Vault 路径未运行且未授权。
- TASK-005 已由 Codex Product Integrator 以 merge commit `cfc302ddc41cd908777f49de292327640b6f8314` 整合到 main：双父精确为 `1e5e5f8...` 与 `d5268ef...`，first-parent Diff 精确为 11 个批准文件。整合后 lock/sync、focused 50/30/77、全量 243、mypy/wiring、Ruff、CLI、offline build 及 migration/字幕模块 package inclusion 均 PASS；无意外文件、push 或 source cleanup。唯一非阻断 P2 为 Service/私有 test hook 聚合；真实 YouTube、认证、媒体和 Vault 仍未运行且未授权。
- `yt-dlp[default]` 的已批准必要传递依赖包含 `mutagen`（GPL-2.0-or-later）。本地开发/测试不阻断 TASK-004，但二进制或依赖捆绑分发前必须由 TASK-014 生成许可证清单并作出兼容分发决定。
- TASK-004 将候选/游标提交与元数据成功解耦，并由 TASK-005 重查字幕轨道；Reviewer 需防止实现者为了复用外部工具而改变该边界。
- TASK-004 首个实现将 `SAFE_YDL_OPTS`、`build_ydl_opts` 和含 `Mapping`/`dict` 的 Adapter helper 显式置入 `__all__`，且 `YtDlpMetadataProvider` 公开了 `last_opts: list[dict[str, Any]]` 注入/属性。首个修复 `10f5ffa...` 虽隐藏了这些注解，却仍保留非私有 `map_info_dict_to_video_metadata(info: object)` 以及公开的 `ydl_factory`/`last_opts` 注入参数；以 `object` 包装自由结构不符合修复包。第二轮修复 `9db800f...` 已移除残余公开 mapper 与所有公开测试钩子，改为私有 `_map_*` / `_bind_test_hooks`；主控静态核验其构造面、模块符号、修复 commit 的 4 文件范围和完整 17 文件范围均通过。独立 Reviewer 仍须重跑门禁并独立判断。
- `video-to-subtitle-summary-skill`、`yt2md` 只能按复用登记选择性参考；其中存在 faster-whisper/ffmpeg/付费 API/直接 Vault 写入或 TLS 风险，不能整套引入。
- `youtube-skills` 依赖 TranscriptAPI 账号、密钥和 credits，与 V1 本地优先边界冲突，已标记为 V1 `REJECT`。
- MLX Whisper 的安装、模型下载和资源兼容性属于 `TASK-006`，不扩入 `TASK-001`。
- TASK-006/TASK-007 预检确认，`mlx-whisper`、模型、ffmpeg、Ollama 与评分模型的
  ADR-007 方向已获接受，但仍不等于任务级安装/下载授权；精确版本、digest、缓存、
  HTTP、安全和拆分门禁必须由 TASK-005A/TASK-006/TASK-007 分别执行和审查。
- 官方 PyPI 显示 `mlx-whisper` 最新稳定版为 `0.4.3`、MIT、Python `>=3.8`，但包含 `torch` 等必要传递依赖；本机 Python 3.12/arm64 的实际解析、安装和资源表现尚未验证。
- 默认 MLX Whisper 转换模型已核实 revision `a4aaeec...`、权重 `1,613,977,612` bytes 与 LFS SHA-256；转换仓库 model card 未声明 license，不能仅用上游 OpenAI 模型 MIT 自动替代该证据。
- TASK-007 推荐标准库 loopback HTTP，不新增 httpx；拟验证 Ollama `>=0.32.1,<0.33` 和 `qwen3:8b` 固定 digest。Ollama 安装/服务、模型拉取和真实调用仍未授权。
- TASK-005A 已使 `complete_stage` 能在 `TRANSCRIPT_READY -> SCORED` 时原子写入评分摘要；
  TASK-007 Correction 1 必须复用这一既有契约，不能继续以仅内存缓存替代持久 Provider Call、
  Artifact、Pipeline CAS 和 Job 完成。
- TASK-005A implementation `85cd5362460044773317a48cbaae58e55aa735af` 为 approved
  base `82f45a1...` 的唯一非 merge 后继，完整 Diff 精确为配置示例、`config.py`、
  `domain.py`、`state.py`、三份指定测试和 handoff 共 8 个批准路径；`pyproject.toml`
  与 `uv.lock` 无差异。Implementer 自报 focused 52/10/34、全量 250、mypy、Ruff、CLI
  与 offline build 均通过，但这些结果尚未由独立 Reviewer 验收。实际模型、服务、媒体
  和文件删除仍严格延后至分别授权的后续任务。
- TASK-005A 第一轮独立 Reviewer evidence `3cec2d6a7b60b11912c10e714dc1473197d7374f`
  已 `REJECT`：虽然全量 250、mypy、Ruff、CLI、offline build 和配置/SQLite/Artifact
  探针都通过，但新增 frozen Pydantic 领域对象能被 `model_copy(update=...)` 绕过其字段
  与跨字段验证，生成 hash 不匹配输入和错误最终评分策略。这是 AC-2、ADR-007 L-03/L-05/
  L-06 的 P1；Correction 1 必须仅通过重新验证或拒绝 unchecked update 关闭，并接受新一轮
  独立审查。后续模型、服务、媒体和文件删除继续未授权。
- TASK-005A Correction 1 `3a7df1029a77b7dec84a76c304c10e372f755b77` 为 reviewer evidence 的
  单一非 merge 后继，精确修改 `domain.py`、contracts test 和 handoff 三个允许路径。
  修复策略仅为本任务四个新增评分对象禁止所有 `model_copy(update=...)`，保留无 update
  复制，避免全局改变既有领域模型；Implementer 自报 contracts 53、全量 251、mypy、
  Ruff、CLI、lock/sync、offline build 与 package inclusion 均通过。该结果仍必须由
  第二个全新独立 Reviewer 验证。
- TASK-005A 第二轮独立 Reviewer evidence `e726656ffcc96b3c61d12f649c5574dc927add62`
  只修改 handoff，Verdict=`APPROVE`：完整离线门禁、Pydantic `model_copy` fail-closed
  边界、无 update copy、SQLite 原子回滚和 Artifact index-only 探针，以及 AC-1 至
  AC-5/适用 ADR-007 边界均通过；P0/P1/P2/P3 均无。
- TASK-005A 已由 Codex Product Integrator 以 merge commit
  `865f4fed90dcc22ea43688442c1c4f210b4d31b7` 整合并关闭为 `DONE`。两父提交固定为
  `7cdea4b...` 与 `e726656...`，first-parent 差异精确为 8 个批准路径；focused
  `53/10/34`、全量 `251`、mypy、Ruff、CLI、locked sync、offline build 和 migration
  package inclusion 全部通过。`dist/` 仅为 ignored/uncommitted 构建产物，未被删除或提交。
- 早期 commit 曾使用本机自动推导作者身份 `华 <hua@huadeMacBook-Pro.local>`；仓库现已固定 `Mozhu <huangbuqubunao@gmail.com>` 且 `user.useConfigOnly=true`，后续提交必须保持该已验证身份。

## 主控接收执行结果的最小格式

```text
Task:
Role:
Branch/worktree:
Base commit:
Head commit:
Checks: <command + result summary>
Reviewer verdict:
Remaining risks:
Decision needed: None | details
```

不要把完整构建日志或长篇思考过程粘贴到主控对话；把证据保存到交接文件，只回传摘要和可定位路径。
