# TASK-008：可选云端深度分析

- Status: `DONE`
- Assignee: `Codex`
- Owner role: 实现 Agent + 隐私 Reviewer
- Size: M
- Risk: High
- Depends on: TASK-008A, TASK-009A
- Approval: ADR-008、正式实施范围与离线命令已批准；真实云调用/密钥另批
- Decision gate: ADR-008 A-01 至 A-17 已批准；TASK-008A/TASK-009A 已 `DONE`，本卡已正式分配

## 2026-07-20 只读预检结论

- Read-only Scout 已在 `main@bb9c6b7bb66040b65b091d980f43281c4d9d6ba6`
  完成，仓库无变化；结论为 `DECISION NEEDED`。
- 已批准 `ADR-008` A-01 至 A-15 并建立 `TASK-008A`。TASK-008A 负责公共契约、配置与
  `openai`/`tiktoken` 依赖基线；`TASK-009A` 随后冻结 KnowledgeSink 消费面。
- 两个前置任务均 `DONE` 前，本任务保持 `BLOCKED/UNASSIGNED`。预检不是依赖安装、
  密钥读取、真实 API 调用或实施授权。

## 2026-07-22 正式分配

- Base：`main@473119704c7638d7afd4e68d84d00e85064ceabd`；Worktree：
  `/Users/hua/Documents/yia-worktrees/task-008`；Branch：`codex/task-008-deep-analysis`。
- Codex 为唯一 Implementer；完成后由全新独立 Codex Reviewer 审查。允许范围严格为本卡
  七个路径组；不修改领域/配置契约、`state.py`、Schema/migration、依赖、锁文件、CLI 或任务状态。
- 只授权离线 Fake/合成哨兵和白名单环境隔离子进程 SDK 实现/测试。真实 OpenAI、密钥、
  付费/API 调用、云端 token-count、用户内容、媒体、YouTube 和任何网络路径继续禁止。

## 2026-07-22 实现证据与审查授权

- Implementation source：`10478a9083df4eedae061d99d941c88cb4954179`，唯一父为固定 base
  `473119704c7638d7afd4e68d84d00e85064ceabd`；完整 Diff 落在本卡批准的七路径组内。
- Implementer 自报 full pytest `340`、mypy、Ruff、CLI、lock/sync、offline build、SQLite
  原子成功/回滚、重排零调用与 RAW_RESPONSE_30D 30 天 retention 均 PASS；这些只构成待独立复跑证据。
- 全新独立 Codex Reviewer 仅可向 source handoff 写审查证据，不得改业务代码、依赖、锁文件、main
  或任务状态。TASK-009 继续独立 `IN_REVIEW`，不得被本次审查触碰。

## 2026-07-22 首轮审查拒绝与 Correction 1

- Independent Reviewer evidence：`b61f46f6bca3303d5590aac76d8c8c9b53ec4131`，唯一父为
  implementation `10478a9083df4eedae061d99d941c88cb4954179`，且只修改 source handoff。
- Verdict：`REJECT`，P1=1。`RepositoryBackedAnalysisService` 在持久化分析路径跳过本地 token
  上限门禁；最大输入 token 为 `1` 时，临时 SQLite + Fake Provider/Resolver 仍读取凭据并调用 transport。
- 原 Codex Implementer 只获 Correction 1：`analysis.py`、两份既有分析测试和 handoff。必须在任何凭据、
  Provider/transport 或 Repository 写入前执行同一 token 门禁，并用临时 SQLite + Fake 回归证明超限零调用。
- 真实 OpenAI、密钥、付费/API、网络、云端 token-count、用户内容、媒体、YouTube、Vault、依赖/锁、
  Schema/migration、`state.py`、CLI 与 TASK-009 继续不授权。

## 2026-07-22 Correction 3 实现证据与复审授权

- Correction source：`7a543d0acfe25d1c3d9fd06c4647683ed1487a47`，唯一父为 reviewer-3 evidence
  `b380a8c87d99a3d2dbf88b28bde3ec5b0de4da0f`；Correction 仅修改 `analysis.py`、
  `test_summary_provider.py` 与 source handoff，完整 Diff 仍在原批准范围内。
- Implementer 自报持久化路径按 A-03 处理上游资格、关闭、token/缓存、预算、凭据和预留；关闭、低价值、
  缺凭据零副作用，缓存重排零 credential/transport/新 call/artifact 并可复用成功缓存完成当前 Job；
  focused=`4/14`、full pytest=`345` 与其余离线门禁通过。这些均待独立 Reviewer 4 复跑。
- Reviewer 4 只可追加 source handoff；不得触及真实 OpenAI、密钥、付费/API、网络、云端 token-count、
  Vault、用户内容、媒体、YouTube、TASK-009 或任何范围外索引工件。

## 2026-07-22 第四轮审查拒绝与 Correction 4

- Reviewer 4 evidence：`19323923057adb0b5a9f59cac5eb7c32cce5888a`，唯一父为 Correction 3
  `7a543d0acfe25d1c3d9fd06c4647683ed1487a47`，只修改 source handoff。
- Verdict：`REJECT`，P1=1。缓存恢复只检查成功 ProviderCall 状态，未验证 raw/structured Artifact 的存在、
  元数据/内容 SHA-256，以及恢复结果的 request hash、provider、model 与当前请求一致；篡改 structured
  request hash 仍会推进 Pipeline/Job。违反 ADR-008 A-06。
- 原 Codex Implementer 只获 Correction 4：`analysis.py`、既有分析集成测试与 handoff。恢复只能接受完全
  匹配的成功缓存；任一 Artifact 或 identity 缺失/篡改/不匹配均必须安全失败、零 credential/transport/new
  ProviderCall/Artifact、Pipeline/Job 不变。不得重新发起云调用。完全匹配缓存仍可按 A-12 通过既有
  `complete_stage` 原子恢复当前 Job。

## 2026-07-23 Correction 4 实现证据与复审授权

- Correction source：`bb195a59ddee25cb804b0078676c504e94c44441`，唯一父为 Reviewer 4 evidence
  `19323923057adb0b5a9f59cac5eb7c32cce5888a`；Correction 仅修改 `analysis.py`、
  `test_summary_provider.py` 与 source handoff，完整 Diff 仍在原批准范围内。
- Implementer 自报恢复在 `complete_stage` 前严格验证 ProviderCall identity、两类 Artifact 元数据/文件
  SHA-256 和解析结果 request hash/provider/model；新增十个临时 SQLite/Fake transport 篡改或缺失缓存
  反例，focused=`4/24`、full pytest=`355` 与其余离线门禁通过。这些均待独立 Reviewer 5 复跑。
- Reviewer 5 只可追加 source handoff；不得触及真实 OpenAI、密钥、付费/API、网络、云端 token-count、
  Vault、用户内容、媒体、YouTube、TASK-009 或任何范围外索引工件。

## 2026-07-23 第五轮审查拒绝与 Correction 5

- Reviewer 5 evidence：`78ae101786ada5f04d2b7c734c84a216f8820803`，唯一父为 Correction 4
  `bb195a59ddee25cb804b0078676c504e94c44441`，只修改 source handoff。
- Verdict：`REJECT`，P1=1。隔离 SDK child 在 handshake 与读取 response 时使用无期限 `readline()`；既有
  `wait(timeout=120)` 在读取之后，卡住的 child 会无限阻塞 Job，违反 ADR-008 A-17。
- 原 Codex Implementer 只获 Correction 5：`providers/cloud_llm.py`、既有分析集成测试与 handoff。
  所有 pipe I/O 与 child 退出必须有限时，任一 timeout/EOF/格式或退出错误均要安全映射并 terminate/kill/reap；
  保持 A-17 白名单环境和匿名 credential pipe，不得扩大到真实云端或其他范围。

## 2026-07-23 Correction 5 实现证据与复审授权

- Correction source：`dcbbd38fe8bab79fd6db1679f43a8ca48fb472ea`，唯一父为 Reviewer 5 evidence
  `78ae101786ada5f04d2b7c734c84a216f8820803`；Correction 仅修改 `providers/cloud_llm.py`、
  `test_summary_provider.py` 与 source handoff，完整 Diff 仍在原批准范围内。
- Implementer 自报 handshake、write/flush、response read 与 exit 全部有限时，失败路径关闭 pipe 并有限
  terminate/kill/reap child；离线 Fake child 回归覆盖卡住、EOF、畸形、非零退出与正常 response，focused=`4/30`、
  full pytest=`361` 和其余离线门禁通过。这些均待独立 Reviewer 6 复跑。
- Reviewer 6 只可追加 source handoff；不得触及真实 OpenAI、密钥、付费/API、网络、云端 token-count、
  Vault、用户内容、媒体、YouTube、TASK-009 或任何范围外索引工件。

## 2026-07-23 第六轮独立审查通过与最终整合授权

- Reviewer 6 evidence：`6914312eaac0e3d65f1d2895ea2e3c0c2c39f4d8`，唯一父为 Correction 5
  `dcbbd38fe8bab79fd6db1679f43a8ca48fb472ea`，只修改 source handoff；Verdict=`APPROVE`，P0–P3=0。
- 独立复跑 locked sync、focused=`4/30`、full pytest=`361`、mypy、Ruff、CLI、offline build、sdist/wheel
  prompt/fixed tokenizer/migration inclusion 和完整 Diff 全部通过；A-03、A-06、A-17、成功/回滚/重排/retention
  离线矩阵均通过。真实 OpenAI、凭据、网络、付费、Vault/用户内容继续未运行且未授权。
- TASK-008 现为 `ACCEPTED`；Product Integrator 只获固定 source 的 `--no-ff` 整合和整合后离线门禁，
  不得修代码、改 TASK-009 或写为 `DONE`。

## 2026-07-23 整合与关闭结果

- Codex Product Integrator 已以 merge commit `4f9ca390cdbfb57e6c1e14bf6b900402bd6945f7` 整合 accepted source
  `6914312eaac0e3d65f1d2895ea2e3c0c2c39f4d8`；双父为 `7659943803d0e02799cb835418e4469fb08d52df` 与该 source。
- first-parent Diff 严格为六个授权路径；lock/sync、focused `4/30`、全量 `361`、mypy、Ruff、CLI、离线构建和
  sdist/wheel migration、prompt、固定 tokenizer 大小与 SHA-256 验证全部通过。source 已成为 main 祖先，未 push 或清理。
- 本卡已收口为 `DONE`。真实 OpenAI、凭据、网络、付费调用、Vault/用户内容、媒体与模型路径仍未授权。

## 2026-07-22 Correction 2 实现证据与复审授权

- Correction source：`71e1c24936b0ed1be3a98c49efa7770f7456d85c`，唯一父为 reviewer-2 evidence
  `02317f2bc53f4a7e3dcc5ed7210da74f4129c7bf`；Correction 仅修改 `analysis.py`、
  `test_summary_provider.py` 与 source handoff，完整 Diff 仍在原批准范围内。
- Implementer 自报预算耗尽在 ProviderCall 预留、凭据、Provider/transport 和所有 Repository 写入前返回
  `BUDGET_EXHAUSTED`；临时 SQLite + Fake 回归中 Resolver/transport=0、ProviderCall/Artifact=None、
  Pipeline=`SCORED`、Job=`RUNNING`；focused=`4/11`、full pytest=`342` 与其余离线门禁通过。这些均待
  独立 Reviewer 3 复跑。
- Reviewer 3 只可追加 source handoff；不得触及真实 OpenAI、密钥、付费/API、网络、云端 token-count、
  Vault、用户内容、媒体、YouTube、TASK-009 或任何范围外索引工件。

## 2026-07-22 第三轮审查拒绝与 Correction 3

- Reviewer 3 evidence：`b380a8c87d99a3d2dbf88b28bde3ec5b0de4da0f`，唯一父为 Correction 2
  `71e1c24936b0ed1be3a98c49efa7770f7456d85c`，只修改 source handoff。
- Verdict：`REJECT`，P1=1。持久化路径未在 ProviderCall 预留前统一执行关闭、低价值与缺凭据门禁；
  缺凭据还会将预留 call 标为可重试失败，违反 ADR-008 A-03/A-08 的零副作用与凭据最后读取。
- 原 Codex Implementer 只获 Correction 3：`analysis.py`、两份既有分析测试与 handoff。必须以既有冻结
  契约严格执行高价值/上游有效性、关闭、本地采样-token-缓存、预算、凭据、预留的顺序，并用临时 SQLite +
  Fake 对所有零调用门禁逐项证明无外部或新持久化副作用；缓存重排可按 ADR-008 A-12 复用既有成功
  Artifact/ProviderCall 并以 `complete_stage` 原子推进当前 Job。
- 真实 OpenAI、密钥、付费/API、网络、云端 token-count、用户内容、媒体、YouTube、Vault、依赖/锁、
  Schema/migration、`state.py`、CLI 与 TASK-009 继续不授权。

## 2026-07-22 Correction 1 实现证据与复审授权

- Correction source：`8317cd9c2a13f6c38fa366ab9f40c326e59d8731`，唯一父为首轮 review evidence
  `b61f46f6bca3303d5590aac76d8c8c9b53ec4131`；Correction 仅修改 `analysis.py`、
  `test_summary_provider.py` 与 source handoff，完整 Diff 仍在原批准范围内。
- Implementer 自报持久化路径在 SQLite、凭据和 Provider/transport 之前完成本地 token gate；max token=`1`
  的临时 SQLite + Fake 回归中 Resolver=0、transport=0、无 ProviderCall/Artifact，Pipeline=`SCORED`、
  Job=`RUNNING`；full pytest=`341` 及其余离线门禁通过。这些均待独立 Reviewer 2 复跑。
- Reviewer 2 只可追加 source handoff；不得运行真实 OpenAI、密钥、付费/API、网络、云端 token-count、
  Vault、用户内容、媒体、YouTube 或测试目录外文件操作。

## 2026-07-22 第二轮审查拒绝与 Correction 2

- Reviewer 2 evidence：`02317f2bc53f4a7e3dcc5ed7210da74f4129c7bf`，唯一父为 Correction 1
  `8317cd9c2a13f6c38fa366ab9f40c326e59d8731`，只修改 source handoff。
- Verdict：`REJECT`，P1=1。预算已耗尽时，持久化路径仍创建 `PENDING` ProviderCall 并读取凭据，才返回
  `BUDGET_EXHAUSTED`，违反 ADR-008 A-03/A-07/A-08 的门禁顺序与零副作用。
- 原 Codex Implementer 只获 Correction 2：`analysis.py`、既有分析集成测试和 handoff。必须在 ProviderCall
  预留、凭据解析、Provider/transport 或任何 Repository 写入前返回 `BUDGET_EXHAUSTED`，并用临时 SQLite +
  Fake 回归证明 Resolver/transport/ProviderCall/Artifact 为零且 Pipeline/Job 不变。
- 真实 OpenAI、密钥、付费/API、网络、云端 token-count、用户内容、媒体、YouTube、Vault、依赖/锁、
  Schema/migration、`state.py`、CLI 与 TASK-009 继续不授权。

## 目标

仅对策略允许的高价值视频调用已启用的 OpenAI Adapter，返回经过严格结构与证据
校验的深度分析，并通过稳定请求缓存、调用预算和延迟密钥读取避免重复成本与隐私
泄漏。

## 范围

- 实现本地 `cloud-token-sampling-v1`、规范请求哈希、缓存和 run 预算策略。
- 实现注入式 `CredentialResolver`，只在全部零调用门禁通过后解析环境变量。
- 实现官方 OpenAI Responses Adapter：Structured Outputs、`store=False`、
  `max_retries=0`、一次推理调用、无 tools/stream/custom endpoint。
- 复用既有 Artifact/Provider-call/`complete_stage`，记录安全使用量并支持重排恢复。

## 范围外

- 不在代码、YAML、测试或日志中保存真实密钥。
- 不在开关关闭、低于阈值或预算用尽时发送任何字幕内容。
- 不添加第二个云 Provider，除非另建任务并审批依赖。
- 不修改公共领域/配置契约、Schema、`state.py`、依赖或锁文件。
- 不调用 token-count endpoint，不运行真实 OpenAI 或其他网络路径。

## 验收标准

- [ ] 关闭、低分、缓存、预算耗尽、本地 token 超限和缺凭据均为零调用且按固定顺序
  发生；高价值成功路径只调用一次。
- [ ] 最小化 payload 精确等于 ADR-008 A-04 白名单；未知 tokenizer、28k/30k
  边界、采样和请求哈希具有确定性测试。
- [ ] Structured Outputs 成功、refusal、缺字段、语义/证据错误、限流、5xx、
  timeout 和缓存恢复均映射到冻结结果/错误。
- [ ] Fake transport + 真实临时 SQLite 证明 Artifact、Provider call、Pipeline/Job
  原子完成、回滚与重排不重复付费调用。
- [ ] 隐私 Reviewer 确认 SDK 配置、延迟密钥读取和完整异常图均不泄露密钥、字幕
  全文、响应正文或本地路径。

## 验证

- [ ] `uv lock --check`
- [ ] `uv sync --locked`
- [ ] `uv run python -m pytest tests/unit/test_analysis_policy.py`
- [ ] `uv run python -m pytest tests/integration/test_summary_provider.py`
- [ ] `uv run python -m pytest`
- [ ] `uv run mypy src`
- [ ] `uv run ruff check .`
- [ ] `uv run python -m youtube_intel --help`
- [ ] `uv build --offline`
- [ ] `git diff --check <base>...HEAD`
- [ ] 静态检查：仓库和测试产物不包含真实凭证格式；检查方法由 Reviewer 记录，不输出匹配值。

## 预计触达文件

- `src/youtube_intel/analysis.py`
- `src/youtube_intel/providers/cloud_llm.py`
- `src/youtube_intel/prompts/summary.md`
- `tests/fixtures/analysis/**`
- `tests/unit/test_analysis_policy.py`
- `tests/integration/test_summary_provider.py`
- `handoffs/TASK-008.md`

不包含 `domain.py`、`config.py`、`state.py`、Schema/migration、`pyproject.toml`、
`uv.lock`、CLI、任务状态或 Obsidian 文件。公共契约或依赖不足时必须报告
`DECISION NEEDED`。

## 复用决定

- `DIRECT`：TASK-008A 锁定后的官方 OpenAI SDK 和 tiktoken；本任务只在
  获得正式实施授权后离线导入并使用 Fake transport。
- `DIRECT`：既有 Analysis/Artifact/Provider-call/SQLite/Pydantic 契约。
- `REJECT`：自写 OpenAI HTTP 客户端、第二 Provider、SDK 自动重试、格式修复调用、
  token-count 云端预检和真实密钥/API。

## 交付证据

- Provider/依赖/隐私审批记录。
- ADR-008 A-01 至 A-15 追溯、零调用/缓存/预算/证据/事务测试结果。
- 如未进行真实云端冒烟，必须明确标注；真实冒烟需另获用户授权。
