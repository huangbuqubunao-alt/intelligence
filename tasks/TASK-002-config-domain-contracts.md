# TASK-002：配置与领域契约

- Status: `BLOCKED`
- Assignee: `UNASSIGNED`
- Owner role: 实现 Agent
- Size: M
- Risk: Medium
- Depends on: TASK-001

## 目标

把已审批的配置、核心实体、Provider 输入输出和错误分类固化为经过类型与运行时校验的契约，为后续并行开发提供稳定边界。

## 范围

- 实现频道、运行设置、模型、阈值、语言、存储、重试和时区配置 Schema。
- 实现 System Design 中的核心领域对象、Pipeline 状态和统一错误码。
- 提供无密钥的示例配置，并在启动前报告字段级校验错误。

## 范围外

- 不连接 YouTube、Ollama、云模型、SQLite 或 Obsidian。
- 不在配置文件中加入真实密钥或用户真实 Vault 路径。
- 不擅自新增配置项；新增需求先更新 PRD/System Design。

## 验收标准

- [ ] 有效示例配置能加载成强类型对象；未知字段、非法阈值、无效时区和越界路径配置会明确失败。
- [ ] Provider 契约和领域对象不导入任何具体 Provider SDK，状态值与 System Design 一致。
- [ ] 密钥只表示为环境变量名/引用；对象显示、异常和测试快照不会泄露其值。

## 验证

- [ ] `python -m pytest tests/unit/test_contracts.py`
- [ ] `mypy src`
- [ ] `ruff check .`
- [ ] 人工检查：用无效阈值和无效时区运行配置加载，错误包含字段路径但不包含密钥值。

## 预计触达文件

- `src/youtube_intel/config.py`
- `src/youtube_intel/domain.py`
- `config/channels.example.yaml`
- `config/settings.example.yaml`
- `tests/unit/test_contracts.py`

## 交付证据

- 测试、类型检查和 Lint 结果。
- 一份脱敏的有效/无效配置输出示例。
- 契约变更摘要；无则写 `None`。
