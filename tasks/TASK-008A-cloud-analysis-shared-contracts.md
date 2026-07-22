# TASK-008A：云分析共享契约与依赖基线

- Status: `DONE`
- Assignee: `Codex`
- Reviewer: `第二轮全新独立 Codex APPROVE；已整合并关闭`
- Owner role: Codex Implementer + 全新独立 Codex Reviewer
- Size: M
- Risk: High
- Depends on: TASK-007
- Decision gate: ADR-008 A-01 至 A-15 已于 2026-07-20 批准；A-16/A-17 已于
  2026-07-21 补充批准
- Resource gate: `openai`/`tiktoken`、必要传递依赖、网络包下载、锁文件和本卡
  离线命令已批准；Correction 1 另获一次固定 OpenAI BPE Blob 下载授权

## 2026-07-20 正式分配

- Base：`main@82d1fd7c7f2f82e77df0518e63755bad0bf240f2`
- Worktree：`/Users/hua/Documents/yia-worktrees/task-008a`
- Branch：`codex/task-008a-cloud-analysis-shared-contracts`
- Implementer：Codex；Reviewer：实现提交后启动全新独立 Codex 会话
- 完整产品 Diff：原实现只允许本卡“预计触达文件”的 7 个路径；Correction 1 获准
  新增固定 tokenizer 资源后，完整范围扩展为 8 个路径
- 并行边界：TASK-009A、TASK-008、TASK-009 均继续 `BLOCKED/UNASSIGNED`；不得
  并发修改 `domain.py`、`pyproject.toml` 或 `uv.lock`

## 2026-07-20 实现证据与审查授权

- Implementation source：
  `382251298af7fcbfadba66c1902af6de0a425179`；唯一父提交为固定 base。
- 完整产品 Diff 精确为本卡 7 个批准路径；无 Provider、Prompt、
  Schema/migration、`state.py`、`complete_stage`、CLI 或任务状态改动。
- Implementer 自报 contracts `66 passed`、全量 `318 passed`、mypy、Ruff、CLI、
  lock/sync、offline build 和 migration package inclusion 全 PASS；这只构成待
  Reviewer 独立复跑的实现证据。
- 直接依赖锁定为 OpenAI `2.46.0`、tiktoken `0.13.0`；既有直接依赖未升级。
- 状态进入 `IN_REVIEW`；Reviewer 包已准备，但 Reviewer 尚未启动，不得预写
  `APPROVE`、`ACCEPTED`、merge 或 `DONE`。

## 2026-07-21 第一轮独立审查与 Correction 1

- Reviewer evidence：
  `0f52c3056379bcfcd9b7bb0805ccdb5dba99a9dd`；唯一父提交为 implementation
  `382251298af7fcbfadba66c1902af6de0a425179`，且只修改
  `handoffs/TASK-008A.md`。
- Reviewer 独立复跑 contracts `66 passed`、全量 `318 passed`、mypy、Ruff、CLI、
  lock/offline sync/build、migration package inclusion 与固定 Diff 均 PASS；这些
  不能抵消以下 6 个 P1。
- Verdict=`REJECT`：三处审计哈希未限制为 64 位小写 SHA-256；多个出站/grounding
  字段接受纯空白；`ConfigError` traceback frame locals 保留 secret sentinel；
  `o200k_base` 空 cache 会网络下载；主进程 `import openai` 会读取
  `AZURE_OPENAI_AD_TOKEN`；`AnalysisCompleted` 允许 result/call provider/model
  矛盾。
- 产品负责人批准 ADR-008 A-16/A-17 和 Correction 1：原 Codex Implementer 从
  reviewer evidence 继续，只修复上述 6 个 P1。相对 reviewer evidence 的 Correction
  与相对 original base 的完整产品范围都只能属于原 7 路径加
  `src/youtube_intel/resources/o200k_base.tiktoken`。
- A-16 只允许一次无认证 OpenAI 官方 Blob GET；资源 SHA-256 必须为
  `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`，并进入
  sdist/wheel。运行时只读本地资源，缺失/篡改/解析失败均 fail-closed，禁止网络
  fallback。文件级分发许可继续由 TASK-014 复核。
- A-17 禁止主进程导入 OpenAI SDK。TASK-008A 只用合成哨兵离线验证清空/白名单化
  子进程导入策略；TASK-008 后续才实现导入完成后的匿名管道密钥传输和 Provider。
- 状态退回 `IN_PROGRESS`；第一轮 Reviewer 已结束，下一 Reviewer 尚未启动。

## 2026-07-22 Correction 1 实现证据与第二轮审查授权

- Correction 1 source：`d95745fd04b115369a9fd70362cd735d1eb70917`；唯一父提交为
  first review evidence `0f52c3056379bcfcd9b7bb0805ccdb5dba99a9dd`，source 干净。
- Correction Diff 精确为 `domain.py`、`config.py`、contracts 测试、固定 tokenizer
  resource 和 handoff 五个路径；完整产品 Diff 相对 original base 精确为获准八路径。
  `pyproject.toml` 与 `uv.lock` blob 均与 reviewed implementation 保持一致。
- A-16 资源为 `3,613,922` bytes，SHA-256
  `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`；Implementer
  自报 source/sdist/wheel 一致，空 cache/socket/HTTP 拒绝下本地 loader 成功，缺失、
  篡改、错误 hash 和解析失败均 fail-closed。
- A-17 自报产品源码和 pytest 主进程均无 OpenAI 导入；SDK 只在绝对 Python executable
  和三个固定环境变量的新建子进程中离线导入，合成 OpenAI/Azure/代理/凭据变量未继承。
  未实现 Provider 或匿名密钥管道。
- Implementer 自报六个 P1 的独立 RED `6 failed` -> GREEN `6 passed`；contracts
  `72 passed`、全量 `324 passed`、mypy、Ruff、CLI、lock check、locked offline sync、
  offline build、migration/BPE package checks 和固定 Diff 均 PASS。这些是待独立复跑
  的证据，不构成 `APPROVE`。
- 状态进入 `IN_REVIEW`；第二轮全新独立 Codex Reviewer 包已准备但尚未启动，不得预写
  `APPROVE`、`ACCEPTED`、merge 或 `DONE`。

## 2026-07-22 第二轮独立审查、验收与整合授权

- Reviewer evidence：`7a8239f3da02fa204b63702677fae5f669fb99c0`；唯一父提交为
  Correction 1 source `d95745fd04b115369a9fd70362cd735d1eb70917`，且只修改
  `handoffs/TASK-008A.md`。
- Reviewer 独立复跑 contracts `72 passed`、全量 `324 passed`、mypy、Ruff、CLI、
  locked offline sync/build、migration/BPE source/sdist/wheel hash 和固定 Diff；六组
  P1 探针 A-F 均 PASS。
- Verdict=`APPROVE`，P0/P1/P2/P3 均无。六个先前 P1 已关闭：hash 表示、语义空白、
  完整 ConfigError 脱敏图、BPE 本地只读/无网络回退、SDK 白名单子进程隔离导入和
  `AnalysisCompleted` 元数据一致性。
- 主控验收：`ACCEPTED`。Product Integrator 仅可按固定 source 执行 non-fast-forward
  merge、全部离线门禁、migration/BPE archive hash、八路径 first-parent Diff 和敏感扫描；
  本卡不得提前写入 merge SHA 或 `DONE`。

## 2026-07-22 整合与收口

- Product Integrator 以 merge commit `64a9c41683bb559b27bebb784fcff4fbff644a18` 整合，父提交顺序为执行基线 `d00841802ef375170542e7458ecba0504b6fd182` 与 accepted source `7a8239f3da02fa204b63702677fae5f669fb99c0`。
- first-parent Diff 精确为八个批准路径；locked offline sync、contracts `72`、全量 `324`、mypy、Ruff、CLI、offline build、sdist/wheel migration 与 BPE 资源核验均 PASS。
- BPE 资源保持 `3,613,922` bytes，SHA-256 为 `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`；文件级 NOTICE/license 复核仍归 TASK-014。
- 最终状态：`DONE`。未推送，source branch/worktree 保留为审计证据；真实 API、密钥、云调用、YouTube/Vault/媒体/模型路径仍未授权。

## 2026-07-20 产品审批

- 批准 `openai>=2.46.0,<2.47`、`tiktoken>=0.13.0,<0.14`、必要传递依赖、网络包
  下载、`pyproject.toml`/`uv.lock` 修改和本卡列出的 uv 离线验证/构建。
- 依赖 TASK-007 已为 `DONE`；本任务已正式分配，并在实现阶段进入
  `IN_PROGRESS`。
- 真实 OpenAI API、环境变量值/密钥、付费调用、云端 token-count 请求、真实 Vault/
  用户内容继续未授权。

## 目标

在不实现云 Provider、不读取密钥、不发起任何云调用的前提下，冻结 TASK-008 和
TASK-009 共同消费的分析输入、结构化完成/跳过结果、配置、隐私、预算和依赖基线。

## 范围

- 新增/收紧不可变具名契约：`AnalysisPayload`、有限 `AnalysisInput`、
  provider-neutral `AnalysisContent`、`AnalysisCompleted`、`AnalysisSkipped`、
  `AnalysisOutcome`、跳过原因和证据来源。
- 所有新增公共契约拒绝未验证 `model_copy(update=...)`；禁止公共自由 `dict`、
  `Any` 和宽 `object`。
- 强化 `AnalysisResult` 的字段种类、非空 evidence 引用和最小化输入精确 grounding
  规则；V1 禁止虚构时间戳。
- 扩展 `CloudSettings`：本地 28k token 发送上限、30k Provider 上限、描述/输出
  上限（输出默认 4,000、范围 `256..8,000`）、Prompt/Schema/采样/隐私版本及
  显式 tokenizer 支持边界；V1 不发送 temperature。
- 把 `openai>=2.46.0,<2.47`、`tiktoken>=0.13.0,<0.14` 作为显式直接依赖解析和
  锁定；验证版本、许可证、Python 3.12/arm64 的隔离子进程导入和现有依赖不被意外
  升级。
- 把 OpenAI 官方 `o200k_base.tiktoken` 作为固定包内资源，验证 SHA-256、打包、
  本地读取和无网络回退；冻结 OpenAI SDK 的隔离子进程导入/匿名管道密钥策略。
- 只补契约/配置测试，不实现采样函数、CredentialResolver、CloudCallBudget、
  OpenAI Adapter、Prompt、缓存或事务编排。

## 范围外

- 不读取任何环境变量值、密钥、凭据或真实配置。
- 除 A-16 固定 BPE 资源的一次无认证 GET 外，不调用 OpenAI、token-count endpoint
  或任何网络 API。
- 不实现 `analysis.py`、`providers/cloud_llm.py`、Prompt 或 TASK-010 编排。
- 不新增 Schema/migration，不修改 `state.py`、`complete_stage` 或 CLI。
- 不访问真实 YouTube、字幕、Vault、媒体、模型或用户数据。

## 验收标准

- [ ] 完成/跳过 union、最小化 payload、证据约束和 `model_copy` 安全边界均有正反
  契约测试。
- [ ] 云设置默认关闭；model/tokenizer/28k/30k/描述/输出/版本边界和未知字段拒绝
  均可验证，错误/`repr` 不泄露敏感值。
- [ ] `AnalysisPayload` 的可序列化字段精确等于 ADR-008 A-04 白名单，不能携带
  路径、内部 ID、哈希、评分维度或自由 metadata。
- [ ] 依赖精确落在批准范围；OpenAI 只在白名单环境的独立子进程离线导入，tiktoken
  只消费本地资源；现有直接依赖不被升级，无 API 调用或凭据读取。
- [ ] 三处审计哈希只接受 64 位小写 SHA-256；所有语义非空的出站/grounding/provider/
  model 字段拒绝纯空白；`AnalysisCompleted` 强制 result/call provider/model 一致。
- [ ] secret-shaped YAML 在异常、cause/context、Pydantic errors、traceback 和所有
  项目 frame locals 中不可见。
- [ ] 固定 `o200k_base.tiktoken` 资源哈希正确且进入 sdist/wheel；空 cache、socket
  拒绝、资源缺失/篡改探针证明无网络 fallback 并安全失败关闭。
- [ ] 主进程不导入 OpenAI SDK；隔离导入测试使用新建白名单环境和合成哨兵，证明
  OpenAI/Azure/代理/凭据变量未被继承或读取。TASK-008 的匿名管道 Provider 不在本卡
  实现。
- [ ] 无 Schema、Repository、Provider、Prompt 或产品编排行为。

## 验证

- [ ] `uv lock --check`
- [ ] `uv sync --locked --offline`
- [ ] `uv run python -m pytest tests/unit/test_contracts.py`
- [ ] `uv run python -m pytest`
- [ ] `uv run mypy src`
- [ ] `uv run ruff check .`
- [ ] `uv run python -m youtube_intel --help`
- [ ] `uv build --offline`
- [ ] `git diff --check <base>...HEAD`
- [ ] 人工审计：无 API/密钥/Provider/Schema/state 写入；sdist/wheel 仍包含 migration。

## 预计触达文件

- `src/youtube_intel/domain.py`
- `src/youtube_intel/config.py`
- `config/settings.example.yaml`
- `tests/unit/test_contracts.py`
- `pyproject.toml`
- `uv.lock`
- `handoffs/TASK-008A.md`
- `src/youtube_intel/resources/o200k_base.tiktoken`

若上述文件不足以冻结契约，必须报告 `DECISION NEEDED`，不得自行修改 `state.py`、
Schema、Provider、编排或其他任务文件。

## 复用决定

- `DIRECT`：已批准官方 `openai>=2.46.0,<2.47`、
  `tiktoken>=0.13.0,<0.14`；依赖已锁定，Correction 1 不新增或升级依赖。
- `DIRECT`：OpenAI 官方 `o200k_base.tiktoken` Blob；只允许一次无认证 GET、固定
  SHA-256 和包内只读使用，许可证由 TASK-014 复核。
- `DIRECT`：现有 Pydantic 配置/领域模型、Python 标准库时间/哈希/枚举能力。
- `REJECT/DEFER`：自写 OpenAI HTTP 客户端、第二个云 Provider、token-count 云端
  预检、SDK 自动重试、真实 API/密钥，留给后续明确授权。

## 交付证据

- ADR-008 A-01 至 A-17 追溯表。
- 新增对象/配置的完整正反契约测试和未验证更新探针。
- 依赖解析、tokenizer 资源哈希/打包/无网络回退、SDK 隔离导入、许可证、完整 Diff
  和未触达真实资源声明。
