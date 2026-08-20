# TASK-016C Phase G：预写验证、持久化与 Runtime Cutover 修订

## 状态

`DESIGN READY / IMPLEMENTATION NOT AUTHORIZED`

本修订只冻结 TASK-016C Phase G 的实现边界。它不授权实现、真实 Ollama、网络、repair、
retry、崩溃恢复或 cache recovery。

## 已接受基线与 Phase F 等价整合

- 接受的 TASK-016C 设计：`c547b7c46afbf254979331c2c56cddb93a8503f2`
- Phase D accepted：`2c11faf41e17c3b823a39bfd1018c5c876b236c5`
- Phase E accepted：`9b92946a3c156a7c365d808f92f7a1734dcca874`
- 当前 Phase G discovery baseline：`2f6e30bd4720e76a72783974704e8e975b6f60c0`

Phase F 的原 accepted commits 因 conflict-free `cherry-pick` 而具有新的、线性的本地
commit identity。经产品授权，以下 mapping 是本基线的唯一权威整合证明；不得 rewrite
history 来恢复原 SHA：

| Accepted source | 已整合的内容等价 commit | 内容关系 |
|---|---|---|
| `c0268a2157d7b9bb99bdc888b2ee493655bbbaa2` | `61bb0bb…` | tree/content-equivalent |
| `df920cc268f732a5c809ba3d9e0c6b98ea1f44b0` | `d059bea…` | tree/content-equivalent |
| `931674ee475a07a3f494a9d286d40511733361be` | `2f6e30bd4720e76a72783974704e8e975b6f60c0` | tree/content-equivalent evidence |

原提交继续作为 review provenance；Phase G 的祖先要求是上表中的 integration equivalents、
Phase D 和 Phase E 均为当前 HEAD 的祖先。Phase F 状态为 `APPROVED`。

## 1. 仓库事实：legacy 持久化路径

当前 production 路径仍是明确命名的 `PRE-TASK-016C COMPATIBILITY PATH`：

```text
RuntimeOperations.scoring_stage
  -> RepositoryBackedScoringService.score
  -> build_scoring_input / build_scoring_request_identity
  -> reserve_provider_call（SQLite PENDING，发生在 provider 调用前）
  -> OllamaScoringProvider.score（bare ScoreResult）
  -> direct raw.json / structured.json write
  -> SQLiteStateRepository.complete_stage
       （Artifact rows + ProviderCall completion + video score + job completion，一笔 SQLite transaction）
```

真实源码结论如下。

1. `request_hash` 由纯函数 `build_scoring_request_identity()` 以既有
   `build_provider_request_hash()` 创建；legacy `_provider_request()` 会再次断言二者相等。
2. legacy 在 provider 调用前 `reserve_provider_call()`，因此会产生持久化 `PENDING`。
3. raw 目前是 provider 的原始 response string，直接 UTF-8 `write_bytes()` 到
   `scoring/<request_hash>/raw.json`；structured 是 bare `ScoreResult` JSON。
4. legacy 文件写入在 DB registration 前；`response_artifact_id` 在 DB transaction 的
   ProviderCall completion 时产生。
5. `complete_stage()` 的 SQLite transaction 覆盖 Artifact row、已预留 ProviderCall 的
   completion、video score/threshold 与 Job completion；它不覆盖任何文件系统操作。
6. 目前没有 temporary-file → file fsync → no-clobber promote → parent-directory fsync
   协议。故文件与 SQLite 不是跨资源原子；DB 失败后 legacy 会尝试删除本次 direct-written
   文件。
7. legacy cache/recovery 会读取 bare `ScoreResult` 和 legacy raw/structured Artifact。它不是
   TASK-016C trusted input，也不能被新路径升级为 trusted success。

Phase G 必须保留旧记录可供显式 compatibility consumer 读取，但正常 `process` 的 scoring
stage 不得继续经由此路径产生新 trusted success。

## 2. Phase G 的唯一输入与 continuation-completeness 修订

Phase G 的 trusted persistence ingress **只**接受 exact
`PhaseFTrustedScoringSuccess`。拒绝 bare `ScoreResult`、单独 `TrustedScoreResult`、单独
`PrimaryScoringAttempt`、Mapping、JSON、Artifact、cache payload、ProviderCall record、legacy raw
与调用方重建 DTO。

### 2.1 发现并关闭的设计 P1：success 缺少可重验的 quality/input material

现有 Phase F aggregate 已封存 exact primary raw、candidate 与 trusted result 的
request/candidate/raw hashes，但不保存完整 `ScoringInput`、`ContentQualityInput`、
`ContentQualityResult`、`QualityJudgeOperationInput` 与 `QualityPassAttestation`。仅凭现有字段，
G 无法重新计算 request identity 或验证完整 PASS attestation；从 caller 参数补入这些对象会破坏
runtime-owned trust boundary。

因此 Phase G 实现首先以**向后兼容的 F→G continuation enrichment**扩展同一 opaque aggregate，
而不是新增第二条入口：

```text
PhaseFTrustedScoringSuccess
  = TrustedScoreResult
  + PrimaryScoringAttempt
  + canonical ScoringInput bytes/hash
  + canonical ContentQualityInput bytes/hash
  + canonical ContentQualityResult(PASS) bytes/hash
  + canonical QualityJudgeOperationInput bytes/hash
  + canonical QualityPassAttestation bytes/hash
  + sealed cross-bindings
```

这些字段只能由现有 private Phase F seam 在 Gate → Judge → Attestation → Finalizer 成功后一次
mint。aggregate 同时封存由 Finalizer 内 sealed serializer 生成的 canonical structured-result
bytes/hash；serializer 只接收 exact `TrustedScoreResult` 并仅输出 bytes，不会向 G 调用方 expose
bare `ScoreResult`。aggregate 保持 private sentinel、exact type、immutable、non-copyable、non-pickle、
non-serializable、non-subclassable；它只暴露 immutable canonical bytes 或受验证只读视图，G 在
每次使用前均从 bytes 完整重建领域模型。不存在 `from_mapping`、`from_json` 或 caller factory。
旧 aggregate（缺完整 evidence）不能升级，必须 fail-closed；它也不是 legacy compatibility
payload。这是 G 对既有已接受 F seam 的最小 interface extension，不改变 Phase F 的 PRIMARY-only、
zero-persistence 或 no-repair 语义。

## 3. Runtime-owned boundary 与 PREWRITE_VALIDATE

`RuntimeOperations` 继续是唯一组合/minting boundary：其已验证 `AppConfig` 在 composition 时铸造
`TrustedScoringContext` 和 `QualityProvenanceAuthority`，并私有持有 repository、DATA root、当前
Job/video/stage context。Phase G 新的 private `TrustedScoringPersistenceCommitter` 只能由
`RuntimeOperations` 创建；其 public operation 只接收 success aggregate，authority/context、root、
job 和 video 一律来自该 runtime-owned closure，禁止作为 caller 参数替换。

`PREWRITE_VALIDATE(success)` 是 committer 内的 pure in-memory boundary；在它成功前禁止：

- `ProviderCall` reserve/complete/fail；
- Artifact、cache、SQLite、stage、response_artifact_id 写入；
- temporary file、mkdir、parent directory 或任何文件系统写入；
- provider recall、Ollama 调用、legacy cache/raw/Artifact 读取作为 input。

固定验证顺序为：

1. exact `PhaseFTrustedScoringSuccess`、`TrustedScoreResult`、`PrimaryScoringAttempt` 与 enriched
   canonical evidence type/shape；先检查 capability，后读取字段；
2. 从 aggregate canonical bytes 重建 `ScoringInput`、quality input/result/operation/attestation；
   重新执行领域 validation、PASS matrix 与 canonical hashes；
3. 使用当前 runtime-owned `TrustedScoringContext` 重建 canonical scoring identity；核对
   normalized/request hash、provider/model/model digest、schema/prompt/operation、temperature、
   max tokens、description limit、output language。任何 config rotation 都拒绝；
4. 对 `primary_attempt.final_raw_response.encode("utf-8")` 重算 SHA-256，要求等于 attempt 和
   aggregate seal；用 Phase F 同一 `parse_scoring_candidate()` 重 parse，并重算 candidate hash；
5. 核对 raw → candidate、candidate → `TrustedScoreResult` 业务字段、attempt → result request
   identity，以及 aggregate 三个 sealed hashes；不接受 raw A + candidate B + result C；
6. 使用当前 `QualityProvenanceAuthority` 重新验证 quality operation、full PASS result、
   `QualityPassAttestation`、candidate/input/quality-result/attestation hashes 与 Judge H2；
7. 仅以 `success.primary_attempt.final_raw_response` 构造 canonical raw envelope bytes，以 sealed
   serializer 的 structured-result bytes 构造/核对 structured bytes；对两份最终 bytes 做 strict
   parse、canonical reserialize equality、长度/hash 与 deterministic metadata 交叉验证；
8. 只有所有步骤成功，才 mint opaque `ValidatedScoringWritePlan`。

Finalizer 不因 aggregate 存在而降低验证；它仍只接受 candidate 与既有 quality/authority inputs，
不信任 raw，也不创建 raw provenance。

## 4. Canonical raw envelope 与 write plan

### 4.1 唯一 raw 表示

唯一 provider raw 值是 bounded、strict UTF-8 decoded 的完整 Provider HTTP JSON response string：
`success.primary_attempt.final_raw_response`。其 request binding 是：

```text
raw_response_hash = SHA-256(final_raw_response.encode("utf-8"))
```

它不是 `payload["response"]`、candidate、bare `ScoreResult`、缓存内容、legacy Artifact 或
重新序列化的 provider JSON。raw envelope 以 canonical JSON 包含该 exact string、完整 candidate、
finalized result binding、完整 PASS result、完整 attestation 与当前 provenance；G 对 envelope 做
canonical reserialize equality。G 不得 recall provider，也不能由 `TrustedScoreResult` 反推 raw。

### 4.2 `ValidatedScoringWritePlan`

plan 是 opaque、sentinel-minted、exact-type、immutable、non-copyable、non-serializable、
process-memory-only 的 write capability，不是 authority、DTO、cache identity 或 persistence record。
只有 PREWRITE_VALIDATE 可创建，writer/registration API 不接受散装 bytes、metadata、Mapping 或
replacement plan。它冻结：

- exact Phase F request/candidate/raw/quality/attestation seals；
- canonical raw-envelope 与 structured bytes、length、SHA-256；
- raw/structured `ArtifactWrite` keys/IDs/paths/provider/model/producer versions/retention；
- scoring ProviderCall request/completion material 与 quality Judge H2 completion material；
- scoring summary、job/video/pipeline identity 与 current runtime provenance。

raw 使用既有 `SCORING_RAW`，structured 使用既有 `SCORING_STRUCTURED`；不新增 Artifact kind、
DB table、migration 或独立 cache record。producer versions 固定为
`scoring-raw-content-quality-v1` 和 `scoring-structured-content-quality-v1`。该 normal-success
commit 仅写入未来 I 可验证的原料；G 不读取或返回 cache hit。

## 5. ProviderCall 与 Artifact 绑定

scoring ProviderCall 的 request identity 必须由同一 `build_scoring_request_identity()` 与既有
`build_provider_request_hash()` 得到，且严格等于 `success.scoring_request_hash`；不得复制
`state.py` hash 算法。operation=`local-scoring`，provider/model/prompt/schema 与 current scoring
context 精确相等。Judge ProviderCall 的 H2 来自 attestation 的 frozen
`local-content-quality-v1` operation identity；二者均只在 G 的成功 registration transaction 内
从无记录状态插入并立即完成，不能在 F 或 PREWRITE 前 reserve。

两个 completed ProviderCall 均只可引用同一个 verified composite raw-envelope Artifact ID：该
Artifact 同时保存 scoring exact raw、full quality PASS evidence 与 their cross-binding。structured
Artifact 保存 canonical finalized `ScoreResult`。这不是将 Judge raw response 伪装为 scoring raw：
raw envelope 明确只保存 scoring provider exact response，Judge 的可验证事实是其 canonical
operation/result/attestation H2 binding。任何 legacy ProviderCall + new trusted result 的拼接均拒绝。

## 6. 文件与 SQLite 一致性策略

Phase G 不宣称跨 filesystem/SQLite 原子。它冻结可判定、fail-closed 的 normal-success protocol：

```text
PREWRITE_VALIDATE -> WRITE_PLAN_CREATED
  -> same-filesystem exclusive tmp write (raw, structured)
  -> fsync each tmp -> hash/length verify
  -> no-clobber atomic promote each final -> fsync each parent directory
  -> reopen controlled regular finals -> hash/length/path verify
  -> one SQLite IMMEDIATE transaction
       insert Artifact rows
       insert transient PENDING scoring + Judge calls
       complete both ProviderCalls against raw Artifact
       update score/threshold and finish SCORING job
  -> COMMITTED
```

tmp names bind operation/request hash plus an unpredictable component; paths remain under DATA, same filesystem,
exclusive-create, no symlink, no cross-device rename and no overwrite. Existing final paths are idempotent only
when controlled regular file, same operation/key/path/length/hash and same plan; otherwise reject. The new
repository method atomically creates and completes the two calls **inside the same uncommitted transaction**.
Thus no observable PENDING is written before PREWRITE_VALIDATE, and no pre-reservation is inherited from legacy.
It rechecks the job lease/status/target stage and all Artifact/ProviderCall identities before commit.

If a file promotes but SQLite fails, files are verified but unindexed orphan finals: not Artifact, cache, ProviderCall
success or stage completion. G stops fail-closed and never deletes/overwrites a final. H alone may later classify
or recover that state. If SQLite commits, the DB graph is all-or-nothing; a crash after commit is a future I/H
verification concern, not a reason for G to re-call providers. G may only clean its own unpromoted temporary files
on a known local write failure.

## 7. Runtime cutover、legacy isolation与最小幂等性

Phase G replaces the normal `RuntimeOperations.scoring_stage` producer route with:

```text
build_scoring_input
-> OllamaScoringProvider.primary_attempt
-> RuntimeOperations.run_primary_trusted_scoring
-> PhaseFTrustedScoringSuccess
-> TrustedScoringPersistenceCommitter.commit
```

There is exactly one normal production trusted route. `RepositoryBackedScoringService` remains only an explicitly
named pre-TASK-016C compatibility reader/route, must not be selected by normal `process`, and can neither feed
Phase F/G nor upgrade bare data to trusted state. `RuntimeOperations._load_scoring` may consume a committed trusted
structured result for the downstream note compatibility boundary only after its raw-envelope/Artifact/ProviderCall
provenance is verified; it must not turn legacy cache data into a new trusted input. Full derived cache hit/recovery
belongs exclusively to I.

Minimal G idempotency is intentionally narrow. A repeat of the **same in-memory plan** may return the already
committed result only after it proves the complete committed graph (two Artifact records, two SUCCEEDED calls,
raw response artifact IDs, stage/job/video summary, paths and hashes) equals the plan. Any existing PENDING,
FAILED, partial, legacy, hash/config conflict, missing file or different owner is fail-closed with no provider/Judge
recall and no recovery. Cross-process retry, unknown state reclaim and cache recovery remain H/I.

## 8. Failure matrix

| Failure | Writes before failure | G result | H/I ownership |
|---|---|---|---|
| exact-type, raw/candidate/result, request, quality/attestation, authority/context rotation mismatch | none | fail-closed | no recovery action in G |
| serializer/envelope/structured canonical mismatch | none | fail-closed | none |
| tmp write/fsync/hash/path/symlink failure | only current operation tmp, if any | fail-closed; clean only own tmp | H handles unknown leftovers |
| promote/parent fsync/final verification failure | possibly verified orphan final(s) | fail-closed; never overwrite/delete final | H classifies/recovery |
| DB artifact/call/stage transaction failure | verified orphan finals only | fail-closed; DB rollback | H recovery |
| conflict/duplicate complete graph | no new write | return only proven idempotent result | I later cache validation |
| existing PENDING/FAILED/partial/legacy graph | none | fail-closed; no retry/reservation | H/I only |
| provider/Judge recall request during G | none | programming-contract failure | forbidden |

Repair, retry, repair budget, unknown-state recovery, crash recovery engine, cache recovery/hardening, real
network and release acceptance are prohibited in G.

## 9. Required implementation scope

| File | Necessity |
|---|---|
| `src/youtube_intel/scoring.py` | enrich F→G aggregate, construct/prevalidate opaque plan, canonical envelope/structured serialization, safe file writer and trusted committer |
| `src/youtube_intel/runtime.py` | sole composition/minting owner and normal scoring-stage cutover; bind private context/job/repository without caller authority |
| `src/youtube_intel/state.py` | one new no-migration atomic registration method that inserts/completes the two calls and scoring stage in one transaction; no pre-reservation |
| `src/youtube_intel/quality.py` | only minimal reusable verification/export surface if needed for full attestation reconstruction; no quality policy change |
| focused Phase G tests and existing Phase F/quality/runtime regressions | RED-first security, ordering, file, DB and cutover proof |
| control-plane/handoff documents | evidence and scope recording |

`providers/ollama.py`, `domain.py`, dependencies, `uv.lock`, DB schema/migrations, Cloud, Router, Weekly
production and TASK-016B Language Validator are forbidden unless a separately reviewed amendment authorizes them.

## 10. Adversarial self-review result

The amendment explicitly rejects raw A/candidate B, candidate A/result B, success A/current context B,
forged plan, bare/legacy/cache/Artifact/Mapping/JSON input, copy/pickle/subclass/proxy capabilities,
provider recall, raw reserialization, configuration rotation and duplicate partial commit. The initial
continuation-completeness gap is closed by the enriched opaque aggregate rather than caller input.

Known P0: 0

Known P1: 0
P2: cross-resource crash recovery remains deliberately deferred to H/I; G records only deterministic orphan/commit
states and fails closed.
