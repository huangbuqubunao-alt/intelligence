# YouTube Intelligence Agent 项目状态

- 更新时间：2026-07-23
- 当前阶段：Phase 3 — TASK-010 已整合并收口为 `DONE`
- 主控状态：ACTIVE
- 规划基线 commit：`c0f1f553db52b1cb4eb354e5c689c2abc5556223`
- 实现任务基线：分配时取最新已验收的 `main` commit，并写入任务包
- 活动 worktree：`/Users/hua/Documents/yia-worktrees/task-008` /
  `codex/task-008-deep-analysis@473119704c7638d7afd4e68d84d00e85064ceabd`，以及
  `/Users/hua/Documents/yia-worktrees/task-009` /
  `codex/task-009-obsidian-notes@473119704c7638d7afd4e68d84d00e85064ceabd`。
  TASK-009A worktree 与历史 TASK-005/TASK-005A/TASK-006/TASK-007 worktree 只保留为审计证据。
- 活动任务：TASK-008A 已由 Codex Product Integrator 以 merge commit
  `64a9c41683bb559b27bebb784fcff4fbff644a18` 整合并关闭为 `DONE`。accepted source
  固定为 `7a8239f3da02fa204b63702677fae5f669fb99c0`。TASK-009A 已由 Codex Product Integrator
  以 merge commit `9b0269eddbd29cee83a056d44951d7973c87492b` 整合，收口后为 `DONE`；accepted source
  固定为 `e30b40c7bfb388748ff1aee0420177f2ee6c2e2e`。正式 TASK-008/TASK-009 的共享契约依赖已满足，
  已从 `main@473119704c7638d7afd4e68d84d00e85064ceabd` 并行分配给 Codex。TASK-008 首轮独立审查
  evidence `b61f46f...` 为 `REJECT`：持久化路径绕过本地 token 上限并在超限时读取凭据/调用 Fake
  transport。Reviewer 2 evidence `02317f2...` 再次 `REJECT`：预算耗尽路径仍在 ProviderCall 预留和
  凭据读取后才返回，留下 PENDING 状态。Reviewer 3 evidence `b380a8c...` 再次 `REJECT`：持久化
  路径仍在关闭、低价值和凭据门禁前预留 ProviderCall。Reviewer 4 evidence `193239230...` 为 `REJECT`：
  Correction 3 缓存恢复未验证 raw/structured Artifact 的内容 hash 及 request/provider/model identity，篡改结果仍可
  原子推进 Pipeline/Job。Reviewer 5 evidence `78ae101...` 为 `REJECT`：隔离 SDK child 的 handshake/response
  使用无期限 `readline()`，可能无限阻塞 Job。Correction 5 source `dcbbd38...` 已经 Reviewer 6 evidence
  `6914312...` 独立复跑后 `APPROVE`（P0–P3=0）。TASK-008 已由 Codex Product Integrator
  以 merge commit `4f9ca390cdbfb57e6c1e14bf6b900402bd6945f7` 整合到 main：双父精确为
  `7659943803d0e02799cb835418e4469fb08d52df` 与
  `6914312eaac0e3d65f1d2895ea2e3c0c2c39f4d8`，first-parent Diff 严格为六个授权路径，
  `git diff --check`、lock/sync、重点测试（4/30）、全量测试（361）、mypy、Ruff、CLI help、
  离线构建和 sdist/wheel 的 migration、prompt、固定 tokenizer 大小及 SHA-256 验证均通过；
  凭据格式扫描通过。source 已成为 main 祖先且两个 worktree 均干净；未 push、未触及 TASK-009。
  TASK-008 已在主控收口后为 `DONE`。
  TASK-009 首轮 Reviewer 只因未跟踪的
  `.codebase-memory/` 本地索引工件而 `REJECT`；经产品负责人批准精确清理后 Reviewer 2 复审仍为
  `REJECT`：标题变化无法恢复首次 NoteRef，且同 video_id 非受管候选不会 fail-closed，另有 `C:`
  子目录 P2。Reviewer 3 evidence `f4a231b...` 再次 `REJECT`：Vault 权限类 OSError 被错误归为
  `LOCAL_RESOURCE` 而非 `PERMISSION_DENIED`。Correction 2 source
  `22147b087157a6bbb0adc7e78f2f5d3eae700f8e` 是 reviewer-3 evidence 的唯一子提交，只修改
  Obsidian Adapter、既有集成测试和 handoff：`EACCES`、`EPERM`、`EROFS` 映射为
  `PERMISSION_DENIED`；`ENOSPC` 与 errno-less fsync/replace 仍为 `LOCAL_RESOURCE`。
  Implementer 自报临时 Vault/SQLite 的原文件、临时文件、Pipeline/Job/Artifact 回归以及全部离线
  门禁通过。Reviewer 4 evidence `e675feef7f12d19561f1ca439e181a47f4a521b8` 是 Correction 2 的唯一
  子提交且仅改 handoff，Verdict=`APPROVE`、P0–P3=0；独立 N-13 故障矩阵与全部离线门禁通过。
  source 已干净。TASK-009 已由 Codex Product Integrator 以 merge commit
  `1cb718b7e7e53705ae12792a3c2ba2d0f26b2476` 整合到 main：双父精确为
  `777e5a65b74e719050d2d6d4979cccea9d4ccfba` 与
  `e675feef7f12d19561f1ca439e181a47f4a521b8`，first-parent Diff 严格为六个实际使用的
  授权路径（fixtures 未改动）。lock/sync、focused `4/17`、全量 `382`、mypy、Ruff、CLI、离线构建和
  sdist/wheel 模板、migration inclusion 均通过；source 已成为 main 祖先，两个 worktree 均干净，未 push
  或清理 source。TASK-009 已在主控收口后为 `DONE`。
- TASK-007 Correction 2 已证明存在 recovery Artifact 时可只修复一次；新 P1 仅在“已标记为恢复
  重试但 Artifact 索引记录缺失”时触发。Correction 3 仅补齐既有 Provider Call 安全标记下的
  fail-closed 分支，真实 Ollama 或模型资源仍未授权。
- Agent 资源策略：Grok 当前不可用；所有新分配的 Implementer、Reviewer、Integrator 和 Scout 均使用 Codex。历史 Grok 审计记录保留，不重写证据。
- 实时控制面只存在于 `main`；为保留可审计的共同 base，TASK-008/TASK-009 source worktree 内的
  任务卡与项目状态文档是分配前冻结快照。Implementer 必须按 main 的动态授权包读取实时状态，
  不得把 source 快照当作冲突或写回 source 文档。

## 已完成或已批准

- DEC-01 至 DEC-10 已由产品负责人全部批准。
- `docs/PRD.md`、`docs/SYSTEM_DESIGN.md` 和 `docs/IMPLEMENTATION_ROADMAP.md` 已批准。
- 多 Agent 协作模式 ADR-001 已接受并生效。
- C-01 至 C-08 已由产品负责人批准，配置与领域契约 ADR-002 已接受并同步到 System Design；ADR-006 至 ADR-009 也已同步，当前系统设计版本为 V1.6。
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
- 产品负责人已于 2026-07-20 批准 ADR-008 A-01 至 A-15、ADR-009 N-01 至 N-15，
  以及 `openai>=2.46.0,<2.47`、`tiktoken>=0.13.0,<0.14`、
  `Jinja2>=3.1.6,<3.2` 的必要传递依赖、网络包下载、锁文件和共享任务离线命令。
- 产品负责人已于 2026-07-21 补充批准 ADR-008 A-16/A-17：固定包内
  `o200k_base.tiktoken` 资源及其 SHA-256、禁止运行时网络回退，并冻结 OpenAI SDK
  子进程隔离导入/导入后匿名管道密钥策略；TASK-008A Correction 1 可执行一次官方
  Blob 下载。

## 当前阻塞

- TASK-006 仅获 `mlx-whisper` 包/锁定与离线实现授权；Whisper 模型下载/加载、ffmpeg、
  媒体/YouTube 下载和真实转写冒烟仍未授权。TASK-007 仅获离线 Fake/标准库实现授权；
  Ollama 安装/启动、`qwen3:8b` 拉取和真实模型调用仍未授权。
- TASK-008 只获离线 Fake/隔离子进程 SDK 实现与测试授权；真实 OpenAI、密钥、付费调用、
  token-count、媒体、网络与用户内容仍未授权。TASK-009 只获测试临时目录内的原子写、替换、
  清理与 symlink 安全测试授权；真实 Vault、用户笔记、测试目录外写入和外部文件删除仍未授权。
- TASK-008 真实密钥/付费云调用和 TASK-009 真实 Vault/用户笔记始终是后续独立
  门禁，不由 ADR 或共享任务隐含授权。

## 下一步

1. TASK-012 Correction 1 source `d046c39...` 已提交，现等待独立 Reviewer 2 复跑 ADR-011 离线门禁；
   TASK-013/014 继续阻塞。
2. 真实 Whisper/Ollama/OpenAI、模型、ffmpeg、媒体、网络、真实 Vault、用户笔记、launchd 注册与凭据
   操作继续不批准。

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
| 已完成可关闭 | TASK-006 第四次独立 Codex Reviewer | evidence `f00209c...` 已 `APPROVE`，无 P0–P3；不得继续写 source |
| 已完成可关闭 | TASK-006 Product Integrator/Reviewer/Implementer | merge `fd9a074...` 已关闭为 `DONE`；不得继续写 source |
| 已完成可关闭 | TASK-007 Integrator/Reviewer/Implementer | merge `3d49ec...` 已关闭为 `DONE`；不得继续写 source |
| 等待资源授权 | TASK-006/TASK-007 后续真实资源阶段 | 模型、服务、ffmpeg、媒体和凭据继续单独审批 |
| 已完成可关闭 | TASK-008/TASK-009 Read-only Scout | 两份预检已回传，仓库无变化；终端可关闭 |
| 已完成可关闭 | TASK-008A 两轮 Reviewer、Correction 1 Implementer 与 Product Integrator | evidence `0f52c30...` 已 `REJECT`；evidence `7a8239f...` 已 `APPROVE`；merge `64a9c416...` 已关闭为 `DONE` |
| 已完成可关闭 | TASK-009A Implementer、两轮 Reviewer 与 Product Integrator | evidence `f73b287...` REJECT 已修复；evidence `e30b40c...` APPROVE；merge `9b0269...` 已通过整合门禁；不得继续写 source |
| 已完成可关闭 | TASK-008 Product Integrator/Reviewer | merge `4f9ca390...` 已进入 main；Reviewer 6 `APPROVE`，全部离线门禁通过；已为 `DONE`，不得继续写 source |
| 已完成可关闭 | TASK-009 Product Integrator/Reviewer | merge `1cb718b...` 已进入 main；Reviewer 4 `APPROVE`，全部离线门禁通过；已为 `DONE`，不得继续写 source |
| 已完成可关闭 | TASK-010 Product Integrator/Reviewer | merge `3d2122c...` 已进入 main；Reviewer 2 `APPROVE`，全部离线门禁通过；收口控制面已同步为 `DONE`，不得继续写 source |

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
- TASK-006 Correction 1 `17afcd349827b36e5ba18fb0eab443c1ae5fb53f` 是第一轮 review evidence
  的唯一非 merge 后继，精确修改 `transcription.py`、两份既有转写测试和 handoff 四个允许文件。
  Implementer 记录未知/缺失/不匹配 Artifact 时保留音频并返回 `INDEX_CONFLICT`，以及成功确认、
  post-delete CAS 竞态、kind/retention/root/hash、符号链接/路径逃逸的真实 SQLite 回归；自报
  focused `10/9`、全量 `270`、mypy、Ruff、CLI、locked sync、offline build 与 migration package
  inclusion 全 PASS。这些仅构成待独立复跑证据；预检到最终 CAS 间仍只声称 at-most-once cleanup。
- TASK-006 第二轮独立 Reviewer evidence `47599db196b1b9440de3ae57ec3547935f64b1dc` 是
  Correction 1 的唯一子提交且仅改 handoff，Verdict=`REJECT`：所有离线门禁及 unknown/stale/
  CAS/hash/root 边界均通过，但符号链接/路径逃逸虽保留文件，返回 `PATH_OUTSIDE_DATA` 而非
  已授权的统一 `INDEX_CONFLICT`。Correction 2 只可调整这一安全拒绝诊断与回归，禁止改变
  删除顺序、CAS、Schema/Repository、依赖或真实资源边界。
- TASK-006 Correction 2 `51b308828a6f2c433a9b4e92fb4a24e042f55d77` 是第二轮 review
  evidence 的唯一非 merge 后继，精确修改 `transcription.py`、两份既有转写测试和 handoff 四个
  允许文件；完整产品范围仍为既定八路径，`state.py`、Schema/migration、依赖和锁文件未变。Implementer
  自报绝对/相对路径逃逸、DATA-root escape 与符号链接均统一为安全可重试的 `INDEX_CONFLICT`，并保留
  所有文件/根外目标；focused `11/10`、全量 `272`、mypy、Ruff、CLI、locked offline sync、offline
  build 与 migration package inclusion 均 PASS。这些仍须由全新独立 Reviewer 复跑。
- TASK-006 第三次独立 Reviewer evidence `66f0b31023c290d76e2c14bea72d1cc103cc27c7` 是
  Correction 2 的唯一子提交且仅修改 handoff，Verdict=`REJECT`：规定离线门禁均通过，但
  `language_hint` 未进入缓存身份，导致不同语言请求可复用旧转写；另有错误 kind/root/retention
  Artifact 返回 `INELIGIBLE_ARTIFACT` 而非已冻结的统一、可重试 `INDEX_CONFLICT`。Implementer
  正确报告原四文件范围无法把 `WhisperDecodePolicy.language_hint` 传入唯一生产缓存键调用点；
  主控因此批准 Correction 3 使用 `transcription.py`、`providers/whisper.py`、两份既有测试和
  handoff 五个路径。Provider 仅可修改该缓存键调用点，并保持 executor、公共 Adapter、删除顺序、
  CAS、Schema/Repository、依赖和真实资源边界不变。
- TASK-006 Correction 3 `548338978b8656db0c650be276f847850af940a1` 是第三次 review
  evidence 的唯一非 merge 后继，精确修改上述五个允许路径；`providers/whisper.py` 只在既有
  cache-key call site 传入 `self._decode_policy.language_hint`。Implementer 自报 focused
  `11/12`、全量 `274`、mypy、Ruff、CLI、locked offline sync、offline build 与 migration
  package inclusion 全 PASS，并记录 wrong kind/root/retention 的 `INDEX_CONFLICT` 与临时
  SQLite/DATA-root 回归；这些仅为待第四次独立 Reviewer 复跑的实现证据。
- TASK-006 第四次独立 Reviewer evidence `f00209c8018a9e728d9f6509f0ae70067fa33676`
  是 Correction 3 的唯一子提交且仅修改 handoff，Verdict=`APPROVE`：focused `11/12`、
  全量 `274`、mypy、Ruff、CLI、locked offline sync、offline build、migration package
  inclusion、固定 Diff、缓存 API/`None/en/zh` 隔离和临时 SQLite/Fake cleanup 矩阵全部
  PASS；P0/P1/P2/P3 均无。保留 post-unlink/final-CAS 的 at-most-once 风险，不声称
  exactly-once；真实模型、ffmpeg、媒体、网络、Vault 与凭据仍未运行且未授权。
- TASK-006 已由 Codex Product Integrator 以 merge commit
  `fd9a07462a0596e1c5d4c67c200c3a7f2561fea1` 整合到 main：双父精确为
  `7d18ecffc61fc0def974ce07ee9dc1ceeb4bf305` 与
  `f00209c8018a9e728d9f6509f0ae70067fa33676`，first-parent 差异精确为批准的八个路径。
  整合后 lock check、locked offline sync、focused `11/12`、全量 `305`、mypy（13 source
  files）、Ruff、CLI、offline build 与 sdist/wheel migration inclusion 全 PASS；main/source
  均干净且 source worktree 保留。未运行模型、ffmpeg、真实转写、媒体、网络、Vault 或凭据路径。
- TASK-007 第一轮独立 Reviewer evidence `266c488c17fc82cb648053b5e1066211a7bea9a9` 仅改
  handoff，Verdict=`REJECT`：`OllamaScoringProvider` 的修复响应、短读和部分畸形/超限响应
  可经异常链泄漏或逃逸；`ScoringService` 只使用内存缓存，未复用既有 `ProviderCall`、
  `ArtifactWrite`、`ScoringSummaryWrite` 与 `complete_stage` 的原子完成契约。Correction 1
  仅限补齐该既有契约与离线真实 SQLite 回归，禁止 Schema、依赖、领域契约和真实 Ollama 路径。
- TASK-007 Correction 1 `f46881bc4a8ca0fda4d5ef7006b372bc566cff97` 是上述 evidence 的唯一
  非 merge 后继，精确修改 `scoring.py`、`providers/ollama.py`、两份既有评分测试和 handoff
  五个允许文件。Implementer 自报 lock/sync offline、focused 23、全量 274、mypy、Ruff、CLI、
  offline build、迁移包内容及固定 Diff 全 PASS；这不替代全新独立 Reviewer 的复跑与探针。
- TASK-007 第二轮独立 Reviewer evidence `d8eaeabdd2454141eeb646d9254f4a0a24626605` 是
  Correction 1 的唯一子提交且仅修改 handoff，Verdict=`REJECT`：全部离线门禁仍通过，但当
  主结构化响应无效且一次修复也失败时，主响应没有保存为受请求约束的 `SCORING_RAW`；重排 Job
  会再发起主调用与修复，违反 ADR-007 L-09。Correction 2 仅可在既有 Artifact/Provider Call/
  fail-provider-call 语义内保存并验证主响应恢复输入，禁止 Schema、依赖、领域或真实资源扩张。
- TASK-007 Correction 2 `567b0f63f9cefc6c8bff43bfea0e9e156ac3a02c` 是上述 evidence 的唯一
  非 merge 后继，精确修改 `scoring.py`、`providers/ollama.py`、两份既有评分测试和 handoff
  五个允许文件；相对共同 base 的完整产品范围仍为 11 个批准路径，锁文件无差异。Implementer
  自报 focused `16/14`、全量 `281`、mypy、Ruff、CLI、locked offline sync、offline build 和
  migration package inclusion 全 PASS；这只构成待独立复跑证据。
- TASK-007 第三轮独立 Reviewer evidence `1d27d3bdeb8981ca85deaacd5c1cad498ef7a632` 是
  Correction 2 的唯一子提交且仅修改 handoff，Verdict=`REJECT`：所有离线门禁仍通过，present-
  Artifact 恢复、修复一次和 atomic rollback 均通过；但已删除 recovery Artifact 索引记录时，
  实现把它当作首轮请求而再次发送主评分。Correction 3 必须以现有 `ProviderCall` 的安全、
  request-bound 恢复标记区分重试，不改 Schema；标记存在而 Artifact 缺失/篡改/不匹配时必须
  安全失败且不发送主评分或修复。
- TASK-007 Correction 3 `9da12c2a6932d04b936d6ae1543acb55a72ec9dd` 是上述 evidence 的唯一
  非 merge 后继，精确修改 `scoring.py`、评分 unit 测试和 handoff 三个允许文件；完整产品范围仍为
  11 个批准路径、锁文件无差异。Implementer 自报 focused `17/14`、全量 `282`、mypy、Ruff、CLI、
  locked offline sync、offline build 与 migration package inclusion 全 PASS；这只构成待独立复跑证据。
- TASK-007 第四次独立 Reviewer evidence `95087c115b799d6f4e1e063a0adba0a6d10352ce` 是
  Correction 3 的唯一子提交且仅修改 handoff，Verdict=`APPROVE`：focused `17/14`、全量 `282`、
  mypy、Ruff、CLI、locked offline sync/build、migration package inclusion 和固定 Diff 全 PASS；
  真实 SQLite/Fake probe 也确认 present recovery 单次 repair、rollback 可恢复，以及恢复索引/文件/
  哈希/模型/provenance 不匹配时零 transport 的 retryable `INVALID_RESPONSE`。P0–P3 均无。
- TASK-007 已由 Product Integrator 以 merge commit `3d49ecaf31a4ab800d6a58b5b44f815ab830a06c`
  整合到 main：双父精确为 `7b33f6f...` 与 `95087c...`，first-parent 差异严格为批准的 11 路径，
  锁/依赖未变。整合后 focused `17/14`、全量 `282`、mypy、Ruff、CLI、locked offline sync/build
  和 migration package inclusion 全 PASS。真实 Ollama/模型兼容性与质量仍需单独授权，不阻断离线关闭。
- 真实 Obsidian Vault 和 launchd 操作均未授权。
- TASK-008/TASK-009 只读预检已完成；ADR-008/ADR-009 已接受。TASK-008A 获准在
  正式分配后解析/锁定/安装 `openai>=2.46.0,<2.47`、
  `tiktoken>=0.13.0,<0.14`；TASK-009A 在依赖满足且正式分配后可处理
  `Jinja2>=3.1.6,<3.2`。必要传递依赖、网络包下载、`pyproject.toml`/`uv.lock`
  和各卡离线命令已批准。
- TASK-008A 已从
  `main@82d1fd7c7f2f82e77df0518e63755bad0bf240f2` 分配到
  `/Users/hua/Documents/yia-worktrees/task-008a` /
  `codex/task-008a-cloud-analysis-shared-contracts`；Codex Implementer 已完成固定
  source commit，第一轮 Reviewer 已结束并退回 Correction 1。原实现范围为任务卡
  7 路径；Correction 1 完整范围扩展为原 7 路径加固定 tokenizer 资源文件，仍不允许
  Provider、Schema/migration、`state.py`、`complete_stage` 或真实资源路径。
- TASK-008A Implementer 已提交
  `382251298af7fcbfadba66c1902af6de0a425179`，唯一父提交为固定 base，完整 Diff
  精确为任务卡 7 路径。Implementer 自报 contracts `66`、全量 `318`、mypy、
  Ruff、CLI、lock/sync、offline build 与 migration package inclusion 全 PASS；
  直接依赖锁定为 OpenAI `2.46.0`、tiktoken `0.13.0`。这些仅是待独立复跑的实现
  证据，不构成 `APPROVE`。
- TASK-008A 第一轮独立 Reviewer evidence
  `0f52c3056379bcfcd9b7bb0805ccdb5dba99a9dd` 是 implementation 的唯一子提交且只
  修改 handoff，Verdict=`REJECT`、P1=6：审计哈希形状、语义空白、ConfigError
  traceback locals、tokenizer 网络回退、OpenAI SDK 导入时环境读取和完成结果元数据
  一致性未关闭。既有 contracts `66`、全量 `318` 和其他离线门禁通过不抵消这些
  P1。Correction 1 按 A-16/A-17 修复后必须由全新独立 Reviewer 再审。
- TASK-008A Correction 1 `d95745fd04b115369a9fd70362cd735d1eb70917` 是 first review
  evidence 的唯一非 merge 后继，精确修改 `domain.py`、`config.py`、contracts 测试、
  固定 `o200k_base.tiktoken` 资源和 handoff 五个路径；相对 original base 的完整产品
  Diff 为获准的八路径，`pyproject.toml`/`uv.lock` blob 未变。Implementer 自报
  contracts `72`、全量 `324`、mypy、Ruff、CLI、locked offline sync/build、资源与
  migration package hash 全 PASS；六个 P1 的 RED/GREEN 仅构成待第二轮独立复跑证据。
- TASK-008A 第二轮独立 Reviewer evidence
  `7a8239f3da02fa204b63702677fae5f669fb99c0` 是 Correction 1 的唯一子提交且只修改
  handoff，Verdict=`APPROVE`、P0/P1/P2/P3 均无：contracts `72`、全量 `324`、mypy、
  Ruff、CLI、locked offline sync/build、migration/BPE source/sdist/wheel hash、固定
  Diff 和 A-F 独立探针均 PASS。真实 API/密钥/云调用/Vault/媒体/模型仍未授权，不作为
  离线共享契约拒绝理由。
- TASK-008A 已由 Codex Product Integrator 以 merge commit
  `64a9c41683bb559b27bebb784fcff4fbff644a18` 整合到 main：双父精确为
  `d00841802ef375170542e7458ecba0504b6fd182` 与
  `7a8239f3da02fa204b63702677fae5f669fb99c0`，first-parent Diff 精确为八个批准路径。
  locked offline sync、contracts `72`、全量 `324`、mypy、Ruff、CLI、offline build、
  migration/BPE source/sdist/wheel 包含性、BPE `3,613,922` bytes/SHA-256 与敏感扫描均
  PASS；未 push。BPE 文件级 NOTICE/license 仍由 TASK-014 release gate 复核。
- 真实 OpenAI API、密钥读取、付费调用、云端 token-count、真实 Vault/用户笔记和
  最终文件删除/移动/重命名继续未授权。

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
