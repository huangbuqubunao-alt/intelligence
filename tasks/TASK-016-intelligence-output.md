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
- FOUNDATIONAL CONTRACTS IMPLEMENTATION QUALIFIED: the five strict-mypy errors
  introduced by the focused contract test were corrected without production
  changes. The source-level normative mypy gate, focused contracts, full test
  suite, and Ruff pass; repository-wide mypy is back to its `1019 errors / 44
  files` pre-existing baseline only. This qualification does not authorize a
  provider, credential implementation, or TASK-016D/E/F.

## 2026-08-30 foundational-contract implementation correction R1

- The independent code review at `b66ed1d…` found four P0 and two P1 defects in
  the foundational implementation. Correction R1 closes all six: trusted
  consumption now requires process-local, runtime-owned admission verification,
  rather than `TrustedDeepAnalysisSuccess` instance shape; A1 hashes remain
  identities rather than authority tokens; the A2 mode matrix, credential
  identity, dispatch/fallback cross-bindings, and failure pair matrix are
  fail-closed.
- Process-local admission is deliberately not persisted and does not claim to
  defeat arbitrary interpreter/memory compromise. It mechanically rejects
  `object.__new__`, `object.__setattr__`, model-constructed, copied, or
  caller-created lookalikes at consumption time unless exact runtime-owned
  admission state exists. Persistence/revalidation remains TASK-016D scope.
- The credential execution contract now accepts only an opaque SHA-256 profile
  identity plus provider ID; raw account, organization, deployment, policy,
  credential-reference, and secret fields are structurally absent. This changes
  pre-release A3/node/cache golden values without changing DACS-1 or A1/A2;
  no trusted provenance has been persisted because 016D is unauthorized.
- Validation: focused contracts `41 passed`; full pytest `1823 passed, 1
  warning`; target test mypy, module/source mypy, Ruff, and `git diff --check`
  pass; repository mypy remains its `1019 errors / 44 files` historical
  baseline with zero errors in this test file. This correction still authorizes
  no provider adapter, credential storage/loading, or TASK-016D/E/F.

## 2026-08-30 foundational trust-authority closed-loop correction

- The Correction R1 second review identified that its registry-backed
  `_admit_*` / `_mint_*` seams were still caller-importable authority. The
  closed-loop correction removes those helpers and both registries entirely.
  The foundational public surface can verify
  `TrustedDeepAnalysisSuccess`, but has no successful production mint/admit
  path; verification fails closed until the separately authorized
  provider-neutral validation/finalizer boundary owns runtime admission.
- A1, known scoring request hashes, PRIMARY/REPAIR_H2C provenance, and
  caller-created or `model_construct` canonical input remain identities/data,
  never authority. Object-shaped lookalikes, copy/deepcopy/pickle,
  reconstruction, admission transfer, dead state, and object-ID reuse cannot
  produce trust because no foundational admission registry exists.
- Closed-loop review: `docs/TASK-016-DEEP-ANALYSIS-FOUNDATIONAL-TRUST-AUTHORITY-CLOSED-LOOP-REVIEW.md`.
  Final result: original P0 `4/4` closed; original P1 `2/2` closed; final P0
  `0`; final implementation-critical P1 `0`. Focused contracts `43 passed`,
  full pytest `1825 passed, 1 existing warning`, targeted/source mypy and Ruff
  pass, and repository mypy remains the `1019 errors / 44 files` baseline.
- This approval makes only the **Provider-Neutral Dispatch / Validation Boundary
  Design-to-Implementation Gate** ready. It does not authorize a provider
  adapter, credentials, TASK-016D/E/F, or any TASK-016B/C semantic change.

## 2026-08-30 provider-neutral dispatch / validation boundary

- Closed-loop implementation and review are recorded in
  `docs/TASK-016-DEEP-ANALYSIS-DISPATCH-VALIDATION-CLOSED-LOOP-REVIEW.md`.
- The runtime now owns input admission from an exact `VerifiedScoringRead`,
  payload projection, prepared dispatch binding, ordered untrusted-response
  validation, and the successful `TrustedDeepAnalysisSuccess` admission.
- No concrete provider adapter, transport/network code, credential storage, or
  TASK-016D/E/F work was added. The next logical gate is one qualified
  reference-provider adapter, not persistence/cache work.

## 2026-08-30 OpenAI reference-provider adapter qualification

- The first concrete provider adapter is the qualified OpenAI Responses adapter:
  `CLOUD_USER_KEY` provider ID `openai`, adapter
  `openai-deep-analysis-responses` v1, and versioned model snapshot
  `gpt-5.4-mini-2026-03-17`. OpenAI is a reference provider, not the sole or
  globally mandatory provider.
- The adapter accepts only a prepared provider-neutral dispatch and returns only
  an untrusted response. Strict application schema/domain/grounding/KG2/language/
  provenance validation and the trusted success mint remain finalizer-owned.
- The frozen profile uses Responses `POST /v1/responses`, strict provider JSON
  Schema as an output constraint only, selected evidence only, conservative
  400k context admission, 30-second bounded timeout, and SDK retries disabled.
  It has no provider/model fallback and persists no credentials.
- Fake-transport adapter tests, finalizer integration, fabricated-evidence,
  secret-leak, request-ID identity, retry, timeout, and transcript-minimization
  attacks pass. Full pytest is `1854 passed, 1 warning`; source mypy and Ruff
  pass; repository mypy remains exactly its `1019 errors / 44 files` baseline.
- No approved temporary OpenAI credential was present, therefore live
  qualification is mechanically `LIVE CREDENTIAL BLOCKED`; no request was sent
  and no secret was persisted. This does not block the qualified offline adapter
  gate because current official API evidence and complete fake-boundary tests
  establish the mandatory mechanical provider properties.
- Final review is `APPROVE`, P0 `0`, implementation-critical P1 `0`. The next
  gate is TASK-016D provider-aware Deep Analysis persistence/cache provenance;
  TASK-016B/C remain closed and TASK-016E/F remain unauthorized.

## 2026-08-30 TASK-016D persistence/cache provenance

- TASK-016D adds SQLite schema v3 and append-only provider-aware Deep Analysis
  persisted results. It retains contract-required input/request/execution,
  validation, response, KnowledgeContent, scoring, Evidence Registry,
  consent/scope, and attempt provenance for persisted revalidation.
- A database row is not runtime admission: writes require a live
  runtime-verified success; reads return only an integrity-verified persisted
  representation. The original process-local admission is not persisted.
- Exact cache identity binds A1/A2/A3/validation policy; floating profiles are
  audit-only/cache-ineligible. Evidence is in the TASK-016D persistence and
  closed-loop review documents. OpenAI live remains `PENDING / CREDENTIAL
  BLOCKED`; no provider call, credential storage, 016E/F, or 016B/C change.
- Independent adversarial review found and closed one P0: a persisted
  `provenance_identity` alteration originally escaped cache-read verification.
  `84715a0` adds a regression test and exact finalizer-compatible provenance
  recomputation. Final result: `APPROVE`, P0 `0`, implementation-critical P1
  `0`. The app-only revalidation materials share exactly the persisted cache
  row's lifetime; no unapproved TTL was introduced.
