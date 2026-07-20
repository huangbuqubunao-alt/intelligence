# YIA 任务分配索引

## 当前门禁

项目状态：`TASK_003_DONE__TASK_004_DONE__TASK_005_DONE__TASK_005A_DONE__TASK_006_DONE__TASK_007_DONE`

DEC-01 至 DEC-10 已批准，`TASK-000`、`TASK-001` 均为 `DONE`。`TASK-001` 的实现与审查证据已通过 merge commit `5273e069aa34392db957e82b8803a709bdd1ab1f` 进入 `main`，整合后门禁全部通过。

`TASK-002` 的实现、预审修复、独立 Grok 审查和最终整合均已完成；审查证据 commit 为 `d98de3537187ac346e404d7899d0a9d90c228483`，merge commit 为 `823d68a2dffc1745e04cbbe54c817bf0c117a6fa`。整合后全部门禁通过，状态为 `DONE`。

`TASK-003` 已由 Codex Integrator 以 merge commit `072511f20b587f973b29437d79080f6cb7863f1a` 整合到 main，整合后门禁全通过，状态为 `DONE`。`TASK-004` 已由 Codex Product Integrator 以 merge commit `dc3f097ce125bc8390b04d0913b5d00f44eae3e8` 整合：双父、固定 17 文件范围及 lock/sync、state 30、unit 36、integration 10、全量 132、mypy/wiring、Ruff、CLI、build/migration 门禁均通过；状态在本次收口后为 `DONE`。

TASK-005 已由 Codex Product Integrator 以 merge commit `cfc302ddc41cd908777f49de292327640b6f8314` 整合到 main，双父和 first-parent 11 文件范围正确；整合后全部受影响离线门禁、offline build 与 package inclusion 通过，并已 closure 同步为 `DONE`。唯一 Service/私有 test hook 聚合 P2 继续登记。ADR-007 已接受并建立 TASK-005A 共享契约任务；TASK-005A、TASK-006/007 的后续结果见下文当前状态。

TASK-005A 已由 Codex Product Integrator 以 merge commit
`865f4fed90dcc22ea43688442c1c4f210b4d31b7` 整合并关闭为 `DONE`：双父与 first-parent
8 路径范围正确，整合后全部离线门禁及 package inclusion 通过。产品负责人现已从共同
base `6b4d59c...` 并行分配 TASK-006 阶段 A 与 TASK-007 离线实现：TASK-006 独占
`pyproject.toml`/`uv.lock`，只获包解析/锁定/安装授权；TASK-007 不改依赖/锁文件且仅用
离线 Fake。两项真实模型、服务、ffmpeg、媒体和凭据路径继续未授权。

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
| [TASK-003](TASK-003-state-store.md) | SQLite 状态存储 | Codex Implementer + 独立 Grok Reviewer + Codex Integrator | DONE | 002 |
| [TASK-004](TASK-004-discovery-metadata.md) | 频道发现与元数据 | Codex Integrator merge `dc3f097...` | DONE | 002 |
| [TASK-005](TASK-005-subtitle-pipeline.md) | 字幕获取与规范化 | 已整合并关闭；merge `cfc302...` | DONE | 003, 004 |
| [TASK-005A](TASK-005A-local-model-shared-contracts.md) | 本地模型共享契约 | 已整合并关闭；merge `865f4fed...` | DONE | 005 |
| [TASK-006](TASK-006-local-transcription.md) | 本地 Whisper 转写 | 已整合并关闭；merge `fd9a074...` | DONE | 005A；模型/ffmpeg/媒体另批 |
| [TASK-007](TASK-007-local-scoring.md) | Ollama 本地评分 | 已整合并关闭；merge `3d49ec...` | DONE | 005A；Ollama/模型另批 |
| [TASK-008](TASK-008-deep-analysis.md) | 可选云端深度分析 | Codex + 独立 Codex 隐私 Reviewer（未分配） | BLOCKED | 007 |
| [TASK-009](TASK-009-obsidian-notes.md) | Obsidian 视频笔记 | Codex（未分配） | BLOCKED | 003, 007 |
| [TASK-010](TASK-010-orchestration-recovery.md) | 流程编排与恢复 | Codex + 独立 Codex Reviewer（未分配） | BLOCKED | 003-009 |
| [TASK-011](TASK-011-weekly-report.md) | 周报 | Codex（未分配） | BLOCKED | 009, 010 |
| [TASK-012](TASK-012-cli-operations.md) | CLI、调度与日志 | Codex（未分配） | BLOCKED | 010 |
| [TASK-013](TASK-013-e2e-acceptance.md) | 端到端验收 | Codex QA（未分配） | BLOCKED | 011, 012 |
| [TASK-014](TASK-014-release-readiness.md) | 发布准备 | PO + Codex TL/QA（未分配） | BLOCKED | 013 |

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
