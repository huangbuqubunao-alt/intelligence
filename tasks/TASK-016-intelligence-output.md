# TASK-016：Local / Hybrid / Cloud Intelligence 与中文知识输出

- Status: `IN_PROGRESS`
- Assignee: `Codex Orchestrator`
- Base: `main@451766f9b1772eed9d36587d7956328ee7c2f7ff`
- Dependencies: TASK-015 `DONE`、ADR-023 `Accepted`
- Reuse decision: `DIRECT` — 复用现有 Pydantic 领域契约、Ollama/OpenAI Adapter、
  SQLite Repository、Artifact/ProviderCall、Obsidian 安全渲染、Weekly Service 与锁定
  依赖；不新增生产依赖。

## 产品目标

Cloud 关闭时仍为高价值视频生成完整、可信、默认中文的知识笔记；Hybrid 仅为高价值
视频使用受预算控制的 Cloud；Weekly 从列表升级为跨视频情报综合。

## 里程碑与顺序

### M1：Local-only 可用产品

`016A -> 016B -> 016C -> 016D -> 016E -> 016F`

每个任务必须独立审查并整合。前一任务未 `DONE` 时不得分配下一项。`016F` 整合后必须
停下，由产品负责人验收 Local-only 真实输出。

### M2：Hybrid / Cloud

- `016G`：Hybrid/Cloud Router、预算、fallback 与严格 Cloud 语义。
- 只有 M1 获产品验收后才可建立正式任务卡与实施授权。

### M3：跨模式验收

- `016H`：Local/Hybrid/Cloud E2E、迁移兼容、真实 smoke 与运维证据。
- 真实网络、Key、付费调用及发送范围必须逐项另行批准。

## 总体验收边界

- Local-only 无 Key 能完成高价值视频的中文知识笔记与 Weekly V2。
- 低价值视频不执行 Deep Analysis。
- 所有 Provider 共享 Knowledge V2 Contract。
- Evidence、cache、model/mode/current-config provenance fail-closed。
- 不修改 SQLite Schema；不新增依赖。
- 不包含 UI、发布或 TASK-015 Remaining P2。
