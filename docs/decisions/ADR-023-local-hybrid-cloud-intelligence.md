# ADR-023：Local / Hybrid / Cloud Intelligence 与中文知识输出

## Status

Accepted

## Date

2026-08-12

## Context

TASK-015 已使正式 CLI 完成发现、字幕/转写、本地评分、Obsidian 笔记与周报。但
`cloud.enabled=false` 时，Analysis 被跳过：高价值视频只能得到评分，知识字段与周报
综合内容为空。产品必须满足 `Cloud OFF != Analysis OFF`，同时继续遵守既有成本、隐私、
Artifact provenance、Vault 安全与离线优先边界。

## Decision

1. 支持 `local-only`、`hybrid`、`cloud` 三种 Intelligence Mode。
2. 三种模式均先运行 Local Fast Scoring；只有达到 `thresholds.summary_score` 的视频
   才进入 Deep Analysis。
3. `local-only` 的 Local Deep Analysis 产品方向保留，但具体 Provider、任务号和实现边界
   当前为 `TBD / UNASSIGNED`，不需要 API Key。
4. `hybrid` 是产品推荐模式，但新安装和旧配置的安全初始行为不得自动启用云端；Cloud
   通过全部门禁后优先执行，失败、无 Key、超预算或输入不合格时降级到 Local。
5. `cloud` 仍先本地评分，并保持严格 Cloud 语义；失败时不得静默降级为 Local。
6. Local 与 Cloud 产生同一 `KnowledgeResult V2`；可信 provider/model/mode/version/hash
   provenance 由应用补充，不能接受模型自报。
7. `general.output_language` 进入评分、深度分析、周报、Prompt、Schema 验证和 cache
   identity；用户可见 AI 叙述默认遵守 `zh-CN`。
8. Evidence 由应用建立 Registry；模型只能引用现有 Evidence ID。只有可验证的字幕时间
   映射才展示 timestamp，Whisper 或无法稳定对齐的文本不得伪造时间戳。
9. Weekly V2 默认只消费已验证 Structured Video Knowledge，不发送完整 Transcript 或
   Obsidian 用户区。
10. 模型、mode、output language、Prompt、Schema、sampling/privacy policy 任一变化均
    产生新的执行或请求 identity；旧 Artifact 保留审计但不得冒充当前配置结果。
11. TASK-016 核心实现复用现有 Job、Artifact、ProviderCall 与 Report 表，不修改 SQLite
    Schema。
12. 实施采用 Local-only 第一里程碑；每张子任务独立实现、独立审查，禁止连续实现全部
    TASK-016 子任务。

## Local-only 第一里程碑

按顺序完成并逐项停留审查：

1. `TASK-016A`：模式、配置与统一知识契约。
2. `TASK-016B`：本地评分语言契约。
3. Local Deep Analysis：`TBD / UNASSIGNED`，不得使用 `TASK-016C`。
4. `TASK-016D`：Local-only 持久化编排与 cache provenance。
5. `TASK-016E`：Evidence Registry 与 Video Note V2。
6. `TASK-016F`：Weekly Intelligence V2。

编号修订（2026-08-13）：本 ADR 对 `TASK-016C` 的旧任务分配已由 ADR-025 明确
supersede；`TASK-016C` 只用于 Content Quality Layer。Local Deep Analysis 目标保持为
`TBD / UNASSIGNED`，其 Provider、任务号、接口、持久化和验收边界都必须由未来独立决策
重新分配。本修订不自动重编号、不授权实现，也不启动第 4–6 项。

Local-only 真实验收通过后，主控再次请求产品确认，才可分配 Hybrid/Cloud 路由与最终跨
模式验收任务。

## Alternatives Considered

- Cloud disabled 时继续写占位笔记：拒绝，不能形成用户知识价值。
- 所有视频直接 Cloud：拒绝，成本、延迟和隐私代价不可控。
- Local/Cloud 使用不同 Schema：拒绝，会把 Provider 差异泄漏给 Renderer、Weekly 和
  cache。
- Weekly 直接发送本周全部 Transcript：拒绝，token 成本高且 provenance 更弱。
- 为 TASK-016 新增 SQLite migration：拒绝，现有通用持久化结构已足够。

## Consequences

- 本地资源消耗和处理时间将增加，但无 Key 用户也能获得完整知识输出。
- Hybrid 必须明确显示实际执行 Provider 与 fallback 原因。
- Cloud/Hybrid 真实验证仍需网络、凭据、数据范围和费用的单独授权。
- TASK-015 Remaining P2 不纳入本任务，避免扩大范围。
