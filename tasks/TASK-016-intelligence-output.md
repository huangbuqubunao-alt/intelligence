# TASK-016：Local / Hybrid / Cloud Intelligence 与中文知识输出

- Status: `IN_PROGRESS`
- Assignee: `Codex Orchestrator`
- Base: `main@451766f9b1772eed9d36587d7956328ee7c2f7ff`
- Dependencies: TASK-015 `DONE`、ADR-023 `Accepted`
- Reuse decision: `DIRECT` — 复用现有 Pydantic 领域契约、Ollama/OpenAI Adapter、
  SQLite Repository、Artifact/ProviderCall、Obsidian 安全渲染、Weekly Service 与锁定
  依赖；不新增生产依赖。

## 2026-08-28 provider architecture review

- The deterministic qualification record concludes `QUALIFIED_LOCAL_MODEL=NONE`:
  no candidate qualified under the fixed protocol. It does not claim that all
  local models are incapable.
- `docs/TASK-016-LOCAL-DEEP-ANALYSIS-PROVIDER-ARCHITECTURE-REVIEW.md` selects a
  provider-neutral architecture in which local, optional free cloud, and
  user-key paid cloud are peers behind one untrusted-output validation and
  provenance contract. Local-only is no longer a hard delivery requirement;
  local mode remains supported and cloud dispatch remains explicit,
  privacy-bounded, and never an automatic fallback.
- This is an architecture decision only. It authorizes no provider code,
  credentials, network/model activity, persistence/cache work, or TASK-016D/E/F
  implementation. The next implementation gate is an approved provider-neutral
  TASK-016 contract amendment that reconciles this decision with the existing
  milestone sequencing.

## 2026-08-28 provider-neutral contract amendment

- [TASK-016 Deep Analysis Provider-Neutral Contract Amendment](../docs/TASK-016-DEEP-ANALYSIS-PROVIDER-NEUTRAL-CONTRACT-AMENDMENT.md)
  Correction R2 and ADR-027 freeze the corrected provider-neutral contract. The
  canonical subsystem is `Deep Analysis`; local, optional free cloud, and
  user-key cloud are explicit peers and provider output remains untrusted.
- Correction R1 closed the independent review's P0 and eight original
  implementation-critical P1 findings. Correction R2 closes the second
  review's sole new P1: every fallback plan is a pre-dispatch-validated finite
  DAG with an explicit start node, duplicate semantic-node rejection,
  deterministic failure-class edge matching, no re-entry, bounded attempts,
  fail-closed headless approval, and complete ordered provenance. A2 remains
  the DACS-1 hash of the exact provider-semantic request
  projection; cache binds A1/A2/A3/validation policy; payload is an
  application-owned allowlisted projection; consent/fallback, credentials,
  floating models, context, retry, response identity, 016D evidence retention,
  and qualification are fail-closed. It remains contract-only.
- Provider-native JSON schema is an output constraint only. The amendment
  prohibits application-side repair, first-JSON/fence extraction, hidden
  quality retries, and silent provider fallback. It preserves the authoritative
  scoring ingress and binds exactly to
  `VerifiedScoringRead.scoring_outcome.result.request_hash`, never to
  `scoring_success_provenance`.
- Historical M1/M2/M3 sequencing below is superseded for Deep Analysis by P0–P7:
  independent review; corrected provider-neutral contracts; dispatch/validation
  boundary; one separately qualified adapter; runtime integration; 016D; 016E;
  016F. The historic Hybrid fallback and generic retry language is superseded
  for Deep Analysis only; it does not authorize any provider selection.
  This remains design-only. TASK-016B and TASK-016C remain closed.

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
- Model-selection round 2 is recorded in
  `docs/TASK-016-LOCAL-DEEP-ANALYSIS-MODEL-SELECTION-R2.md`. It rejects only
  the evidenced `qwen3:8b` digest / Ollama 0.32.1 raw/no-format profile,
  selects `qwen2.5:7b` as the one next candidate, and requires separate model
  acquisition, tokenizer freeze/parity, byte-bound reconciliation, and M1 Pro
  feasibility gates. It makes no provider/context-contract change and keeps
  implementation unauthorized; TASK-016B and TASK-016C remain closed.
- The separately authorized acquisition of `qwen2.5:7b` has passed and freezes
  local Ollama `0.32.1` digest
  `sha256:845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`.
  The acquisition record is
  `docs/TASK-016-LOCAL-DEEP-ANALYSIS-QWEN25-MODEL-ACQUISITION.md`.
  Qwen2.5 tokenizer artifact/parity, raw-profile parity, byte-bound
  reconciliation, and M1 Pro feasibility remain separate required gates;
  implementation remains unauthorized.

## 产品目标

Cloud 关闭时仍为高价值视频生成完整、可信、默认中文的知识笔记；Hybrid 仅为高价值
视频使用受预算控制的 Cloud；Weekly 从列表升级为跨视频情报综合。

## 里程碑与顺序

### Superseded sequencing note

The following Local-only M1 / Hybrid M2 sequencing is historical planning.
It must not authorize implementation after the 2026-08-28 provider architecture
review. A provider-neutral contract amendment is required before replacing it
with a new ordered implementation plan.

### Historical M1：Local-only 可用产品

`016A -> 016B -> 016C -> 016D -> 016E -> 016F`

每个任务必须独立审查并整合。前一任务未 `DONE` 时不得分配下一项。`016F` 整合后必须
停下，由产品负责人验收 Local-only 真实输出。

### Historical M2：Hybrid / Cloud

- `016G`：Hybrid/Cloud Router、预算、fallback 与严格 Cloud 语义。
- 只有 M1 获产品验收后才可建立正式任务卡与实施授权。

### Historical M3：跨模式验收

- `016H`：Local/Hybrid/Cloud E2E、迁移兼容、真实 smoke 与运维证据。
- 真实网络、Key、付费调用及发送范围必须逐项另行批准。

## 总体验收边界

- Local-only 无 Key 能完成高价值视频的中文知识笔记与 Weekly V2。
- 低价值视频不执行 Deep Analysis。
- 所有 Provider 共享 Knowledge V2 Contract。
- Evidence、cache、model/mode/current-config provenance fail-closed。
- 不修改 SQLite Schema；不新增依赖。
- 不包含 UI、发布或 TASK-015 Remaining P2。

## 2026-08-29 P0 foundational-contract implementation slice

- Provider-neutral foundational contracts have been implemented in the isolated
  `deep_analysis_contracts` domain module: DACS-1 identities; A1/A2/A3; payload
  consent and scope; non-secret credential execution identity; fallback DAG and
  cache identities; and untrusted/trusted response boundary types.
- This slice contains no adapter, provider selection, transport, credential
  storage/loading, cache/persistence, validation pipeline, or TASK-016D/E/F
  code. `TASK-016B` and `TASK-016C` semantics remain unchanged.
- The implementation is awaiting independent review; this note does not change
  task lifecycle state or authorize any subsequent implementation slice.
