# TASK-008A：云分析共享契约与依赖基线

- Status: `IN_REVIEW`
- Assignee: `Codex`
- Reviewer: `全新独立 Codex，待启动`
- Owner role: Codex Implementer + 全新独立 Codex Reviewer
- Size: M
- Risk: High
- Depends on: TASK-007
- Decision gate: ADR-008 A-01 至 A-15 已于 2026-07-20 批准
- Resource gate: `openai`/`tiktoken`、必要传递依赖、网络包下载、锁文件和本卡
  离线命令已批准；固定实施分配已建立

## 2026-07-20 正式分配

- Base：`main@82d1fd7c7f2f82e77df0518e63755bad0bf240f2`
- Worktree：`/Users/hua/Documents/yia-worktrees/task-008a`
- Branch：`codex/task-008a-cloud-analysis-shared-contracts`
- Implementer：Codex；Reviewer：实现提交后启动全新独立 Codex 会话
- 完整产品 Diff：只允许本卡“预计触达文件”的 7 个路径
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
  锁定；验证版本、许可证、Python 3.12/arm64 导入和现有依赖不被意外升级。
- 只补契约/配置测试，不实现采样函数、CredentialResolver、CloudCallBudget、
  OpenAI Adapter、Prompt、缓存或事务编排。

## 范围外

- 不读取任何环境变量值、密钥、凭据或真实配置。
- 不调用 OpenAI、token-count endpoint 或任何网络 API。
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
- [ ] 依赖精确落在批准范围；`openai`/`tiktoken` 可离线导入，现有直接依赖不被
  升级，无 API 调用或凭据读取。
- [ ] 无 Schema、Repository、Provider、Prompt 或产品编排行为。

## 验证

- [ ] `uv lock --check`
- [ ] `uv sync --locked`
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

若上述文件不足以冻结契约，必须报告 `DECISION NEEDED`，不得自行修改 `state.py`、
Schema、Provider、编排或其他任务文件。

## 复用决定

- `DIRECT`：已批准官方 `openai>=2.46.0,<2.47`、
  `tiktoken>=0.13.0,<0.14`；只可在本任务正式分配后执行安装、下载和锁定。
- `DIRECT`：现有 Pydantic 配置/领域模型、Python 标准库时间/哈希/枚举能力。
- `REJECT/DEFER`：自写 OpenAI HTTP 客户端、第二个云 Provider、token-count 云端
  预检、SDK 自动重试、真实 API/密钥，留给后续明确授权。

## 交付证据

- ADR-008 A-01 至 A-15 追溯表。
- 新增对象/配置的完整正反契约测试和未验证更新探针。
- 依赖解析、许可证、导入、完整 Diff 和未触达真实资源声明。
