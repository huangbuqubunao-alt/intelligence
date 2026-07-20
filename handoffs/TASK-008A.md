# TASK-008A 交接报告

## 元数据

- Task: `TASK-008A`
- Role: `Implementer`
- Agent/session: `Codex /root`
- Base branch/commit: `main@82d1fd7c7f2f82e77df0518e63755bad0bf240f2`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-008a`
- Branch: `codex/task-008a-cloud-analysis-shared-contracts`
- Head commit: 本报告与实现位于同一个新提交；精确 SHA 由提交后的完成报告记录。
- Started: `2026-07-20`
- Reported: `2026-07-20`

## 目标与范围

- 任务目标：在不实现 Provider、Prompt、采样、token 计数、凭据解析、预算或事务编排的
  前提下，冻结 TASK-008/TASK-009 共用的最小化云分析输入、结构化完成/跳过结果、
  配置、隐私/版本和依赖基线。
- 允许修改：`src/youtube_intel/domain.py`、`src/youtube_intel/config.py`、
  `config/settings.example.yaml`、`tests/unit/test_contracts.py`、`pyproject.toml`、
  `uv.lock` 和本报告。
- 实际修改：仅上述 7 个路径；新增或收紧共享 Pydantic 契约、云配置和正反契约测试，
  并锁定获批的 OpenAI SDK/tiktoken 直接依赖及必要传递依赖。
- 明确未做：未新增 Provider/业务模块、Prompt、Schema/migration、Repository/state、
  CredentialResolver、CloudCallBudget、采样/请求构造、缓存、事务或 CLI 行为；未读取
  环境变量值、实例化 OpenAI client、调用 API、写入 Vault 或访问用户内容。

## 验收证据

| 验收项 | PASS/FAIL/BLOCKED | 证据 |
|---|---|---|
| 完成/跳过 union、最小 payload、证据约束和未验证 update | PASS | `AnalysisCompleted`/`AnalysisSkipped`/`AnalysisOutcome`、五个固定跳过原因、四个固定证据来源、V1 空时间字段、每点非空且有效 evidence 引用、字段种类规则和全套 `model_copy(update=...)` 拒绝探针；无 update 的 frozen copy 保持合法。 |
| 云配置默认关闭及所有固定边界 | PASS | `CloudSettings` 固定 openai、显式 model/tokenizer 映射、5 次、28k/30k、描述/输出边界、四个版本和既有 120 秒 timeout；未知 model/tokenizer/字段及跨预算错误均失败关闭。 |
| `AnalysisPayload` 精确出站白名单 | PASS | JSON 序列化键精确等于 10 个 A-04 字段；`extra="forbid"` 排除路径、内部 ID/哈希、评分、密钥名和自由 metadata；描述对象上限为 4,000 code points。 |
| 依赖、离线导入、许可证和既有依赖稳定 | PASS | 直接范围精确为 `openai>=2.46.0,<2.47` 与 `tiktoken>=0.13.0,<0.14`；锁定/离线导入为 2.46.0/0.13.0；Python 3.12.11、arm64；既有直接依赖未升级。 |
| 无 Provider/Schema/Repository/Prompt/编排行为 | PASS | 完整 Diff 仅 7 个获准路径；源码静态测试证明 `domain.py`/`config.py` 不导入 OpenAI 或 tiktoken，配置不导入 `os`；无禁止路径变化。 |

## ADR-008 A-01 至 A-15 追溯

| 决策 | 本切片证据或明确边界 |
|---|---|
| A-01 共享契约先行 | 本提交只冻结具名契约、配置和依赖，不实现云 Provider 或业务编排。 |
| A-02 完成/跳过显式 union | `AnalysisCompleted`、`AnalysisSkipped`、`AnalysisOutcome` 和五个固定跳过原因均有正反测试。 |
| A-03 资格与副作用顺序 | 本切片不实现副作用；有限 `AnalysisInput` 和结构化跳过面供 TASK-008/TASK-010 按固定顺序消费。 |
| A-04 专用最小出站对象 | `AnalysisPayload` 只有 video/title/channel/time/duration/language/description/sample 共 10 个具名字段；`AnalysisInput` 将 payload 与本地哈希/版本隔离。 |
| A-05 本地保守 token 预算 | 配置冻结 `o200k_base` 显式模型映射、28,000 本地上限、30,000 Provider 上限和 `cloud-token-sampling-v1`；采样/计数实现留给 TASK-008。 |
| A-06 完整请求身份 | `AnalysisInput` 冻结 transcript/request hash 与 Prompt/Schema/采样/隐私版本；实际哈希构造和缓存匹配留给 TASK-008。 |
| A-07 按真实出站请求计预算 | 配置上限固定为 5；未实现或伪造预算计数，`CloudCallBudget` 留给 TASK-010。 |
| A-08 注入且延迟读取密钥 | 配置只存经验证的 env 名；不读取进程环境，repr/异常脱敏测试覆盖 secret 哨兵。 |
| A-09 固定 OpenAI 传输边界 | 仅加入官方 SDK 依赖；未实例化 client、未实现 Responses API、重试、temperature 或网络行为。 |
| A-10 严格 Structured Outputs | provider-neutral `AnalysisContent` 不能生成 provider/model/prompt/request/call metadata；本地 `AnalysisResult` 才增加可信审计字段。Adapter 和 JSON Schema 留给 TASK-008。 |
| A-11 最小输入可验证证据 | 来源精确映射到 title/channel_name/description/transcript_sample，时间字段只能为 `None`，所有 point 必须引用存在的 evidence，种类规则固定；运行时精确子串核验留给 TASK-008 Adapter。 |
| A-12 复用现有事务 | 未改 Artifact、Provider call、`complete_stage`、Schema、migration 或 `state.py`；持久化编排留给 TASK-008/TASK-010。 |
| A-13 依赖与并行隔离 | 本任务独占修改清单/锁文件，锁定 OpenAI 2.46.0、tiktoken 0.13.0 和必要传递依赖；未触及 TASK-009A/Jinja2。 |
| A-14 离线隐私/预算验收 | 本切片覆盖白名单、secret 脱敏、支持/未知 tokenizer、28k/30k 及配置边界；Provider/Fake/SQLite 场景属于后续实现验收。 |
| A-15 真实云路径单独授权 | 未读取密钥、未发送字幕、未调用 OpenAI/YouTube/Vault/媒体/模型；仅使用已批准包索引下载，锁定后验证均无 API 行为。 |

## 版本、复用与许可证

- 固定版本：`analysis-prompt-v1`、`analysis-result-v1`、
  `cloud-token-sampling-v1`、`cloud-privacy-v1`。
- `DIRECT`：既有 Pydantic 2.13.4 不可变/严格模型和 Python 标准库
  `datetime`、`enum`、类型能力；官方 OpenAI SDK 2.46.0（Apache-2.0）与
  tiktoken 0.13.0（MIT）。
- 必要新增传递依赖：distro 1.9.0（Apache-2.0）、jiter 0.16.0（MIT）和
  sniffio 1.3.1（MIT OR Apache-2.0）；其余 OpenAI 依赖已在既有锁图中。
- 既有直接解析版本保持不变：mlx-whisper 0.4.3、Pydantic 2.13.4、
  PyYAML 6.0.3、yt-dlp 2026.7.4；tiktoken 0.13.0 从既有传递依赖提升为显式直接依赖。
- `REJECT/DEFER`：手写 OpenAI HTTP、Chat Completions、第二 Provider、云端 token
  计数、SDK 自动重试、真实 client/API/密钥、Prompt/Schema 运行实现。

## TDD 证据

- RED：新增契约测试依次证明缺少 `AnalysisPayload`/outcome、旧 `AnalysisInput` 形状、
  可写时间戳、未固定 enum、未知 tokenizer、跨预算、YAML 缺字段和缺少直接依赖时失败。
- GREEN：每个最小契约/配置/依赖变化后对应测试通过；最终专项 `66 passed`、全套
  `318 passed`。
- REFACTOR：仅修复 Ruff 导入顺序并复跑专项测试；未删除、跳过、弱化测试或修改门禁。

## 检查结果

| 命令/人工检查 | 结果 | 关键输出或说明 |
|---|---|---|
| `uv lock --check` | PASS | `Resolved 84 packages`。 |
| `uv sync --locked` | PASS | `Resolved 84 packages`，`Checked 61 packages`。 |
| `uv run python -m pytest tests/unit/test_contracts.py` | PASS | Python 3.12.11；`66 passed`。 |
| `uv run python -m pytest` | PASS | `318 passed`。 |
| `uv run mypy src` | PASS | `Success: no issues found in 13 source files`。 |
| `uv run ruff check .` | PASS | `All checks passed!`。 |
| `uv run python -m youtube_intel --help` | PASS | CLI 帮助正常输出。 |
| `uv build --offline` | PASS | sdist 与 wheel 均构建成功。 |
| sdist/wheel 内容检查 | PASS | 两个产物均包含 `youtube_intel/migrations/001_initial.sql`；核验后仅清理本轮生成的忽略 `dist/`。 |
| Python/平台/许可证元数据 | PASS | Python 3.12.11、`arm64`；直接和新增必要传递依赖的许可证元数据均已核验。 |
| `git diff --check` | PASS | 提交前工作 Diff 无空白错误；提交后精确 base range 由完成报告记录。 |

## Diff 复核

- 修改文件：仅任务批准的 7 个路径。
- 是否存在任务范围外修改：否；禁止的 Provider、Prompt、Schema/migration、state、
  Repository、CLI、任务卡、ADR 和 TASK-009A 路径均未修改。
- 是否存在生成文件或格式化噪声：否；`dist/` 只为离线验包生成，已核验并清理。
- 是否触及依赖、Schema、密钥、真实 Vault、云调用或调度红线：只按明确审批修改
  `pyproject.toml`/`uv.lock` 和下载包；未触及其他红线。敏感模式审查只命中既有测试
  脱敏哨兵，未发现凭据、token、私钥或真实绝对路径。

## 失败、跳过与风险

- 已解决失败：沙箱最初拒绝读取用户级 uv 缓存；按门禁授权原命令后锁定、同步、元数据
  和离线构建均成功。依赖许可证测试最初读取了并非两个包都提供的
  `License-Expression` 字段，随后按实际安装元数据改为验证 OpenAI `License` 和
  tiktoken MIT 文本；Ruff 仅报告测试 import 排序，自动排序后所有检查通过。
- 跳过检查及原因：未运行任何真实 OpenAI/API/token-count/网络推理、CredentialResolver、
  环境变量值读取、Provider、Prompt、SQLite/Vault/YouTube/字幕/媒体/模型路径；均为范围外
  或未授权。除已批准依赖下载外无外部网络行为。
- 剩余风险：模型到 tokenizer 的显式表当前只冻结 V1 支持的 GPT-4.1 系列；新增模型必须
  经配置契约变更。精确 evidence 子串验证、请求哈希覆盖、采样/token 计数、SDK 参数、
  错误映射、缓存及持久化原子性仍必须由 TASK-008/TASK-010 的 Fake/临时 SQLite 测试证明。
- `DECISION NEEDED`：`None`。

## 实现者结论

- 建议状态：`IN_REVIEW`
- Commit SHA：见包含本报告的唯一实现提交；精确 SHA 由完成报告记录。
- 复现/验证说明：在本 worktree 从固定 base 执行上表命令；所有测试只验证纯配置、
  领域契约、离线 import 和现有本地代码，未创建 OpenAI client。

## Reviewer 结论

- Reviewer agent/session：
- 审查 commit：
- 重新运行的检查：
- Findings：
- Verdict：`APPROVE | REJECT`
- 未解决 P0/P1：

## 主控验收

- Orchestrator：
- Verdict：`ACCEPT | REJECT`
- 依据：
- 批准整合的 commit：

## 整合结果

- Integrator：
- 主线 commit：
- 整合后检查：
- 最终状态：`DONE | BLOCKED`
