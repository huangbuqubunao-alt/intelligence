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
| [ADR-006](ADR-006-subtitle-acquisition-contract.md) | Proposed | 2026-07-15 | 冻结字幕选择、规范化、缓存、错误与 Artifact 恢复契约；等待产品负责人批准 T-01 至 T-15 |
