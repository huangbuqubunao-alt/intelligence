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
| [ADR-013](ADR-013-restricted-public-subtitle-smoke-entry.md) | Accepted | 2026-07-26 | 冻结仅供发布 QA 的受限公开字幕 smoke 入口、临时根、脱敏审计与禁止资源边界 |
| [ADR-014](ADR-014-console-entrypoint-contract.md) | Accepted | 2026-07-27 | 仅将既有 CLI 主入口暴露为正式 `youtube-intel` console command，不扩展行为或资源权限 |
| [ADR-015](ADR-015-public-subtitle-directory-diagnostics.md) | Accepted | 2026-07-28 | 冻结公开字幕目录失败的有限脱敏分类、最小 smoke 审计出口及离线验证边界 |
| [ADR-016](ADR-016-directory-only-public-subtitle-smoke.md) | Accepted | 2026-07-28 | 冻结受限 directory-only 公开字幕 smoke、零正文读取和临时根边界 |
| [ADR-017](ADR-017-safe-subtitle-directory-shape-diagnostics.md) | Accepted | 2026-07-28 | 冻结目录 `INVALID_RESPONSE` 的固定无值结构诊断 |
| [ADR-018](ADR-018-safe-subtitle-directory-origin-fingerprint.md) | Accepted | 2026-07-28 | 冻结目录失败的固定无值来源与结构指纹 |
| [ADR-019](ADR-019-restricted-directory-keyname-diagnostic.md) | Accepted | 2026-07-29 | 冻结 mapping/unknown 边界的受限规范键名例外 |
| [ADR-020](ADR-020-safe-content-availability-diagnostics.md) | Accepted | 2026-07-29 | 冻结 `CONTENT_UNAVAILABLE` 的固定无值内容可用性来源分类 |
| [ADR-021](ADR-021-safe-subtitle-directory-contract-state-diagnostics.md) | Accepted | 2026-07-29 | 冻结 mapping `INVALID_RESPONSE` 的六字段无值目录契约状态矩阵 |
| [ADR-022](ADR-022-production-runtime-composition.md) | Accepted | 2026-08-12 | 正式 CLI production composition、首次运行 bootstrap 与可操作诊断 |
| [ADR-023](ADR-023-local-hybrid-cloud-intelligence.md) | Accepted；TASK-016C allocation superseded by ADR-025 | 2026-08-12；修订 2026-08-13 | Local/Hybrid/Cloud 总体方向；Local Deep Analysis 为 TBD / UNASSIGNED |
| [ADR-024](ADR-024-scoring-language-validator-scope.md) | Accepted | 2026-08-13 | 冻结评分语言校验器的可判定职责边界，实体与内容质量识别移交独立后续任务 |
| [ADR-025](ADR-025-content-quality-layer-scope-boundary.md) | Accepted；Phase F APPROVED；Phase G design ready / implementation not authorized | 2026-08-13 | 冻结 TASK-016C 窄 Deterministic Gate、可信 Finalizer、PASS attestation、F→G sealed continuation、pre-write/persistence 与 cache recovery 边界 |
| [ADR-026](ADR-026-task-016c-phase-d-provenance-authority-boundary.md) | Accepted | 2026-08-15 | 狭义修订 Phase D：已加载当前 AppConfig 仅能在 runtime composition 铸造 PASS attestation provenance capability |
| [ADR-027](ADR-027-provider-neutral-deep-analysis-contract.md) | Accepted；Correction R2 | 2026-08-28 | 提供方中立的深度分析、输入/资格/授权边界；具体 V1.x 激活遵循 V1X-DR-001～004 |
| [V1X-DR-001](V1X-DR-001-content-deep-analysis.md) | Accepted | 2026-10-01 | 冻结 V1.x Content 级深度分析：五角色产品契约、RELATION_TO_KNOWLEDGE/KNOWLEDGE_DELTA 延后、Phase 1B 后端 durable Evidence 收敛、无通用 router、资格门为激活门、Obsidian merge key 纠正、M13 分支与迁移序号隔离 |
| [V1X-DR-002](V1X-DR-002-durable-deep-analysis-evidence.md) | Accepted | 2026-10-02 | Phase 1B：durable Evidence promotion、同 Content membership、持久化与重启核验 |
| [V1X-DR-003](V1X-DR-003-deep-analysis-qualification-governance.md) | Accepted | 2026-10-03 | Phase 1C：独立资格记录及失效、生产资格、逐次云端授权、最小证据外发、诚实费用与至多一次派发；当前无合格生产路线 |
| [V1X-DR-004](V1X-DR-004-deep-analysis-obsidian-publish.md) | Accepted | 2026-10-03 | Phase 2：显式单向 Obsidian 投影、稳定语义身份、SQLite 权威与安全原子写入 |
| [V1X-PHASE3-DR-001](V1X-PHASE3-DR-001-home-knowledge-delta.md) | Accepted | 2026-10-03 | Phase 3：Home 七天确定性 Knowledge Delta、无模型、无持久状态 |
| [V1X-PHASE4-DR-001](V1X-PHASE4-DR-001-research-lite.md) | Accepted | 2026-10-03 | Phase 4：确定性的资料库优先研究证据包、显式内容范围、稳定语义身份与不可变执行 |
| [V1X-PHASE5-DR-001](V1X-PHASE5-DR-001-research-history.md) | Accepted | 2026-10-03 | Phase 5：不可变研究版本与历史读取、原子当前指针、无新增迁移 |
| [V1X-PHASE6-DR-001](V1X-PHASE6-DR-001-research-diff.md) | Accepted | 2026-10-03 | Phase 6：两个可信研究版本的确定性派生对比、无对比持久化或模型调用 |
| [ADR-028](ADR-028-external-o200k-provisioning.md) | Accepted | 2026-08-31 | 以显式管理员预置、固定哈希验证的本地资源替代 ADR-008 A-16 的包内 BPE 存储细节；无运行时网络或 fallback |
