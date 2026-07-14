# YouTube Intelligence Agent — Repository Guidance

本文件适用于在本仓库工作的所有 Codex、Grok Build 和其他编码 Agent。

## 1. 开工前必须阅读

按顺序阅读：

1. `docs/COLLABORATION.md`
2. `docs/PROJECT_STATUS.md`
3. `docs/PRD.md`
4. `docs/SYSTEM_DESIGN.md`
5. 自己被分配的 `tasks/TASK-*.md`
6. 主控对话生成的 `agent-prompts/TASK-*.md`

如以上文件冲突，停止工作并向主控对话报告；不得自行选择一种解释。

## 2. 权限与角色

- 主控对话/Orchestrator：拥有产品决策、任务分配、任务状态和最终验收权。
- 实现者：一次只实现一张已分配且依赖已满足的任务卡。
- Reviewer：独立审查 Diff 和证据，不修改业务代码；只可补充对应交接报告。
- Integrator：只整合已经验收的提交，不顺便开发或重构。
- Worker 不得自行领取任务、扩大范围、把任务设为 `DONE` 或合并到 `main`。

## 3. Git 与并行规则

- 一个任务使用一个独立 worktree、一个分支和一个主要实现对话。
- 分支名使用 `<agent>/task-<id>-<slug>`，例如 `codex/task-003-state-store`。
- 不允许两个写入型 Agent 同时操作同一 worktree。
- 不直接在 `main` 开发、提交、合并、rebase、reset 或清理其他 Agent 的分支/worktree。
- 任务必须从包含全部已完成依赖的最新已验收基线创建。
- Reviewer 在实现者提交后工作；需要修复时退回原实现者。

完整流程见 `docs/COLLABORATION.md`。

## 4. 默认执行循环

1. 复述任务目标、完成标准、依赖和预计修改文件。
2. 检查任务状态、审批门禁、相关代码、测试和仓库说明。
3. 做满足任务的最小改动；不做无关重构。
4. 运行任务卡要求的测试、类型检查、Lint、构建或人工复现。
5. 检查 Diff 是否包含无关、危险或超范围修改。
6. 使用 `handoffs/TEMPLATE.md` 填写 `handoffs/TASK-<id>.md`。
7. 提交范围明确的 commit，报告 SHA；不得自行合并。

完成必须有外部证据，不能只靠 Agent 自述。

## 5. 红线

未经用户对具体动作明确批准，不得：

- 删除、跳过或弱化测试、断言、覆盖率或 CI 门禁。
- 编辑 `.env`、密钥、token、私钥、认证文件或生产配置。
- 新增/升级生产依赖，修改包管理器、锁文件或工具链。
- 修改数据库 Schema、执行破坏性迁移或删除数据。
- 写入真实 Obsidian Vault、调用付费云模型或注册/加载 launchd 服务。
- 执行强制 reset、广泛删除或其他不可逆操作。
- 实现 V2 数据源、GUI、Web、多用户或其他范围外功能。

出现红线、规格空白或跨任务接口冲突时，停止并输出 `DECISION NEEDED`。

## 6. 失败与报告

- 先处理类型/语法错误，再调试测试失败。
- 测试失败时先检查断言和预期，不先改测试。
- 同一失败连续出现两次后停止重复方法，保留命令、关键错误行、文件和已尝试方案。
- 最终报告必须包含：修改内容、检查及结果、Diff 复核、阻塞项、跳过项和剩余风险。
