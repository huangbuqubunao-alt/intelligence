# TASK-007：Ollama 本地评分

- Status: `DONE`
- Assignee: `Codex`
- Owner role: 已整合并关闭（merge `3d49ec...`）
- Size: M
- Risk: Medium
- Depends on: TASK-005A

## 2026-07-16 只读预检

- Scout observed main：`b335b12358bbbc9dada1abfafc5a2fe9a68494be`
- Repository changes：None
- 结论：`DECISION NEEDED`
- ADR-007 L-01 至 L-15 已于 2026-07-17 接受；本任务仍为 `BLOCKED/UNASSIGNED`，
  不得创建 worktree、安装 Ollama 或拉取模型。
- 共享配置、采样、决策对象与评分摘要原子持久化必须先由 TASK-005A 整合为 `DONE`；
  TASK-007 继续不修改依赖或锁文件。Ollama 安装/启动、模型拉取与本机文本冒烟仍须
  独立任务级授权。

## 2026-07-19 离线实现分配与边界

- Main control-plane base：`6b4d59c882ccdcbd0e5a6069a6661e0672921a80`。worktree：
  `/Users/hua/Documents/yia-worktrees/task-007`；branch：
  `codex/task-007-local-scoring`；Implementer：Codex；完成后由全新独立 Codex
  Reviewer 审查。
- 仅允许本卡“预计触达文件”列出的 `scoring.py`、`providers/ollama.py`、
  `prompts/scoring.md`、两份测试、`tests/fixtures/scoring/**` 和
  `handoffs/TASK-007.md`。复用 Python 标准库 HTTP/JSON 与既有锁定依赖；不得修改
  `pyproject.toml`、`uv.lock`、Schema/migration、共享 `config.py`/`domain.py`/`state.py`
  或任务状态。
- 所有验证必须离线：允许 Fake transport/本地测试替身，不得请求实际 `127.0.0.1:11434`
  或任何外部地址。若环境缺少已锁定包，只允许 `uv sync --locked --offline`；它失败时停止，
  不得联网补包。
- 继续禁止：Ollama 安装或启动、`qwen3:8b` 拉取、真实模型/服务调用、cloud tag、模型
  下载、媒体/YouTube、Cookie/登录、remote components、ffmpeg、真实 Vault/密钥或文件
  删除。真实文本冒烟属于后续单独授权。

## 实现证据与独立审查授权

- Source：`codex/task-007-local-scoring@258358fcd5227e144c9294beafdf7ec6e2feea63`；
  唯一父提交为共同 base `6b4d59c882ccdcbd0e5a6069a6661e0672921a80`，worktree 已干净。
- base...source 精确包含本卡允许的 7 个路径组、共 11 个文件：`scoring.py`、
  `providers/ollama.py`、`prompts/scoring.md`、两份测试、5 个评分夹具和 handoff。
  `pyproject.toml` 与 `uv.lock` 无差异，`git diff --check` 通过。
- Implementer 自报评分单测 `4`、Fake Ollama 集成 `6`、全量 `261`、mypy、Ruff、CLI、
  离线 sync/build 和 migration packaging 全部通过；这些只构成待复跑证据，不构成验收。
- Reviewer：必须为全新独立 Codex 会话，仅可在 source worktree 的
  `handoffs/TASK-007.md` 追加审查并创建一个以 `258358f...` 为唯一父提交的 evidence
  commit。不得改业务代码、测试、依赖、锁文件、任务状态或 main；审查包由动态 main
  commit 解析。不得读取、检查或操作 TASK-006 worktree。

## 目标

使用可配置的 Ollama Provider 对元数据和规范文本做本地价值评分，严格解析结构化结果，并由应用策略决定是否进入深度分析。

## 范围

- 实现评分输入采样、Prompt 版本、Provider 调用、Schema 校验和一次格式修复。
- 记录总分、理由、主题、建议值、应用阈值结果和不一致诊断。
- 建立输入/模型/Prompt/Schema 版本感知的评分缓存。

## 范围外

- 不调用云端模型。
- 不写 Obsidian 或周报。
- 不把模型输出直接当可信对象或让模型绕过配置阈值。
- 不自动安装/启动 Ollama、不自动拉取模型、不访问 cloud tag 或远程地址。

## 验收标准

- [ ] 固定响应覆盖合法评分、越界分数、缺字段、非法 JSON、修复成功和修复失败。
- [ ] 字幕采样覆盖开头/正文/结尾且受长度限制；同一规范输入重复评分命中缓存。
- [ ] `should_summarize` 的最终值由批准阈值策略决定，模型建议冲突会被记录。

## 验证

- [ ] `uv lock --check`
- [ ] `uv run python -m pytest tests/unit/test_scoring.py`
- [ ] `uv run python -m pytest tests/integration/test_ollama_provider.py`
- [ ] `uv run mypy src`
- [ ] `uv run ruff check .`
- [ ] `uv build`
- [ ] `git diff --check`
- [ ] 可选本地冒烟：对一个固定文本运行已批准模型，记录模型名、版本、耗时和结构化结果，不记录全文。

## 预计触达文件

- `src/youtube_intel/scoring.py`
- `src/youtube_intel/providers/ollama.py`
- `prompts/scoring.md`
- `tests/unit/test_scoring.py`
- `tests/integration/test_ollama_provider.py`
- `tests/fixtures/scoring/**`
- `handoffs/TASK-007.md`

本任务使用 Python 标准库 HTTP，不新增 `httpx`/Ollama SDK，不修改
`pyproject.toml`/`uv.lock`。共享 `config.py`、`domain.py`、`state.py`、示例配置和
既有契约/状态测试必须由 TASK-005A 先行完成。

## 交付证据

- 测试和可选冒烟结果。
- Prompt/Schema 版本示例。
- 黄金样例人工评分偏差说明。
- Ollama 版本、模型 tag/digest/许可证、Fake HTTP、安全读取和 no-cloud 边界证据。

## 第一轮独立审查拒绝与 Correction 1

- 第一轮审查证据：`266c488c17fc82cb648053b5e1066211a7bea9a9`；唯一父提交为原实现
  `258358fcd5227e144c9294beafdf7ec6e2feea63`，且仅修改 `handoffs/TASK-007.md`。
- Verdict：`REJECT`；P0=0、P1=2、P2=0、P3=0。审查已独立复跑 lock/sync、评分测试、全量
  测试、mypy、Ruff、CLI、离线构建、迁移包内容和完整 Diff；真实 Ollama/模型/媒体/Vault
  路径均未运行。
- P1-1：`providers/ollama.py` 的异常边界会让修复响应正文经 cause/context/traceback 可达；
  `http.client.IncompleteRead`、缺失/超长 `response` 等路径也可能以私有异常逃逸，而非返回
  具名、脱敏、含请求视频身份的应用错误。
- P1-2：`scoring.py` 仅有进程内缓存，未把 `SCORING_RAW`、`SCORING_STRUCTURED`、Provider
  Call、`ScoringSummaryWrite`、Pipeline CAS 与 Job 成功放在已有 `complete_stage` 的同一
  SQLite 事务中，因此成功评分既不可持久恢复也不能保证状态真实。

### Correction 1 的冻结边界

- 起点必须是上述 review evidence；Correction commit 必须以它为唯一父提交。只允许修改：
  `src/youtube_intel/scoring.py`、`src/youtube_intel/providers/ollama.py`、
  `tests/unit/test_scoring.py`、`tests/integration/test_ollama_provider.py`、必要的
  `tests/fixtures/scoring/**` 和 `handoffs/TASK-007.md`。
- 必须复用已有 SQLite Repository/`ProviderCallRequest`、`ProviderCallCompletion`、
  `ArtifactWrite`、`ScoringSummaryWrite` 与 `complete_stage`；不得修改或绕过
  `state.py`、Schema/migration、`domain.py`、配置、依赖或锁文件，也不得重写现有公共
  Provider 契约。
- 成功路径必须在一个 `TRANSCRIPT_READY -> SCORED` 事务中持久化原始响应
  (`SCORING_RAW`/`RAW_RESPONSE_30D`)、结构化结果
  (`SCORING_STRUCTURED`/`LONG_LIVED`)、成功 Provider Call、最终评分摘要、Pipeline CAS
  和 Job 成功；注入任一后写失败必须全部回滚。相同已验证输入必须复用持久结果，改变
  输入/模型/Prompt/Schema/operation 必须未命中。
- 所有公开评分调用的异常边界必须抑制未受信任正文、URL、Prompt、字幕及本机绝对路径在
  `message`、`__cause__`、`__context__` 或 traceback 中泄漏；短读必须映射为
  `TRANSIENT_NETWORK`，畸形/超限响应映射为安全 `INVALID_RESPONSE`，且只允许一次修复调用。
- 继续只使用 Fake transport 与临时 SQLite；禁止真实 Ollama/网络、安装或启动服务、模型
  拉取、媒体/YouTube、Cookie、ffmpeg、Vault/凭据和文件删除。Correction 完成后必须再次由
  全新独立 Codex Reviewer 审查，Implementer 不得自行改变任务状态、合并或启动 Reviewer。

### Correction 1 实现证据与第二次独立审查

- Correction source：`f46881bc4a8ca0fda4d5ef7006b372bc566cff97`，唯一父提交为第一轮
  review evidence `266c488c17fc82cb648053b5e1066211a7bea9a9`；source worktree 干净。
- Correction 精确修改 `src/youtube_intel/scoring.py`、`src/youtube_intel/providers/ollama.py`、
  `tests/unit/test_scoring.py`、`tests/integration/test_ollama_provider.py` 和
  `handoffs/TASK-007.md`。相对共同 base 的完整产品范围仍为原批准的 11 个文件；
  `pyproject.toml`、`uv.lock` 无差异。
- Implementer 自报完整异常图脱敏、`IncompleteRead`/畸形/超限安全映射、一次 repair、
  repository-backed `SCORING_RAW`/`SCORING_STRUCTURED`、Provider Call、评分摘要、
  `complete_stage` 原子完成、已验证持久缓存和 injected rollback 已有离线回归；它只构成待复跑
  证据，不构成 `APPROVE` 或验收。
- 第二次 Reviewer 必须是全新独立 Codex 会话，只能在 source handoff 写入并创建以
  `f46881bc...` 为唯一父提交的 evidence commit；禁止改业务代码、测试、依赖、锁文件、任务
  状态或 main，也不得访问 TASK-006 worktree。

## 第二次独立审查拒绝与 Correction 2

- 第二次审查证据：`d8eaeabdd2454141eeb646d9254f4a0a24626605`；唯一父提交为
  Correction 1 `f46881bc4a8ca0fda4d5ef7006b372bc566cff97`，且仅修改
  `handoffs/TASK-007.md`。全部规定离线门禁通过，但 Verdict 为 `REJECT`，P0=0、P1=1、
  P2=0、P3=0。
- P1：主结构化响应无效后触发一次修复；若修复仍无效，`OllamaScoringProvider` 丢弃主响应。
  因而 `RepositoryBackedScoringService` 仅记录失败 Provider Call，重排 Job 会再次执行主调用与
  修复，违反 ADR-007 L-09 的“优先复用已保存主响应”恢复要求。

### Correction 2 的冻结边界

- 起点必须是上述审查证据；Correction commit 必须以 `d8eaeab...` 为唯一父提交。只允许修改
  `src/youtube_intel/scoring.py`、`src/youtube_intel/providers/ollama.py`、
  `tests/unit/test_scoring.py`、`tests/integration/test_ollama_provider.py`、必要的
  `tests/fixtures/scoring/**` 和 `handoffs/TASK-007.md`。不得触达 `state.py`、Schema/migration、
  `domain.py`、配置、Prompt、依赖、锁文件、任务状态或 main。
- 当主响应已收到但解析失败且一次修复也失败时，必须在现有请求哈希、确定性 Artifact key、文件
  哈希和 Provider Call 语义内，安全持久化主响应作为 `SCORING_RAW` 恢复输入，并记录可重试失败；
  不得把它伪造成 `SCORING_STRUCTURED`、评分摘要、`SCORED` Pipeline 或成功 Job。
- 同一已验证请求的重排 Job 必须先验证该恢复输入的路径、大小、哈希、Artifact kind、请求/视频/
  Provider/模型/provenance 绑定；验证成功时不得再次发送主评分请求，只允许对已保存主响应执行恰好
  一次修复请求。缺失、篡改或不匹配时必须按既有安全重试语义 fail-closed，绝不能伪造评分或泄漏原文。
- 必须以临时真实 SQLite 和 in-process Fake transport 增加 RED/GREEN 回归：第一次“主响应无效+
  修复失败”后保存恢复输入；第二次仅修复且不重发主请求；第二次修复成功时原子写入 raw/structured
  Artifacts、成功 Provider Call、评分摘要、Pipeline CAS 与 Job；任一数据库写入失败全部回滚。错误图、
  缓存篡改和重复重排不得泄漏正文、Prompt、URL、字幕或绝对路径。
- 继续只允许离线 Fake/临时 SQLite；禁止实际 loopback 或外网 Ollama、模型下载/拉取、安装/启动服务、
  媒体/YouTube、Cookie、ffmpeg、Vault/凭据和文件删除。完成后必须由另一全新独立 Codex Reviewer
  重审；Implementer 不得自行改变任务状态、合并或启动 Reviewer。

### Correction 2 实现证据与第三次独立审查

- Correction source：`567b0f63f9cefc6c8bff43bfea0e9e156ac3a02c`，唯一父提交为第二次 review
  evidence `d8eaeabdd2454141eeb646d9254f4a0a24626605`；source worktree 干净。Correction
  精确修改 `scoring.py`、`providers/ollama.py`、两份既有评分测试和 handoff；共同 base
  `6b4d59c...` 的完整产品范围仍为批准的 11 路径，`pyproject.toml` 与 `uv.lock` 无差异。
- Implementer 自报：主响应无效且修复失败时保存请求绑定的恢复 raw Artifact；重排验证该 Artifact
  后不再 preflight 或主评分、仅执行一次修复；缺失/篡改/模型不匹配安全 fail-closed。离线门禁为
  scoring unit `16`、Fake integration `14`、全量 `281`、mypy、Ruff、CLI、offline sync/build 与
  migration package inclusion 全 PASS；这些只构成待复跑证据，不构成验收。
- 第三次 Reviewer 必须是全新独立 Codex 会话，只能在 source handoff 写入并创建以
  `567b0f...` 为唯一父提交的 evidence commit；禁止改业务代码、测试、依赖、锁文件、任务状态或
  main，也不得访问 TASK-006 worktree。

## 第三次独立审查拒绝与 Correction 3

- 第三次审查 evidence：`1d27d3bdeb8981ca85deaacd5c1cad498ef7a632`，唯一父提交为
  `567b0f63f9cefc6c8bff43bfea0e9e156ac3a02c`，且仅改 handoff。Verdict=`REJECT`，P1=1；
  所有规定离线门禁通过。
- P1：初次主响应/修复失败后，Provider Call 已处于恢复重试语义；若其 recovery Artifact 索引行
  被删除，服务把 `get_artifact_by_key()` 的 `None` 误认为首轮执行并调用主评分。ADR-007 L-09
  要求它安全 fail-closed，绝不得重新 preflight、主评分或修复。

### Correction 3 的冻结边界

- 起点为 `1d27d3b...`，Correction commit 必须以它为唯一父提交。只允许修改
  `src/youtube_intel/scoring.py`、`src/youtube_intel/providers/ollama.py`、两份既有评分测试、
  必要的 `tests/fixtures/scoring/**` 与 handoff；不得改 `state.py`、Schema/migration、domain/config/
  Prompt、依赖/锁、main 或任务状态。
- 必须使用既有 retryable Provider Call 的安全、固定字符串标记与请求哈希/确定性 Artifact key 绑定，
  区分“首轮请求”与“需要 recovery 的重排”。不得把原始响应、Prompt、字幕、URL、路径或密钥写进
  错误/标记。若 recovery-required 标记存在而 Artifact 缺失、索引/文件/哈希/绑定不匹配，必须安全
  `INVALID_RESPONSE` 失败、保留正确的 retry 语义，且零 GET/主评分/修复 transport 调用与零伪造结果。
- 以真实临时 SQLite 和 in-process Fake transport 增加回归：删除 Artifact 索引行、缺失文件和
  provenance 篡改均由 recovery-required retry fail-closed；有效 recovery 仍只修复一次并保持原子
  成功/rollback。不得弱化 present-Artifact、异常脱敏、一次修复或缓存身份测试。
- 继续禁止真实 Ollama/网络/模型、安装/服务、媒体/YouTube、Cookie、ffmpeg、Vault/凭据和文件删除。
  完成后必须再由全新独立 Codex Reviewer 审查；Implementer 不得改变状态、合并或启动 Reviewer。

### Correction 3 实现证据与第四次独立审查

- Correction source：`9da12c2a6932d04b936d6ae1543acb55a72ec9dd`，唯一父提交为第三次 review
  evidence `1d27d3bdeb8981ca85deaacd5c1cad498ef7a632`；source worktree 干净。Correction
  精确修改 `scoring.py`、评分 unit 测试和 handoff，完整 product Diff 仍为批准的 11 路径，依赖/
  锁文件未变。
- Implementer 自报：retryable Provider Call 使用安全、请求绑定 recovery-required 标记；有标记但
  索引/文件/哈希/provenance 不匹配时返回 retryable `INVALID_RESPONSE` 且零 preflight/主评分/修复
  调用；有效 recovery 仍只修复一次并原子完成。focused `17/14`、全量 `282`、mypy、Ruff、CLI、
  offline sync/build 与 migration package inclusion 全 PASS，仅为待复跑证据。
- 第四次 Reviewer 必须是全新独立 Codex 会话，只能在 source handoff 写入并创建以 `9da12c...`
  为唯一父提交的 evidence commit；不得修改业务代码、测试、依赖、锁、任务状态或 main，也不得访问
  TASK-006 worktree。

### Correction 3 第四次独立审查与主控验收

- Review evidence：`95087c115b799d6f4e1e063a0adba0a6d10352ce`，唯一父提交为 `9da12c...`，
  仅修改 handoff。Verdict=`APPROVE`，P0/P1/P2/P3 均无。
- Reviewer 独立复跑 focused `17/14`、全量 `282`、mypy、Ruff、CLI、locked offline sync/build、
  migration package inclusion 与固定 Diff；临时真实 SQLite/Fake transport 证明有效 recovery
  只修复一次、rollback 后可恢复，恢复标记存在时索引/文件/哈希/模型/provenance 任一不匹配皆
  retryable `INVALID_RESPONSE` 且零 transport。
- 主控验收：`ACCEPTED`。允许下一步仅生成 Integrator 包并整合固定 source `95087c...`；不得改
  实现、依赖、锁、Schema、真实资源授权或 TASK-006。

### Product Integrator 结果

- Merge：`3d49ecaf31a4ab800d6a58b5b44f815ab830a06c`，双父为
  `7b33f6fd73ee5ab7019a7647d71a3b5e78b99e35` 与 `95087c115b799d6f4e1e063a0adba0a6d10352ce`。
  first-parent 差异精确为批准的 11 路径，锁文件和依赖无差异；main/source worktree 均干净且 source 保留。
- 整合后 lock/sync offline、focused `17/14`、全量 `282`、mypy、Ruff、CLI、offline build 和
  migration package inclusion 全 PASS。真实 Ollama/模型、网络、媒体、Vault 与凭据路径仍未运行且未授权。
- 已满足 `DONE` 前的整合证据；仅等待 Status Integrator 同步关闭状态，禁止顺便修改产品代码或任务依赖。
