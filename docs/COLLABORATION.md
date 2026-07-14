# Codex + Grok Build 多 Agent 协作协议

- 版本：V1.2
- 状态：`ACTIVE`
- 适用范围：YouTube Intelligence Agent V1
- 控制面：主控产品/项目管理对话

## 1. 目标

让 Codex、Grok Build 和人工负责人可以并行工作，同时保持需求、代码、状态、证据和最终验收一致。并行单位是“独立任务”，不是“长期角色窗口”。

## 2. 事实来源

所有 Agent 共享的是仓库，不是彼此的聊天记忆。

| 文件/证据 | 作用 |
|---|---|
| `AGENTS.md` | 所有 Agent 的永久执行规则 |
| `docs/PRD.md` | 产品范围、行为和验收标准 |
| `docs/SYSTEM_DESIGN.md` | 接口、状态机、Schema 和错误语义 |
| `docs/PRODUCT_DECISIONS.md` | 产品/技术决策及批准状态 |
| `docs/PROJECT_STATUS.md` | 当前基线、活动任务、阻塞、风险和下一步的短摘要 |
| `docs/IMPLEMENTATION_ROADMAP.md` | 依赖、阶段和并行关系 |
| `docs/REUSE_REGISTER.md` | 外部组件的复用等级、来源、许可证和否决理由 |
| `tasks/TASK-*.md` | 单次实现范围和任务级验收 |
| `agent-prompts/TASK-*.md` | 主控按最新基线生成的任务/角色执行包 |
| `handoffs/TASK-*.md` | 实现、检查、审查和风险证据 |
| Git commit/Diff | 实际发生的变更 |

聊天中的新决定只有写回相应文件后才对其他 Agent 生效。

## 3. 角色

### 3.1 主控对话 / Orchestrator

- 维护 PRD、决策、路线图和任务状态。
- 决定某张任务卡何时进入 `READY`。
- 指定实现模型、Reviewer、基线 commit 和允许范围。
- 在任务进入 `READY` 时即时生成 Implementer/Reviewer/QA/Integrator 所需提示词，不提前批量生成过期任务包。
- 对照任务卡、Diff 和检查证据做最终验收。
- 只有验收并整合后，才能把任务设为 `DONE`。

主控对话不实现产品代码。

### 3.2 实现者

- 在独立 worktree 中完成一张任务卡。
- 开工前复核任务包的 `Reuse decision`；发现成熟候选更合适或登记已过期时先报告，不自行扩大依赖。
- 只修改任务卡允许的文件；需要额外文件时先报告。
- 运行检查、检查 Diff、填写交接报告并提交 commit。
- 不更新公共任务看板，不合并 `main`。

### 3.3 Reviewer

- 应优先使用与实现者不同的模型或独立新对话。
- 重新读取规格和任务卡，不依赖实现者总结。
- 审查 `base...HEAD`，重新运行关键检查。
- 不修改业务代码；可以在对应 `handoffs/TASK-*.md` 记录审查结论。
- 输出 `APPROVE` 或 `REJECT`；发现问题退回原实现者。

### 3.4 Integrator

- 只整合被主控对话标记为 `ACCEPTED` 的 commit。
- 一次整合一个任务并运行受影响检查。
- 有冲突时停止并交回主控对话，不自行重新设计。

## 4. 任务生命周期

```text
BLOCKED
  -> READY
  -> IN_PROGRESS
  -> IN_REVIEW
  -> ACCEPTED
  -> DONE

任一阶段发现依赖、红线或规格问题
  -> BLOCKED
```

| 状态 | 含义 | 谁能设置 |
|---|---|---|
| `BLOCKED` | 依赖或批准未满足 | 主控对话 |
| `READY` | 可以创建 worktree 并领取 | 主控对话 |
| `IN_PROGRESS` | 已指定实现者和分支 | 主控对话 |
| `IN_REVIEW` | 实现 commit 和交接证据齐全 | 主控对话 |
| `ACCEPTED` | Reviewer 与主控验收通过，待整合 | 主控对话 |
| `DONE` | 已整合到主线且检查通过 | 主控对话 |

Worker 通过交接报告汇报状态，不直接修改主线上的任务状态。

## 5. WIP 与并行限制

- 默认最多同时进行 2 张写入型实现任务。
- 最多再运行 1 个 Reviewer；主控对话不计入 WIP。
- 只有路线图明确标记可并行的任务才能同时进行。
- 两张任务如可能修改同一核心契约、Schema、依赖或共享配置，必须串行。
- 阅读、调研、测试分析可以更高并行，但必须返回摘要，不能产生未经分配的写入。

### 5.1 非阻塞调度

- Worker 必须在独立终端和独立对话中运行；启动后用户立即回到主控对话，不需要停留等待输出。
- 主控每次分配任务时同时列出：`立即启动`、`可并行启动`、`等待依赖` 三组工作。
- 有两张依赖已满足且范围隔离的写入任务时，分别使用独立 worktree 并行执行。
- 没有第二张可写任务时，可以启动只读 Preflight/Scout，会话只检查规格、环境、测试方案或风险并在聊天中返回摘要，不修改仓库、不创建 commit、不改变任务状态。
- 只读结论是后续开工包的输入，不是实现授权，也不能绕过依赖、审批或 Reviewer。
- 同一 worktree 任一时刻只允许一个写入者；Reviewer 如需写交接报告，也必须等待 Implementer 停止写入。
- 主控不轮询长日志。Worker 在 `BLOCKED`、提交完成或审查完成时，按最小回传格式报告即可。

本项目的批准并行批次：

1. `TASK-003` 与 `TASK-004`。
2. `TASK-006` 与 `TASK-007`。
3. `TASK-008` 与 `TASK-009`。
4. `TASK-011` 与 `TASK-012`。

其他关键路径任务默认串行。

`TASK-000` 是无 Git 基线时期的一次性例外：Integrator 在主 worktree 创建首个 commit 时，其他会话不得写该目录；允许并行运行 `PREFLIGHT-TASK-001-READONLY.md`，但它必须使用只读沙箱且只在聊天中输出结果。

## 6. Worktree 和分支规则

### 6.1 前置条件

- `main` 至少有一个已批准的基线 commit。
- 当前任务全部依赖已合并到基线。
- 任务状态为 `READY`。
- 主控对话已指定实现者和 Reviewer。

### 6.2 创建示例

```bash
mkdir -p ../yia-worktrees

git worktree add \
  ../yia-worktrees/task-003 \
  -b codex/task-003-state-store \
  main
```

Grok 实现任务使用 `grok/task-<id>-<slug>`；非工具绑定任务可使用 `agent/task-<id>-<slug>`。

### 6.3 隔离本地状态

- 每个 worktree 使用独立的临时 SQLite、缓存、日志和测试 Vault。
- 默认测试不得连接真实 Vault、真实云 Provider 或付费 API。
- 密钥只在获批任务的本地进程中注入，不提交、不复制到交接报告。
- 开发服务器或本地 Provider 需要端口时，每个 worktree 使用不同端口。
- 忽略文件不会自动成为可靠共享配置；使用无密钥示例和可重复 setup 命令。

## 7. 开工包

主控对话分配任务时必须提供：

```text
Task: TASK-XXX
Role: Implementer | Reviewer | Integrator
Agent: Codex | Grok Build
Base: <branch>@<commit>
Worktree: <absolute path>
Branch: <branch name>
Allowed scope: <task card / explicit files>
Required checks: <commands>
Reviewer: <agent/session>
Special approvals: <none or links>
Reuse decision: <DIRECT | ADAPT | REFERENCE | REJECT/DEFER + source/version>
Parallel now: <task/preflight or none>
Waiting: <blocked tasks and dependency>
```

缺少 Task、Base 或批准信息时不得开始写入。

## 8. 实现流程

1. 实现者阅读 `AGENTS.md`、PRD、System Design 和任务卡。
2. 复述目标、验收、依赖、预计文件；确认没有红线。
3. 根据 ADR-005 使用已批准组件或记录拒绝理由；适配代码保留来源、commit 和许可证证据。
4. 做满足验收的最小改动。
5. 运行任务卡指定检查；不得用删除/跳过测试换取通过。
6. 检查 `git status` 和相对基线的完整 Diff。
7. 填写 `handoffs/TASK-<id>.md` 的实现部分和复用证据。
8. 创建范围明确的 commit 并报告 SHA。
9. 主控对话把任务转为 `IN_REVIEW`，再启动 Reviewer。

## 9. 审查流程

Reviewer 必须：

1. 确认审查的 base、branch 和 commit。
2. 独立读取规格与任务卡。
3. 检查正确性、回归、测试遗漏、异常路径、安全、范围、许可证/来源和红线。
4. 重新运行关键命令，而不是只读实现者输出。
5. 按 P0/P1/P2/P3 记录问题和文件/行号。
6. 在交接报告写 `APPROVE` 或 `REJECT`，不直接修代码。

`REJECT` 后由原实现者修复并生成新 commit，再重新审查。

## 10. 主控验收与整合

主控对话只在以下条件全部满足时设置 `ACCEPTED`：

- 任务验收项逐条有证据。
- Reviewer 为 `APPROVE`，且没有未处置 P0/P1。
- 必需检查真实通过，跳过项已明确批准。
- Diff 没有无关修改或红线行为。
- 规格、实现和交接报告一致。

Integrator 整合后必须再次运行受影响检查。只有提交已进入主线、主线保持可用，任务才为 `DONE`。

## 11. 规格和决策升级

实现者遇到以下情况必须停止并输出 `DECISION NEEDED`：

- 任务卡与 PRD/System Design 冲突。
- 需要新增依赖、修改 Schema、云端数据范围或真实 Vault。
- 预计修改文件明显超过任务范围。
- 两个并行任务需要改变同一接口。
- 验收标准无法客观验证。

主控对话先更新决策/规格，再决定恢复、重开或取消任务。Agent 不能让既有代码反向决定产品需求。

## 12. 检查点

每个 Roadmap Checkpoint 由独立 QA 会话复核：

- 全量测试、Lint、类型检查和构建。
- 与 PRD 的阶段性验收。
- 分支和 worktree 是否有未整合/遗留状态。
- 任务证据是否齐全。
- 敏感信息、真实 Vault、云调用和依赖审批。

检查点通过前，不开启依赖它的下一阶段。

## 13. 主控对话上下文管理

- 主控对话只接收任务摘要、commit SHA、Reviewer 结论和关键检查结果，不接收整段原始日志。
- 每次任务状态变化后同步 `docs/PROJECT_STATUS.md`，使仓库而非聊天历史成为当前事实。
- 每个 Roadmap Checkpoint 完成后，主控对话生成一次紧凑状态快照。
- 若主控开始遗漏已批准决定、混淆任务状态或上下文长期过大，使用 `agent-prompts/ORCHESTRATOR-BOOTSTRAP.md` 新开一个主控对话。
- 新主控读取仓库快照并确认状态后，旧主控归档；两者不得同时分配任务。
- 不单独建立长期“提示词生成对话”，避免出现两个任务控制中心。
