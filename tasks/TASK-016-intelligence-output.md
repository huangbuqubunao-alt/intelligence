# TASK-016：Local / Hybrid / Cloud Intelligence 与中文知识输出

- Status: `IN_PROGRESS`
- Assignee: `Codex Orchestrator`
- Base: `main@451766f9b1772eed9d36587d7956328ee7c2f7ff`
- Dependencies: TASK-015 `DONE`、ADR-023 `Accepted`
- Reuse decision: `DIRECT` — 复用现有 Pydantic 领域契约、Ollama/OpenAI Adapter、
  SQLite Repository、Artifact/ProviderCall、Obsidian 安全渲染、Weekly Service 与锁定
  依赖；不新增生产依赖。

## Local Deep Analysis design status

- `TASK-016-LOCAL-DEEP-ANALYSIS` design amended in
  `docs/TASK-016-LOCAL-DEEP-ANALYSIS-AUTHORIZATION.md`; the candidate model /
  runtime gate is separately recorded in
  `docs/TASK-016-LOCAL-DEEP-ANALYSIS-M1PRO-FEASIBILITY-AUTHORIZATION.md`.
- Amendment R2 records that formal candidate-token/no-truncation proof is a
  prerequisite design blocker; it does not authorize a benchmark or any
  implementation work.
- `TASK-016-LOCAL-DEEP-ANALYSIS-CONTEXT-PROOF-AUTHORIZATION` now freezes the
  exact Qwen3-8B upstream tokenizer artifacts, hashes, `tokenizers==0.22.2`
  Apple-Silicon distribution, direct raw-text parity evidence, and
  `TokenizerIdentityV1`. Local Ollama model/tokenizer pairing, exact
  raw-profile/runtime-version proof, feasibility, and implementation remain
  separate gates.
- **LOCAL DEEP ANALYSIS TOKENIZER ARTIFACT / HASH FREEZE COMPLETE**; **LOCAL
  OLLAMA TOKENIZER / RAW-PROFILE PARITY PASSED** for exact Ollama `0.32.1`,
  exact `qwen3:8b` digest
  `sha256:500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`,
  and the raw/no-format profile only. The M1 Pro feasibility gate was then run;
  qwen3:8b has now failed the controlled M1 Pro raw/no-format structured-output
  gate: its required SHORT response had exact prompt-token parity but emitted
  Markdown/prose after JSON, so strict JSON/schema/grounding cannot pass. It is
  a `MODEL SELECTION BLOCKER`; no fallback is authorized and implementation
  remains unauthorized. This status update does not assign, start, rename, or
  supersede TASK-016D/E/F; TASK-016B and TASK-016C remain closed.

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
