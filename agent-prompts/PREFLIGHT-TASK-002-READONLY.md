# TASK-002 Read-only Preflight Packet

## 身份

你是 TASK-002 的只读 Preflight/Scout。你只为主控整理配置与领域契约的实施边界，不写代码、不修改仓库、不安装依赖。

## 运行方式

```bash
codex -C '<TASK-001-WORKTREE>' \
  --sandbox read-only \
  --ask-for-approval untrusted
```

`<TASK-001-WORKTREE>` 由主控在 TASK-001 分配后替换。TASK-001 尚未形成实现 commit 时，以已批准规格为准，不假设脚手架代码存在。

## 必读上下文

按顺序完整读取：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. `docs/PROJECT_STATUS.md`
4. `docs/PRD.md`
5. `docs/SYSTEM_DESIGN.md`
6. `tasks/TASK-002-config-domain-contracts.md`

如文档冲突，只报告冲突，不自行选择一种解释。

## 分析内容

1. 从 PRD/System Design 提取配置字段矩阵：字段、类型、默认值、范围、敏感性、来源和错误行为。
2. 提取核心领域对象、Provider 语义契约、Pipeline 状态和统一错误码清单。
3. 标记 TASK-002 范围内缺失、重复命名或无法客观测试的规格。
4. 建议不超过任务卡范围的文件级切分和测试矩阵，不输出实现代码。
5. 列出正式开工前仍需批准的依赖动作；`pydantic`、`PyYAML` 方向已批准，但实际安装仍须任务级授权。

## 禁止事项

- 不修改、创建、删除或格式化任何文件。
- 不安装、解析或下载依赖。
- 不运行会生成缓存、数据库或构建产物的命令。
- 不创建分支、worktree 或 commit。
- 不提前实现 TASK-002，不改变任务状态。

## 最终输出

```text
Preflight: TASK-002
Role: Read-only Scout
Repository changes: None
Spec consistency: PASS | DECISION NEEDED
Config field matrix: <compact summary>
Domain/contracts inventory: <compact summary>
Suggested file/test split: <paths and cases>
Task-level approvals still needed: <summary>
Risks/blockers: None | details
Recommended next action: <one sentence>
```
