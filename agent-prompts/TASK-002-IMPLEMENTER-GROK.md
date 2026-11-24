# TASK-002 Grok Implementer Task Packet

## 身份

你是 Grok，担任 `TASK-002` 的唯一 Implementer。你只实现已批准的配置与领域契约，不领取后续任务，不承担 Reviewer、主控验收或整合职责。

## 固定上下文

在任务 worktree 中按顺序完整读取：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. `docs/PROJECT_STATUS.md`
4. `docs/PRD.md` 第 4、6、8、9、13、14、15 节
5. `docs/SYSTEM_DESIGN.md` 第 3、5、6、7、12、13、14、16、18 节
6. `docs/PRODUCT_DECISIONS.md` 的 DEC-02
7. `docs/decisions/ADR-002-config-domain-contracts.md`
8. `tasks/TASK-002-config-domain-contracts.md`
9. `handoffs/TEMPLATE.md`

如任一文件冲突、公共字段仍有多种合理解释，或实现必须扩大范围，立即停止并输出 `DECISION NEEDED`，不得自行选择解释。

## 开工包

- Task: `TASK-002`
- Role: `Implementer`
- Agent: `Grok`
- Base: `main@46f8497e771e1461034942dd7967f19d85f79f81`
- Worktree: `/Users/developer/Documents/yia-worktrees/task-002`
- Branch: `grok/task-002-config-domain-contracts`
- Reviewer: Codex 独立会话；仅在实现 commit 后由主控启动
- Parallel now: `TASK-003`/`TASK-004` Read-only Preflight，可由其他只读会话执行
- Waiting: `TASK-003`、`TASK-004` 及后续写入型实现

基线说明：该 worktree 从授权提交创建，因此其中的公共任务卡仍显示 `READY/UNASSIGNED`；角色分配随后只提交到 `main` 控制面，不进入实现分支。这是预期隔离，不是规格冲突。以本任务包的角色、worktree 和 branch 为本轮执行授权；不要 pull、merge 或 cherry-pick 分配状态 commit。

## 允许范围

只允许提交以下 8 个文件：

- `src/youtube_intel/config.py`
- `src/youtube_intel/domain.py`
- `config/channels.example.yaml`
- `config/settings.example.yaml`
- `tests/unit/test_contracts.py`
- `pyproject.toml`
- `uv.lock`
- `handoffs/TASK-002.md`

测试缓存和虚拟环境可由验证命令生成，但不得提交。不得修改 `__init__.py`、CLI、公共任务状态、ADR、其他测试、其他 worktree 或任何范围外文件；需要额外文件时先停止并请求主控批准。

## 已批准依赖与权限

- 直接运行时依赖仅限 `pydantic>=2.13.4,<2.14`、`PyYAML>=6.0.3,<7`。
- 允许 uv 网络下载并锁定以上依赖及其必要传递依赖；不启用任何可选 extras。
- 使用现有 Python 3.12、uv、build backend 和开发工具；不得升级 uv 或既有工具链。
- 不新增 `pydantic-settings`、`types-PyYAML` 或其他直接依赖。若 PyYAML 缺少类型标记，只允许在对应导入处使用精确的 `# type: ignore[import-untyped]`，不得放宽全局 mypy 配置。
- 不调用 YouTube、Ollama、OpenAI 或其他网络服务；不解析真实密钥，不接触真实 Vault，不创建数据库或注册 launchd。

## 接口与实现要求

### 配置边界

1. 使用 Pydantic V2 强类型模型，在每个外部输入边界拒绝未知字段；不要使用 `BaseSettings` 或环境自动注入。
2. 配置优先级固定为内建默认值 < YAML < 显式 CLI overrides。CLI overrides 必须是具名、可校验的结构，不得把自由形状 `dict` 暴露为公共契约，也不得提前发明 TASK-012 的命令选项。
3. YAML 只能通过 `yaml.safe_load` 或显式 `SafeLoader` 读取；恶意 Python tag 必须失败。加载后立即把不可信对象交给 Pydantic 验证。
4. 实现 System Design 14.1 的全部字段、默认值、必填关系、范围、唯一性和稳定排序；频道同优先级按 `channel_id` 升序。
5. 使用标准库 `zoneinfo` 校验 IANA 时区。语言偏好必须非空、有序且去重；频道 ID 必须非空且唯一。
6. 项目路径只接受项目根相对路径并拒绝绝对路径、`..` 和规范化逃逸；Vault 根只接受绝对路径，Vault 子目录只接受安全相对路径。配置层只校验和解析，不写任何目录或文件。
7. `api_key_env` 只验证环境变量名称；不得读取对应环境变量值。模型 `repr`、验证错误、人工示例和测试快照不得包含任何真实密钥值。

### 领域与 Provider 契约

1. 实现 System Design 第 5、6 节全部具名对象、枚举和 Provider `Protocol`；公共接口不得导入具体 Provider SDK 或返回未校验自由文本。
2. 输入对象与输出对象分离；Provider 返回新对象，不原地修改调用方对象。公共集合使用不可变或只读语义，并有确定顺序。
3. `ScoreResult`、固定六个评分维度、`AnalysisResult`、`AnalysisPoint`、`EvidenceExcerpt` 的字段、基数、长度、枚举和引用完整性必须与 System Design 一致。
4. `PipelineStatus`、`ProcessingStage`、`JobStatus` 必须是三个独立枚举。只实现 ADR-002 允许的 Pipeline/Job 转换；失败 Job 不改变最近成功的 Pipeline 状态。
5. 实现完整统一错误码及结构化、安全化错误对象；可重试语义和建议等待时间不得混为字符串约定。
6. 对外暴露的类型和入口保持最小、可预测，并在模块中明确导出；不要为后续 Adapter、SQLite 或编排层预写实现。

## 测试要求

先在 `tests/unit/test_contracts.py` 写失败测试，再做最小实现。至少覆盖：

- 有效示例配置和默认值；默认 < YAML < overrides 的优先级。
- 根层和嵌套未知字段、重复频道/语言、无效 IANA 时区和全部数值边界。
- `priority=0/100`、阈值 `0/10`、Top N `1/100` 通过，越界失败；并发不是 `1` 失败。
- 重试顺序、正超时、本地评分限制、云端启用必填关系和预算上限。
- 项目路径/Vault 路径绝对、相对、`..`、规范化与符号链接逃逸场景。
- `safe_load` 拒绝恶意 Python tag；密钥值不出现在 `repr`、验证错误或快照。
- 所有领域对象、集合基数、证据引用、错误码和 Provider Protocol。
- Pipeline 与 Job 的合法/非法转换，以及失败 Job 保留视频最近成功阶段。
- 领域模块不导入具体 SDK，公开契约不使用自由形状 `dict`。

测试只使用临时目录和无密钥样例；不得访问网络、真实环境配置或真实 Vault。

## 执行流程

1. 复述目标、八项验收标准、依赖和 8 个允许文件。
2. 运行并核对：

   ```bash
   pwd
   git branch --show-current
   git rev-parse HEAD
   git status --short
   ```

   目录、分支、基线或干净状态不符立即停止。

3. 用 uv 添加精确批准范围：

   ```bash
   uv add 'pydantic>=2.13.4,<2.14' 'PyYAML>=6.0.3,<7'
   ```

4. 按测试先行方式实现最小契约，不修改批准范围之外的文件。
5. 从 `handoffs/TEMPLATE.md` 创建 `handoffs/TASK-002.md`，加入 ADR-002 C-01 至 C-08 逐项追踪、依赖锁摘要、脱敏有效/无效配置示例、检查证据和剩余风险。
6. 运行全部检查：

   ```bash
   uv lock --check
   uv sync --locked
   uv run python -m pytest tests/unit/test_contracts.py
   uv run python -m pytest
   uv run mypy src
   uv run ruff check .
   uv run python -m youtube_intel --help
   git diff --check
   git status --short
   ```

7. 人工检查无效阈值、无效时区、恶意 YAML tag 和密钥脱敏；记录字段路径明确且不含密钥值的结果。
8. 完整复核 `46f8497e771e1461034942dd7967f19d85f79f81...HEAD` 以及全部未提交/未跟踪文件，确认只有 8 个允许文件、没有生成物、真实路径或密钥。
9. 全部通过后创建范围明确的 commit，建议消息：`feat: define configuration and domain contracts`。不得合并 `main` 或改变公共任务状态。

网络或沙箱阻止已授权下载时，可以请求仅限批准依赖的执行权限。不得通过删减测试、跳过检查、放宽验证、修改全局 mypy/Ruff 配置或替换依赖来获得通过。

## 最终输出

```text
Task: TASK-002
Role: Implementer
Branch/worktree:
Base commit:
Head commit:
Changed files:
Acceptance criteria: PASS/FAIL/BLOCKED per item
Checks: command + exit/result summary
Dependency lock summary: direct and transitive versions
ADR-002 traceability: C-01 through C-08
Manual redaction/path checks:
Diff review:
Skipped checks:
Remaining risks:
Decision needed: None | details
```
