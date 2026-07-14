# TASK-002：配置与领域契约

- Status: `DONE`
- Assignee: `Grok`
- Reviewer: `Grok`（全新独立会话；`APPROVE`）
- Owner role: 实现 Agent
- Size: M
- Risk: Medium
- Depends on: TASK-001
- Contract: `docs/decisions/ADR-002-config-domain-contracts.md`、`docs/SYSTEM_DESIGN.md` V1.1
- Approval: `APPROVED` — 2026-07-14 产品负责人任务级授权
- Base: `main@46f8497e771e1461034942dd7967f19d85f79f81`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-002`
- Branch: `grok/task-002-config-domain-contracts`

## 目标

把已审批的配置、核心实体、Provider 输入输出和错误分类固化为经过类型与运行时校验的契约，为后续并行开发提供稳定边界。

## 范围

- 实现频道、运行设置、模型、阈值、语言、存储、重试和时区配置 Schema。
- 实现 System Design 中的核心领域对象、Provider 输入输出、三层状态模型和统一错误码。
- 提供无密钥的示例配置，并在启动前报告字段级校验错误。
- 配置优先级固定为默认值 < YAML < CLI，所有层级拒绝未知字段。
- 实现 ADR-002 的精确默认值、数值边界、路径规则、集合基数和稳定排序。
- 使用 `pydantic>=2.13.4,<2.14` 和 `PyYAML>=6.0.3,<7`；只允许 uv 解析出的必要传递依赖，不启用可选 extras。
- YAML 仅使用 `yaml.safe_load` 或等价的 `SafeLoader` 路径，不使用可构造任意 Python 对象的不安全 Loader。

## 范围外

- 不连接 YouTube、Ollama、云模型、SQLite 或 Obsidian。
- 不在配置文件中加入真实密钥或用户真实 Vault 路径。
- 不擅自新增配置项；新增需求先更新 PRD/System Design。
- 不实现字幕采样算法、Provider Adapter、Job 调度或文件写入；本任务只建立契约与纯校验。
- 不新增其他运行时依赖，不调用网络服务，不读取真实密钥，也不接触真实 Obsidian Vault。

## 验收标准

- [ ] 有效示例配置能加载成强类型对象；未知字段、非法阈值、无效时区和越界路径配置会明确失败。
- [ ] `priority=0/100`、阈值 `0/10`、Top N `1/100` 的边界通过，越界值失败；V1 并发值不是 `1` 时失败。
- [ ] 重试、超时、本地评分和云端预算使用 ADR-002 默认值，并验证正数、顺序和上限约束。
- [ ] 项目产物路径拒绝绝对路径和目录逃逸；Vault 根拒绝相对路径，Vault 子目录拒绝绝对路径、`..` 和规范化逃逸。
- [ ] Provider 契约和领域对象不导入任何具体 Provider SDK；公共接口不使用自由形状 `dict`。
- [ ] `ScoreResult` 子维度、`AnalysisResult` 字段、结构化证据及集合基数与 System Design 一致。
- [ ] `PipelineStatus`、`ProcessingStage`、`JobStatus` 相互分离，非法转换被拒绝；失败 Job 不改变视频最近成功阶段。
- [ ] 密钥只表示为环境变量名/引用；对象显示、异常和测试快照不会泄露其值。

## 验证

- [ ] `uv lock --check`
- [ ] `uv sync --locked`
- [ ] `uv run python -m pytest tests/unit/test_contracts.py`
- [ ] `uv run mypy src`
- [ ] `uv run ruff check .`
- [ ] `uv run python -m youtube_intel --help`
- [ ] `git diff --check`
- [ ] 人工检查：用无效阈值和无效时区运行配置加载，错误包含字段路径但不包含密钥值。

## 预计触达文件

- `src/youtube_intel/config.py`
- `src/youtube_intel/domain.py`
- `config/channels.example.yaml`
- `config/settings.example.yaml`
- `tests/unit/test_contracts.py`
- `pyproject.toml`
- `uv.lock`
- `handoffs/TASK-002.md`

## 交付证据

- 测试、类型检查和 Lint 结果。
- 一份脱敏的有效/无效配置输出示例。
- ADR-002 逐项追踪表；任何契约偏离均为 `DECISION NEEDED`，不得由实现者自行调整。

## 任务级批准记录

- Approver: 用户（产品负责人）
- Approved at: 2026-07-14
- Approval: `批准 TASK-002 推荐方案：pydantic>=2.13.4,<2.14、PyYAML>=6.0.3,<7；允许必要传递依赖、网络下载、修改 pyproject.toml/uv.lock，并执行 uv add、uv lock、uv sync 及任务卡验证命令。`
- 允许网络下载：上述两个直接依赖及其由 uv 解析和锁定的必要传递依赖。
- 允许依赖写入：使用 uv 更新 `pyproject.toml`、`uv.lock`，并运行 `uv lock --check`、`uv sync --locked` 和本任务全部验证命令。
- 明确不授权：可选 extras、其他运行时依赖、云调用、真实密钥、真实 Vault、launchd、数据库 Schema 或范围外文件。

## 分配记录

- Assigned at: 2026-07-14
- Implementer: Grok，独占 `/Users/hua/Documents/yia-worktrees/task-002` 的写入权。
- Initial reviewer assignment: Codex；从未启动，后由产品负责人改派为独立 Grok Reviewer。
- Implementer packet: `agent-prompts/TASK-002-IMPLEMENTER-GROK.md`
- Parallel read-only work: `agent-prompts/PREFLIGHT-TASK-003-004-READONLY.md`；不构成后续任务开工授权。

## 主控预审修复轮

- Pre-review at: 2026-07-15
- Reviewed implementation head: `4355a59f6f95e409bcf15b3b8004bb112d0033b3`
- Git evidence: 分支、父提交、单提交范围、8 个允许文件和干净工作树均通过；本轮不否定已通过的依赖与基础检查。
- Initial status decision: 保持 `IN_PROGRESS`，退回原 Grok Implementer；不基于首个实现提交启动 Reviewer。
- Correction packet: `agent-prompts/TASK-002-CORRECTION-GROK.md`

必须关闭的既有契约缺口：

1. `api_key_env` 被误填为密钥样式值时，Pydantic 异常不得回显该输入；回归测试必须真正输入受控哨兵值，不能检查一个从未进入系统的无关字符串。
2. 返回自由形状 `dict[str, Any]` 的 YAML 原始加载器不得作为公共 API 导出；公开入口必须返回已验证具名类型。
3. Pipeline/Job 转换集合不得作为可被调用方修改的公共 `dict` 暴露；保留私有实现或提供运行时不可变语义。

边界澄清：

- 统一错误码以 System Design 第 12 节列出的八项为冻结集合；`InvalidTransitionError` 可以保留为领域异常，但不得静默扩展公共 `ErrorCode`。
- `target_stage` 的持久化属于已批准 ADR-003/TASK-003；TASK-002 只冻结 `ProcessingStage`、状态转换和“失败不推进 Pipeline”的领域语义，不新增 Job 存储模型。
- Provider 调用关联与元数据如存在多种公共接口实现方式，不得在修复轮自行新增 Wrapper 或字段；在交接中输出 `DECISION NEEDED`，交由主控先澄清契约。

## 修复证据与审查授权

- Correction code commit: `8492c42b971b01d3aaf4e6cb11e2e5a8210fe46a`
- Evidence/source head: `8f50df2f7e93d778f32947ca471740b6713c9aff`
- Commit chain: `46f8497e... -> 4355a59... -> 8492c42... -> 8f50df2...`
- Implementer state: 已停止写入；worktree 在主控只读核对时干净。
- Pre-review result: 三个强制修复项和额外 `ErrorCode` 已有代码与测试证据；受控密钥哨兵在直接/nested error 的文本、`repr`、结构化 errors、cause/context 中均未出现。
- Status at review authorization: `IN_REVIEW`
- Reviewer packet: `agent-prompts/TASK-002-REVIEWER-GROK.md`
- Review scope: `46f8497e771e1461034942dd7967f19d85f79f81...8f50df2f7e93d778f32947ca471740b6713c9aff`
- Reviewer write scope: 只可补充并提交 `handoffs/TASK-002.md`，不得修改业务代码、测试、依赖或公共任务状态。

## Reviewer 改派记录

- Reassigned at: 2026-07-15
- Requested by: 产品负责人
- Previous reviewer: Codex，未启动、未写 TASK-002 worktree。
- Active reviewer: Grok，全新独立会话；不得复用 Implementer 对话、总结或隐藏上下文。
- Independence mitigation: Reviewer 必须从冻结规格、完整 `base...source head` Diff 和重新运行的检查独立重建 AC-1 至 AC-8；同模型自审不能替代证据，任何未解决 P0/P1 必须 `REJECT`。
- Superseded packet: `agent-prompts/TASK-002-REVIEWER-CODEX.md`，禁止执行。
- Active packet: `agent-prompts/TASK-002-REVIEWER-GROK.md`
- Status at reassignment: `IN_REVIEW`

## 独立审查与主控验收

- Reviewed source head: `8f50df2f7e93d778f32947ca471740b6713c9aff`
- Review evidence commit: `d98de3537187ac346e404d7899d0a9d90c228483`
- Reviewer verdict: `APPROVE`
- Reviewer checks: locked sync、focused/full pytest（46/47 passed）、mypy、Ruff、CLI help、Diff/状态与两个独立探针全部通过。
- Acceptance matrix: AC-1 至 AC-8 全部 `PASS`。
- Findings: P0/P1/P2 无；P3 为公开 `MappingProxyType` 仍由私有 backing dict 支撑，以及后续写入时路径重检/运行时密钥解析职责。
- Contract decision: Provider request correlation/调用元数据、八项 `ErrorCode` 和 `target_stage` 职责与冻结规格一致；`DECISION NEEDED=None`。
- Orchestrator verdict: `ACCEPT`
- Accepted source head for integration: `d98de3537187ac346e404d7899d0a9d90c228483`
- Status at acceptance: `ACCEPTED`；随后由最终 Integrator 整合并由主控关闭为 `DONE`。

## 最终整合与关闭

- Acceptance anchor: `1d8d16115173297aecb04a1a2ecfc2dc2927e3ff`
- Execution base: `e2aef7cd88f5c0f0f4e323a79234e71ca6a95845`
- Accepted source/review head: `d98de3537187ac346e404d7899d0a9d90c228483`
- Merge commit: `823d68a2dffc1745e04cbbe54c817bf0c117a6fa`
- Merge parents: `e2aef7cd88f5c0f0f4e323a79234e71ca6a95845`、`d98de3537187ac346e404d7899d0a9d90c228483`
- First-parent scope: 精确为任务批准的 8 个文件；无范围外文件。
- Post-merge checks: `uv lock --check`、`uv sync --locked`、focused/full pytest（46/47 passed）、mypy、Ruff、CLI help、cached diff 与祖先关系全部 `PASS`。
- Git identity: `Mozhu <huangbuqubunao@gmail.com>`；main 与 source worktree 均干净，source 分支/worktree 保留。
- Final status: `DONE`
- Downstream release: `TASK-003` 与 `TASK-004` 的依赖已满足，均转为 `READY`。
