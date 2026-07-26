# Architecture Decision Records

本目录保存会影响多个任务、成本较高或未来容易被重新争论的决策。

## 生命周期

```text
PROPOSED -> ACCEPTED -> SUPERSEDED | DEPRECATED
```

旧 ADR 不删除。决定改变时新增 ADR，并在新旧文档中互相引用。

## 索引

| ADR | 状态 | 日期 | 决策 |
|---|---|---|---|
| [ADR-001](ADR-001-multi-agent-development-model.md) | Accepted | 2026-07-14 | 以任务和 worktree 为单位组织 Codex/Grok 多 Agent 开发 |
| [ADR-002](ADR-002-config-domain-contracts.md) | Accepted | 2026-07-14 | 冻结 V1 配置、跨模块对象与三层状态契约 |
| [ADR-003](ADR-003-sqlite-state-store-contract.md) | Accepted | 2026-07-14 | 冻结 V1 SQLite 物理 Schema、事务、租约与迁移契约 |
| [ADR-004](ADR-004-discovery-ytdlp-contract.md) | Accepted | 2026-07-14 | 冻结发现提交点、字幕清单归属与 yt-dlp 依赖边界 |
| [ADR-005](ADR-005-reuse-first-delivery-policy.md) | Accepted | 2026-07-14 | 成熟组件优先复用，项目自有领域、状态、策略与安全控制面 |
| [ADR-006](ADR-006-subtitle-acquisition-contract.md) | Accepted | 2026-07-15 | 冻结字幕选择、规范化、缓存、错误与 Artifact 恢复契约；V1 不新增 Schema 或修改 Repository 完成语义 |
| [ADR-007](ADR-007-local-model-pipeline-contracts.md) | Accepted | 2026-07-17 | 冻结本地 Whisper/Ollama、评分持久化、共享契约与分阶段授权边界 |
| [ADR-008](ADR-008-cloud-analysis-contract.md) | Accepted | 2026-07-20；补充 2026-07-21 | 冻结云分析最小化输入、结构化跳过、token/调用预算、固定本地 tokenizer 资源与 OpenAI SDK 进程隔离边界 |
| [ADR-009](ADR-009-obsidian-note-contract.md) | Accepted | 2026-07-20 | 冻结 Obsidian 笔记身份、模板、用户区、路径、原子写和恢复边界 |
| [ADR-010](ADR-010-weekly-report-contract.md) | Accepted | 2026-07-23 | 冻结 completed_at ISO 周、确定性聚合、受控周报写入与包内模板边界 |
| [ADR-011](ADR-011-cli-operations-contract.md) | Accepted | 2026-07-23 | 冻结 CLI 退出码、JSONL 脱敏、零副作用 doctor 与静态 daily/weekly launchd 边界 |
| [ADR-012](ADR-012-local-transcription-continuation-contract.md) | Accepted | 2026-07-24 | 冻结本地 Whisper 成功转写的 Artifact/Provider-call 原子持久化与后续 Pipeline 衔接 |
