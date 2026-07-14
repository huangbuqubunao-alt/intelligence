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
