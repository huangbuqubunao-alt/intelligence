# YIA 任务分配索引

## 当前门禁

项目状态：`TASK_003_004_IN_PROGRESS`

DEC-01 至 DEC-10 已批准，`TASK-000`、`TASK-001` 均为 `DONE`。`TASK-001` 的实现与审查证据已通过 merge commit `5273e069aa34392db957e82b8803a709bdd1ab1f` 进入 `main`，整合后门禁全部通过。

`TASK-002` 的实现、预审修复、独立 Grok 审查和最终整合均已完成；审查证据 commit 为 `d98de3537187ac346e404d7899d0a9d90c228483`，merge commit 为 `823d68a2dffc1745e04cbbe54c817bf0c117a6fa`。整合后全部门禁通过，状态为 `DONE`。

`TASK-003`/`TASK-004` 已从共同基线 `dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176` 建立独立 worktree 并并行分配。TASK-003 由 Codex 实现、Grok 等待审查；TASK-004 首个 Grok 实现 `392edfb897003c1583b538667d10a2a89926a94b` 的预审发现 P1 公共自由 `dict` 泄漏。首个修复 `10f5ffaaa3e8651a02e2f94c1736b8417acf3021` 仍保留非私有映射入口及以 `object` 包装的公开测试注入，已退回同一 Grok 会话做第二轮最小修复，Codex Reviewer 尚未启动。两项状态均为 `IN_PROGRESS`。

ADR-005 已接受“复用优先”策略；所有后续任务包必须引用 `docs/REUSE_REGISTER.md` 并给出 `Reuse decision`，不得未经评估从零实现或整套嵌入第三方应用。

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
| [TASK-002](TASK-002-config-domain-contracts.md) | 配置与领域契约 | Grok Implementer + 独立 Grok Reviewer + Integrator | DONE | 001 |
| [TASK-003](TASK-003-state-store.md) | SQLite 状态存储 | Codex Implementer + Grok Reviewer（等待实现） | IN_PROGRESS | 002 |
| [TASK-004](TASK-004-discovery-metadata.md) | 频道发现与元数据 | Grok Implementer（P1 第二轮修复中）+ Codex Reviewer（未启动） | IN_PROGRESS | 002 |
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
Reuse decision: <DIRECT | ADAPT | REFERENCE | REJECT/DEFER + source/version>
```

实现者使用 `handoffs/TEMPLATE.md` 建立任务交接报告。Reviewer 只在实现 commit 之后启动，并在交接报告给出 `APPROVE` 或 `REJECT`。

只有 Reviewer 核对外部证据、主控验收、Integrator 整合到主线并通过整合后检查，任务才能设为 `DONE`。完整规则见 `docs/COLLABORATION.md`。
