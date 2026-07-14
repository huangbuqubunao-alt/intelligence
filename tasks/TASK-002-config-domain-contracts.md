# TASK-002：配置与领域契约

- Status: `IN_PROGRESS`
- Assignee: `Grok`
- Reviewer: `Codex`（等待实现 commit）
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
- Reviewer: Codex；仅在主控确认实现 commit、交接证据和 `IN_REVIEW` 状态后启动。
- Implementer packet: `agent-prompts/TASK-002-IMPLEMENTER-GROK.md`
- Parallel read-only work: `agent-prompts/PREFLIGHT-TASK-003-004-READONLY.md`；不构成后续任务开工授权。
