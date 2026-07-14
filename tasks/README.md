# YIA 任务分配索引

## 当前门禁

项目状态：`TASK_002_IN_PROGRESS`

DEC-01 至 DEC-10 已批准，`TASK-000`、`TASK-001` 均为 `DONE`。`TASK-001` 的实现与审查证据已通过 merge commit `5273e069aa34392db957e82b8803a709bdd1ab1f` 进入 `main`，整合后门禁全部通过。

`TASK-002` 已从 `main@46f8497e771e1461034942dd7967f19d85f79f81` 创建独立 worktree 和分支，分配 Grok 为唯一 Implementer、Codex 为后续独立 Reviewer，状态为 `IN_PROGRESS`。Reviewer 只在实现 commit 完成后启动。

## 状态定义

- `BLOCKED`：存在明确依赖或审批阻塞。
- `READY`：依赖和审批满足，可以由主控对话分配。
- `IN_PROGRESS`：已由一名执行者领取。
- `IN_REVIEW`：已提交证据，等待独立复核。
- `ACCEPTED`：独立审查和主控验收通过，等待整合。
- `DONE`：已整合到主线且整合后检查通过。

任务状态只由主控对话在主线更新。实现者和 Reviewer 通过 `handoffs/TASK-<id>.md` 报告，不直接修改公共任务状态。

## 任务表

| 任务 | 名称 | 负责人角色 | 当前状态 | 依赖 |
|---|---|---|---|---|
| [TASK-000](TASK-000-product-decisions.md) | 关闭 V1 开工决策 | PO + TL | DONE | 无 |
| [TASK-001](TASK-001-project-scaffold.md) | 工程脚手架与质量门禁 | Codex + Grok + Integrator | DONE | 000 |
| [TASK-002](TASK-002-config-domain-contracts.md) | 配置与领域契约 | Grok + Codex + Integrator | IN_PROGRESS | 001 |
| [TASK-003](TASK-003-state-store.md) | SQLite 状态存储 | 实现 Agent | BLOCKED | 002 |
| [TASK-004](TASK-004-discovery-metadata.md) | 频道发现与元数据 | 实现 Agent | BLOCKED | 002 |
| [TASK-005](TASK-005-subtitle-pipeline.md) | 字幕获取与规范化 | 实现 Agent | BLOCKED | 003, 004 |
| [TASK-006](TASK-006-local-transcription.md) | 本地 Whisper 转写 | 实现 Agent | BLOCKED | 005 |
| [TASK-007](TASK-007-local-scoring.md) | Ollama 本地评分 | 实现 Agent | BLOCKED | 005 |
| [TASK-008](TASK-008-deep-analysis.md) | 可选云端深度分析 | 实现 Agent + 隐私 Reviewer | BLOCKED | 007 |
| [TASK-009](TASK-009-obsidian-notes.md) | Obsidian 视频笔记 | 实现 Agent | BLOCKED | 003, 007 |
| [TASK-010](TASK-010-orchestration-recovery.md) | 流程编排与恢复 | TL/实现 Agent | BLOCKED | 003-009 |
| [TASK-011](TASK-011-weekly-report.md) | 周报 | 实现 Agent | BLOCKED | 009, 010 |
| [TASK-012](TASK-012-cli-operations.md) | CLI、调度与日志 | 实现 Agent | BLOCKED | 010 |
| [TASK-013](TASK-013-e2e-acceptance.md) | 端到端验收 | QA Agent | BLOCKED | 011, 012 |
| [TASK-014](TASK-014-release-readiness.md) | 发布准备 | PO + TL + QA | BLOCKED | 013 |

## 主控分配模板

主控对话将任务设为 `IN_PROGRESS` 时必须记录：

```text
Task: TASK-XXX
Agent/role: <Codex|Grok Build>/<Implementer|Reviewer|Integrator>
Base: <branch>@<commit>
Worktree: <absolute path>
Branch: <branch>
Allowed scope: <task card or files>
Required checks: <commands>
Special approvals: <none or links>
```

实现者使用 `handoffs/TEMPLATE.md` 建立任务交接报告。Reviewer 只在实现 commit 之后启动，并在交接报告给出 `APPROVE` 或 `REJECT`。

只有 Reviewer 核对外部证据、主控验收、Integrator 整合到主线并通过整合后检查，任务才能设为 `DONE`。完整规则见 `docs/COLLABORATION.md`。
