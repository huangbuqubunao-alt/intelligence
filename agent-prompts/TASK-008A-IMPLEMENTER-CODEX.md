# TASK-008A 云分析共享契约 — Codex Implementer

你是 TASK-008A 的唯一 Codex Implementer。只在指定 source worktree 冻结云分析
共享配置、领域契约和依赖基线；不实现 OpenAI Provider、采样/预算服务、Prompt、
CredentialResolver、编排或任何真实资源路径。

## 固定执行状态

- Main repository：`/Users/developer/Documents/youtubek agent`
- Main assignment authorization：动态运行
  `git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-008A-ASSIGNMENT-INTEGRATOR.md`
- Required assignment parent / source base：
  `82d1fd7c7f2f82e77df0518e63755bad0bf240f2`
- Source worktree：`/Users/developer/Documents/yia-worktrees/task-008a`
- Source branch：`codex/task-008a-cloud-analysis-shared-contracts`
- Required identity：`Mozhu <maintainer@example.invalid>`；
  `user.useConfigOnly=true`

开始前，动态 assignment authorization 必须是 Required assignment parent 的单一
直接后继，main 必须在该 authorization commit 且干净；main 的 TASK-008A 卡必须是
`IN_PROGRESS/Codex`。source branch/HEAD 必须精确为 source base，source worktree
必须干净。

**控制面与 source 快照必须区分：**source 从分配前 base 创建，因此 source 内
TASK-008A 卡仍显示 `READY/UNASSIGNED`，这是预期冻结快照，不是阻塞；实时分配事实
只以 main 的 assignment commit 为准。除该预期差异外，任何基线、父链、身份、分支、
洁净度或范围冲突都必须报告 `BLOCKED`。不得 stash、reset、restore、checkout、
merge、rebase、cherry-pick、pull、清理、修改 main 或自行选择其他 SHA。

## 必读与事实优先级

完整读取：

1. `AGENTS.md`
2. source 的 `docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、
   `docs/PRD.md`、`docs/SYSTEM_DESIGN.md`
3. ADR-002、ADR-005、ADR-008
4. `docs/REUSE_REGISTER.md`
5. `tasks/TASK-008A-cloud-analysis-shared-contracts.md`
6. `handoffs/TEMPLATE.md`
7. 本 Implementer 包

另从 main 读取 assignment authorization、TASK-008A 卡和 Project Status，以确认
实时控制面。代码定位优先使用 Codebase Memory 图谱；若仓库未索引则先索引，再定位
现有 `CloudSettings`、`AnalysisInput`、`AnalysisResult`、证据对象和公共 Pydantic
安全模式。图谱不足时只读精确文件。

若 ADR-008、System Design、现有公共契约或任务卡冲突，报告 `DECISION NEEDED`；
不得自行扩大字段、依赖、Schema 或文件范围。

## 唯一允许修改的路径

1. `src/youtube_intel/domain.py`
2. `src/youtube_intel/config.py`
3. `config/settings.example.yaml`
4. `tests/unit/test_contracts.py`
5. `pyproject.toml`
6. `uv.lock`
7. `handoffs/TASK-008A.md`

相对 source base 的完整 Diff 只能属于以上 7 个路径。禁止修改 `state.py`、
`migrations/**`、`complete_stage`、任何 Provider、`analysis.py`、Prompt、CLI、
其他测试、任务/ADR、main 或 TASK-009A 文件。不得创建业务模块或读取真实配置。

## 实现契约

### 领域对象

- 新增/收紧不可变具名 `AnalysisPayload`、有限 `AnalysisInput`、
  provider-neutral `AnalysisContent`、`AnalysisCompleted`、`AnalysisSkipped`、
  `AnalysisOutcome`、固定跳过原因和证据来源。
- 所有本任务新增公共 Pydantic 对象必须拒绝未验证
  `model_copy(update=...)`，同时保留合法无 update 的 frozen copy；不得使用公共
  自由 `dict`、`Any`、宽 `object`、`cast` 或 `type: ignore` 绕过契约。
- `AnalysisPayload` 的可序列化字段必须精确等于 ADR-008 A-04 白名单；路径、
  Vault/用户内容、内部 ID/哈希、诊断、评分维度、密钥名称和自由 metadata 必须在
  类型和序列化探针中都不可进入。
- `AnalysisPoint` 的种类、每项非空 evidence 引用、`EvidenceExcerpt` 来源和精确
  grounding 所需字段按 A-10/A-11 冻结；V1 时间字段必须为空。模型不能生成本地
  provider/model/prompt/request hash/call metadata。
- 不实现采样、token 计数、请求构造、CredentialResolver、CloudCallBudget、
  Adapter、Artifact/Provider-call 或事务行为；只冻结后续任务可直接消费的公共面。

### 配置

- 云端默认关闭；V1 provider 只接受 `openai`。冻结 model、api-key env 名、5 次
  run 上限、本地 28,000、Provider 30,000、描述 4,000、输出默认 4,000/
  `256..8,000`、120 秒 timeout 和 Prompt/Schema/采样/隐私版本。
- 模型与 tokenizer 必须使用显式支持关系；未知映射失败关闭。配置只保存环境变量
  名，不解析值；错误、`repr`、测试快照和交接不得出现真实或哨兵 secret 值。
- `config/settings.example.yaml` 只能使用无密钥、无真实路径示例；不得新增真实
  Provider 可用性探针或读取进程环境。

### 依赖与复用

- `DIRECT`：官方 `openai>=2.46.0,<2.47`（Apache-2.0）和
  `tiktoken>=0.13.0,<0.14`（MIT），以及 uv 解析出的必要传递依赖。
- 可使用 `uv add 'openai>=2.46.0,<2.47' 'tiktoken>=0.13.0,<0.14'` 完成清单与
  锁定；只允许包索引/包下载，不允许 API、token-count 或其他网络路径。
- 验证 Python 3.12/arm64 导入和许可证元数据，确认既有直接依赖未被范围外升级。
- `REJECT/DEFER`：手写 OpenAI HTTP、Chat Completions、第二 Provider、云端
  token-count、SDK 自动重试、真实 API/密钥、Prompt/Schema 运行实现。

## 测试和安全要求

- 按 TDD 先补失败的正反契约测试，再做最小实现；不得删除、跳过、弱化既有测试或
  修改门禁掩盖失败。
- 测试必须覆盖完成/跳过 union、固定原因、payload 白名单、跨字段/基数/evidence、
  未验证 update、默认关闭、边界值、未知字段/model/tokenizer、secret 哨兵、
  `repr`/异常脱敏和依赖离线 import。
- 不得实例化真实 OpenAI client，不得读取 `OPENAI_API_KEY` 或任何环境变量值，不得
  monkeypatch 出“看似真实”的付费路径；测试只能验证纯配置/领域/导入。

## 必须运行的检查

```bash
uv lock --check
uv sync --locked
uv run python -m pytest tests/unit/test_contracts.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
uv build --offline
git diff --check 82d1fd7c7f2f82e77df0518e63755bad0bf240f2...HEAD
```

首次依赖解析/同步允许已批准的包索引与包下载；完成锁定后其余验证应离线。构建必须
证明 sdist/wheel 仍包含 `youtube_intel/migrations/001_initial.sql`；只清理本轮生成
且被忽略的 `dist/`。必须复核 `pyproject.toml`/`uv.lock` 只包含批准的直接范围与必要
传递变化，不得顺带升级无关直接依赖。

提交前检查完整 Diff、禁止路径、敏感字面量和所有证据。按 `handoffs/TEMPLATE.md`
创建交接，记录 ADR-008 A-01 至 A-15 追溯、依赖/许可证、实际检查、Diff、跳过项和
风险。创建一个新的非 merge commit，唯一父提交必须为 source base；不得 amend。

## 完成报告

```text
Task: TASK-008A
Role: Implementer
Branch/worktree:
Base commit:
Head commit:
Changed files:
Acceptance criteria:
Checks:
Dependency lock summary:
ADR-008 traceability:
Reuse/license:
Diff review:
Skipped checks:
Remaining risks:
Decision needed:
```

建议状态只能是 `IN_REVIEW` 或 `BLOCKED`。不要自行启动 Reviewer、修改 main 任务
状态、合并、push 或清理 worktree。
