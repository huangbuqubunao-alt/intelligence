# TASK-016C Phase G Implementation Authorization

## 状态与基线

状态：`READY / AUTHORIZED`。本文件只授权一个未来的 Phase G implementation commit；不授权 review、merge、push、release、Phase H/I 或真实服务调用。

- implementation baseline：`bff2b7d514ce4d65f5a2b68d976c5085539e728d`
- governing design：[Phase G Amendment](../docs/TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md)
- accepted design：`c547b7c46afbf254979331c2c56cddb93a8503f2`
- accepted Phase D/E：`2c11faf…`、`9b92946…`
- accepted Phase F provenance / integrated equivalents：`c0268a… -> 61bb0bb…`、`df920cc… -> d059bea…`、`931674e… -> 2f6e30b…`

实施 commit 必须以本授权的 HEAD 或其无关 control-plane-only 后继为唯一 ancestor chain；不得 squash、rebase、amend、rewrite history。仅一个 implementation commit：

```text
TASK-016C Phase G implement trusted prewrite persistence cutover
```

## 目标

```text
PREWRITE_VALIDATE -> ValidatedScoringWritePlan -> verified tmp/fsync/promote
-> atomic SQLite registration -> normal RuntimeOperations scoring-stage cutover
```

这是 PRIMARY-only normal-success path；不实现 repair、retry、budget、unknown/crash recovery、cache recovery/hardening 或 release acceptance。

## 精确允许范围

生产代码仅允许：

- `src/youtube_intel/scoring.py`：enriched F→G aggregate、sealed plan、canonical envelope/structured serializer、pre-write validator、writer/committer；
- `src/youtube_intel/runtime.py`：runtime-owned composition 与 normal scoring-stage cutover；
- `src/youtube_intel/state.py`：无 migration 的 single-transaction trusted scoring registration；
- `src/youtube_intel/quality.py`：仅 sealed trusted-result serialization 或既有 attestation verify 的最小 private helper，不改变 policy/contract。

测试仅允许新 `tests/unit/test_task016c_phase_g.py`，以及为 aggregate completeness、sealed serializer、attestation binding、normal cutover 所必需的既有 Phase F/quality/scoring/runtime/operations tests；可更新 `handoffs/TASK-016C.md`。范围仍不足时停止并报告 `DECISION NEEDED`。

## 严格禁止

- `providers/ollama.py`、`domain.py`、TASK-016B Language Validator、Cloud、Router、Weekly production；
- DB schema、migration、new table、dependency、`pyproject.toml`、`uv.lock`；
- repair/retry/repair budget、REPAIR Judge、unknown/crash recovery engine、cache read/recovery/hardening；
- provider/Judge recall during G persistence、真实 Ollama/network、Cloud fallback、Vault、credentials；
- legacy `RepositoryBackedScoringService` 作为 normal trusted producer；
- merge、rebase、squash、amend、push、tag、release。

## 冻结信任与 PREWRITE 合同

1. G ingress 只接受 exact `PhaseFTrustedScoringSuccess`；bare `ScoreResult`、single `TrustedScoreResult`、single attempt、Mapping/JSON、Artifact/cache/ProviderCall/legacy payload 一律拒绝。
2. 先验证 aggregate capability，再读取字段。必须 enrich 同一 opaque aggregate，封存 canonical ScoringInput、quality input、full PASS result、quality operation、attestation 与 sealed structured-result bytes/hashes；不得以 caller DTO 补入。
3. `PREWRITE_VALIDATE` 必须在零写入状态下重建并验证 request/raw/candidate hashes、same canonical parser raw reparse、candidate/result business binding、provider/model/digest/schema/prompt/operation/language、current runtime-owned `TrustedScoringContext`、current `QualityProvenanceAuthority`、full PASS attestation/H2、config rotation、canonical raw/structured bytes 与 Artifact metadata。
4. raw source 仅为 `success.primary_attempt.final_raw_response`；重算 strict UTF-8 SHA-256。不得 recall provider、payload extraction、caller/cache/Artifact/legacy substitution，或从 result 反推 raw。
5. `ValidatedScoringWritePlan` 必须 opaque/sentinel/exact-type/immutable/non-copyable/non-serializable；只有 prewrite 能 mint，writer/DB boundary 不接收散装 bytes、metadata 或 replacement plan。
6. PREWRITE 成功前绝对零 tmp/final/mkdir/Artifact/ProviderCall/cache/SQLite/stage/response_artifact_id 写入。

## 文件、DB 与 runtime 规则

- 顺序：same-filesystem exclusive tmp → tmp fsync → length/hash verify → no-clobber promote → parent-directory fsync → reopen controlled regular final verify。
- 两 final files 验证后，单一 SQLite IMMEDIATE transaction 才登记 two Artifact rows、在同一未提交 transaction 内插入并完成 scoring + Judge ProviderCall、更新 score/threshold 并 finish job；不得复用 legacy pre-provider reservation。
- DB failure 后 final files 是 unindexed orphan finals：G fail-closed，不覆盖、不删除、不恢复、不重调；H owns recovery。
- normal `RuntimeOperations.scoring_stage` 必须唯一 cutover 到 Phase F → G trusted route；legacy service 仅为 explicit pre-TASK-016C compatibility boundary，不能作为 trusted input 或 normal producer。
- G 不返回/读取 cache hit；只写未来 I 可验证的 normal-success graph。
- duplicate commit 仅在 files/Artifacts/two SUCCEEDED calls/stage/job/video summary 与同一 plan 完全相等时才可 deterministic idempotent success；PENDING/FAILED/partial/legacy/conflict 一律 fail-closed。

## RED-first 测试与 mutation

先新增 RED，再最小 GREEN。至少覆盖：valid success persist；bare/single/Mapping/JSON rejects；raw/candidate/result/request/provider/model/digest/output-language/quality-authority rotation failures；forged plan；Artifact/cache/ProviderCall input rejection；PREWRITE 前零写；exact F raw source；no provider recall；duplicate deterministic behavior；legacy non-entry；ProviderCall request bridge；Artifact ID/hash binding；DB/filesystem/stage ordering failures；no repair/no H recovery/no real network。

Mutation proof 必须删除并恢复：exact success guard (M1)、raw hash (M2)、raw reparse (M3)、candidate/result binding (M4)、runtime authority/context (M5)、ProviderCall request binding (M6)、Artifact content/hash binding (M7)、prewrite-before-write ordering (M8)、bare-result compatibility re-entry (M9)、stage-completion ordering (M10)。每项必须先使对应测试失败，再恢复 GREEN。

## Required offline gates

```bash
uv lock --check --offline
uv sync --locked --offline
uv run --offline pytest tests/unit/test_task016c_phase_g.py -q
uv run --offline pytest tests/unit/test_task016c_phase_f.py -q
uv run --offline pytest -x -q <Phase-A-E trust suites and TASK-016B suites>
uv run --offline pytest -x -q
uv run --offline mypy src
uv run --offline ruff check .
uv build --offline
bash scripts/security_scan.sh
git diff --check
```

无真实网络或模型依赖。handoff 必须记录 direct parent/SHA、范围、RED/GREEN/mutation/gates、禁止操作与剩余 H/I 风险；停止等待独立 review。
