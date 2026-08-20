# TASK-016C Phase F — Runtime Integration Amendment Round 2

## 状态

`DESIGN READY / IMPLEMENTATION NOT AUTHORIZED`。本修订以已批准的 Phase E 链
`2c11faf` → `8aa9f0b` → `94c5dac` → `1293d87` → `9b92946` 为唯一前提；仅修订
设计与控制面，不授权代码、测试、持久化或 public runtime cutover。

## 1. 唯一阶段归属

| Phase | Owner | Allowed behavior | Forbidden behavior | Entry condition | Exit condition |
|---|---|---|---|---|---|
| F | Candidate-only in-memory runtime integration | PRIMARY-only candidate → schema → language → quality → attestation → Finalizer → `TrustedScoreResult` 的内存 seam | repair/retry/budget/recovery、Artifact、ProviderCall success、cache、DB/filesystem、默认 runtime cutover | E 已批准且本 Amendment 获独立设计审查 | isolated seam 的 PRIMARY 路径与 14 项测试矩阵通过；没有持久化或 legacy upgrade |
| G | Pre-write validation + persistence registration boundary | `TrustedScoreResult` → pre-write validation → `ValidatedScoringWritePlan` → 文件提交协议 → SQLite registration → formal Artifact/ProviderCall success → production cutover | repair/retry/recovery policy、未验证输入、裸 `ScoreResult`、独立 cache identity | F 已接受；原子文件与 DB 设计/授权齐备 | 只有已 promote、hash-verified 的 plan 被原子登记，正式 runtime 才可 cut over |
| H | Repair/retry/recovery/budget orchestration | PRIMARY/REPAIR 预算、repair attempt identity、unknown reservation/crash recovery、fail-closed retry policy | 绕过 F/G 验证、超预算自动重调、把 unknown 当 cache miss | G 已接受 | primary/repair/recovery 事件顺序、预算与 crash matrix 独立通过 |
| I | Production hardening / release acceptance | derived cache verification/recovery、adversarial/crash/bypass 复核、性能与完整 release evidence | 未经验证的历史升级、公开发布或 Production Go 的自动声明 | H 已接受 | 独立 release acceptance；另行处理现有公开分发 No-Go |

旧的 J/K 标签已并入 I；不得再把 cache recovery、crash verification 或 acceptance 另列为与
I 重叠的实施阶段。每个 capability 仅由上表一阶段拥有。

## 2. Phase F 的新定义：非生产、隔离的内存可信组合 seam

Phase F 是 **NON-PRODUCTION / ISOLATED IN-MEMORY TRUSTED COMPOSITION SEAM**，唯一
允许的成功流是 PRIMARY：

```text
ScoringInput
  -> candidate-only Provider transport/parser
  -> ScoringCandidate
  -> schema validation
  -> frozen TASK-016B Language Validator
  -> Deterministic Safety Gate
  -> Local Content Quality Judge (PRIMARY)
  -> ContentQualityResult(PASS)
  -> QualityPassAttestation
  -> TrustedScoringFinalizer
  -> TrustedScoreResult (memory only)
```

任一 PRIMARY 节点失败均 fail-closed；F **不得**自动 repair、retry、重置预算、创建 repair
attempt identity 或处理 unknown reservation。以上职责全部属于 H。F 也不改变
`RuntimeOperations.process` 或 `RuntimeOperations.scoring_stage()` 的正式 persisted stage。

现有 `RuntimeOperations → RepositoryBackedScoringService → OllamaScoringProvider.score() →
bare ScoreResult → persistence` 仍是 **PRE-TASK-016C COMPATIBILITY PATH**。它不是 F 的
trusted path，不能被宣称已完成迁移或 production cutover。

### Legacy isolation 与最小 fail-closed guard

仅靠命名不足以保证新 seam 不包装 legacy 输出。因此 F 的最小授权包含一项**seam 入口
exact-type guard**：in-memory helper 只接收 `ScoringCandidate` 和 Phase E 的 opaque
capabilities；传入 bare `ScoreResult`、legacy provider result、Mapping、JSON 或兼容 service
输出必须拒绝。该 guard 位于允许修改的 `scoring.py`，不调用、实例化或改写
`RepositoryBackedScoringService`。

这不是 process-level dispatch guard：F 无权改变默认 persisted route。任何将 public
`RuntimeOperations.process` 切换到新 trusted path 的 dispatch 改动只能在 G 获得 persistence
boundary 授权后实施。G cutover 前，legacy `ScoreResult` 不得进入、包装为或被视作
TASK-016C trusted result。

## 3. Provider contract

F trusted path 的 Provider 只可暴露 candidate-only PRIMARY 方法：

```text
ScoringInput -> provider transport/parser -> ScoringCandidate
```

- Provider 不得构造 `ScoreResult`、`TrustedScoreResult`、attestation、Artifact、cache 或
  ProviderCall completion。
- 最小 `providers/ollama.py` 修改仅抽离 candidate parser/contract；既有 transport、loopback
  guard、model/digest checks、prompt/request body、timeout、safe error 清洗及 no-download /
  no-fallback 行为不变。
- F 不定义 provider repair method；任何 repair transport 调用、repair prompt 或预算编排由 H
  单独设计、授权和实现。

## 4. TrustedScoreResult supersession

本 Amendment 正式 supersede 旧的 `TrustedScoringFinalizer -> ScoreResult` 表述：

```text
TrustedScoringFinalizer -> TrustedScoreResult
```

`TrustedScoreResult` 内部保存已验证的 `ScoreResult` 业务字段，但它是 F–I 唯一的 trusted
pipeline result。裸 `ScoreResult` 只允许位于明确命名的 **LEGACY / EXTERNAL COMPATIBILITY
BOUNDARY**；它不能重新进入 trusted pipeline，也不能升级为 wrapper。

**No internal unwrap is authorized in Phase F-G-H.** 若未来确实需要外部兼容 unwrap，必须以
新的 boundary 名称、调用方和 fail-closed non-reentry 规则取得独立授权；本 Amendment 不授权。

## 5. scoring.py 与 runtime.py 边界

F 可在 `scoring.py` 新增纯内存 trusted scoring helper。它只能组合 candidate、已有 quality
authority、已有 `TrustedScoringContext` 与 `TrustedScoringFinalizer`；它不得调用或实例化
`RepositoryBackedScoringService`，更不得触发 reservation、cache、Artifact write、ProviderCall
completion 或 stage completion。

`runtime.py` 只可完成 composition wiring：从已验证的 `AppConfig` 使用现有
`QualityProvenanceAuthority`、现有 `TrustedScoringContext`、candidate Provider 和 Finalizer 建立
这个测试/内存 seam。正式 compatibility production path 与新 seam 必须有不同且显式的入口，
两者不得共享 trusted-result 语义。

## 6. F/G 持久化边界

F 输出的 `TrustedScoreResult` 仅留在内存。F 禁止 Artifact、ProviderCall success、
`response_artifact_id`、cache、SQLite、formal file、stage advance 和 filesystem mutation。

G 才拥有以下唯一写入链：

```text
TrustedScoreResult
  -> PREWRITE_VALIDATE
  -> ValidatedScoringWritePlan
  -> temporary write / fsync / hash verification / promote / directory fsync
  -> SQLite registration
  -> formal Artifact + ProviderCall success
  -> production runtime cutover
```

G 才能将 trusted in-memory result 接到 persisted runtime；H/I 不能反向扩大 F 的写入权限。

## 7. Phase F test acceptance matrix

未来 F task card 必须用 TDD 覆盖以下 14 项：

1. Provider trusted path 返回 `ScoringCandidate`，不返回 `ScoreResult`。
2. Candidate 保留 score/dimensions/reason/topics/should_summarize 业务字段。
3. PRIMARY 成功路径产生 `TrustedScoreResult`。
4. Quality failure 不产生 `TrustedScoreResult`。
5. Invalid attestation 不产生 `TrustedScoreResult`。
6. bare `ScoreResult` 被 trusted seam 拒绝。
7. 新 seam 不实例化或调用 `RepositoryBackedScoringService` 路径。
8. 不产生 Artifact。
9. 不产生 ProviderCall success。
10. 不发生 DB/cache/filesystem mutation。
11. TASK-016B language ordering 不变。
12. Phase C/D/E trust tests 继续通过。
13. F 中没有 repair/retry 调用。
14. legacy compatibility `ScoreResult` 不能升级为 `TrustedScoreResult`。

## 8. 未来 F 的最小允许范围

- `src/youtube_intel/providers/ollama.py`：candidate parser/contract；
- `src/youtube_intel/scoring.py`：纯内存 seam 与 exact-type legacy rejection；
- `src/youtube_intel/runtime.py`：仅 composition wiring；
- `src/youtube_intel/quality.py`：必要的 Phase E Finalizer glue；
- `src/youtube_intel/domain.py`：必要 typing/contract；
- 对应测试与 TASK-016C handoff。

禁止 `state.py`、DB schema/migration、Artifact/cache/persistence、ProviderCall completion、
filesystem protocol、repair/retry/recovery、config/CLI、Language Validator、依赖/lockfile、真实
Ollama/network/cloud/Vault，以及 Phase G–I 的任何代码。

## 结论

`DESIGN READY / IMPLEMENTATION NOT AUTHORIZED`。本 Round 2 关闭阶段归属、repair ownership、
legacy isolation 和 Finalizer output contract 的设计冲突；仍须独立设计审查后，才可生成
Phase F implementation authorization。
