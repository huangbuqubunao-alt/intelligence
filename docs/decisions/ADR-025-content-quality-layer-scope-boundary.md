# ADR-025：Content Quality Layer 职责、可信终结与恢复边界

## Status

Proposed；2026-08-14 Round 4.6 修订待 Independent Design Review

## Date

2026-08-13

## Context

TASK-016B 已按 ADR-024 验收并冻结。Language Validator 只负责 script mismatch、
自然语言结构验证与无法证明时 fail-closed。它不负责判断评分理由是否有价值、是否由
identifier 或实体名称堆叠而成，也不负责事实性实体识别。

TASK-016C 建立独立 Content Quality Layer。但第一版设计仍有三处不可接受的信任缺口：

1. Deterministic Gate 试图识别 acronym / identifier，重新引入了 TASK-016B 已拒绝的
   token、技术词和实体启发式；
2. Provider、repair 与 cache recovery 仍可能直接恢复或构造 `ScoreResult`，没有唯一的
   可信构造点；
3. producer version 与 request identity 只能证明“当前策略本应运行”，不能证明某一
   candidate 实际获得了完整的 Quality `PASS`。

本修订把 Deterministic Gate 缩到可机械证明的三个错误，把 `ScoreResult` 的创建权集中到
`TrustedScoringFinalizer`，并引入可恢复、可交叉验证的 Quality PASS attestation。

Round 4.6 进一步关闭持久化前的信任缺口：Finalizer 返回可信 `ScoreResult` 后，应用必须
先构造 canonical raw/structured bytes，并在任何 temporary file write 之前重新解析、完整
验证和交叉绑定这些最终 bytes。只有这一 pre-write boundary 成功后，才能创建纯内存
`ValidatedScoringWritePlan` 并进入 Round 4 已冻结的文件提交协议。SQLite registration 只在
文件 durable promote 后做防御性复核，不能承担或替代“首次写盘前验证”。

ADR-023 原先把 `TASK-016C` 分配给 Local Deep Analysis Provider。该任务编号分配已被本
ADR supersede：`TASK-016C` 只表示 Content Quality Layer。Local Deep Analysis 保持产品
方向，但当前状态为 `TBD / UNASSIGNED`，不得从旧清单推断已获设计或实现授权。

## Decision

### 1. 职责边界

TASK-016C v1 负责：

- identifier-only、entity-only 与 identifier-stuffing 的内容质量判定；
- low-information scoring reason detection；
- minimal claim validation；
- 相对于当前 `ScoringInput` 的 grounding 与 usefulness confidence；
- 在不能可靠证明 `PASS` 时返回 `REJECT` 或 `UNCERTAIN` 并 fail-closed。

TASK-016C 不负责：

- language、script 或 grammar validation；
- 品牌、公司、产品或技术实体的事实识别；
- 事实真伪核验；
- Web、Wikipedia、外部 API、远程知识库或用户知识库查询；
- 修改、替换或重新解释 TASK-016B Language Validator。

### 2. Deterministic Gate 的封闭范围

Deterministic Gate 只能产生以下三种拒绝：

```text
EMPTY_CONTENT
CONTROL_CHARACTER_INVALID
EXACT_REPETITION
```

`EXACT_REPETITION` 只检查 `reason`，机械算法固定为：

1. 以固定 ASCII whitespace 集 `U+0009..U+000D` 与 `U+0020` trim `reason` 首尾；
2. 只按 LF `U+000A` split；
3. 删除值为精确空字符串的 segment，不额外 trim segment；
4. 若任意两个相邻 segment 按 code point 完全相等，则拒绝。

不得 casefold、lowercase、规范标点、Unicode normalization、tokenize、模糊匹配、NLP 或
语义归并。内部空格、大小写或标点不同即不相等。

`CONTROL_CHARACTER_INVALID` 的检测发生在上述 trim/split 和任何其他 normalization 之前。
它拒绝所有 Unicode General Category `Cc`，但明确允许 TAB `U+0009` 和 LF `U+000A`；
此外无论 Unicode category 如何，明确拒绝 ZERO WIDTH SPACE `U+200B` 与 BOM / ZERO WIDTH
NO-BREAK SPACE `U+FEFF`。因此 NULL `U+0000` 必须拒绝。严格 UTF-8/Unicode 解码先于该
扫描；解码失败直接 schema invalid，不进入 Gate。

Gate 明确禁止：

- identifier list / acronym detection；
- 技术词、品牌、公司或产品判断；
- token 数量、token 位置、大小写、词尾规则；
- POS、dependency、NER 或其他语言学分析；
- 直接产生 `PASS`。

因此 `API SDK GPT LLM`、`Docker Kubernetes Terraform`、
`General Dynamics Corporation` 以及所有结构合法但语义未知的文本都必须 `CONTINUE`
到 Local Judge。

### 3. 双层质量判定

```text
schema-valid ScoringCandidate
        |
        v
frozen TASK-016B Language Validator
        |
        v
Deterministic Safety Gate
        |
        v
Fixed Local Content Quality Judge
        |
        v
ContentQualityResult: PASS | REJECT | UNCERTAIN
```

Local Judge：

- 复用当前 `local_scoring` 的固定 Ollama provider/model 与 expected digest；
- 仅允许既有受限 loopback Adapter；
- 固定 policy、prompt 与 schema version；
- 使用结构化输出、`temperature=0`、`stream=false`、`think=false`、无 tools；
- 禁止下载、model pull、远程地址、用户动态 prompt、cloud 或 network fallback；
- 只能返回有限枚举、固定 confidence 与应用预先建立的 evidence ID；
- 不得自报 excerpt、provider、model、digest、version、request hash 或自由 diagnostics。

Judge 的 `PASS` 只证明候选在当前有界输入中具有最小可用、可 grounding 的评分价值，
不证明外部事实真实。

### 4. 唯一可信 ScoreResult 构造点

ADR-025 明确 supersede `docs/SYSTEM_DESIGN.md` 中旧的
`ScoringProvider.score(ScoringInput) -> ScoreResult` 语义契约。TASK-016C 生效后的唯一
Provider 契约是：

```text
ScoringInput -> Provider Adapter -> ScoringCandidate
```

Provider、repair、Artifact reader 和 cache recovery 均不得直接构造、反序列化为或返回
可信 `ScoreResult`。

`ScoringCandidate` 不是新业务结果，而是现有评分业务字段的不可信 wrapper。它必须保持
现有精度与可选性：`score: float`、`dimensions: ScoreDimensions | None`，并原样保留
`reason`、`topics`、`should_summarize`。不得把 score 收窄为 integer、把 dimensions 变成
必填，也不得新增、删除或改变任何 `ScoreResult` 业务字段。Candidate 只移除可信
provenance，并增加“不可信、尚未 final”这一类型边界。

`TrustedScoringFinalizer` 是唯一允许创建 `ScoreResult` 的应用边界。它必须同时接收并
重新验证：

1. canonical `ScoringCandidate`；
2. 当前可信 scoring context（provider/model/output language/prompt/schema）；
3. 从不可信输入重建、通过完整 PASS matrix 且已 canonicalize 的 `ContentQualityResult`；
4. 完整且有效、绑定该 result hash 的 Quality PASS attestation；
5. 当前 scoring request、quality input 与 Judge ProviderCall identity 的重算结果。

只有全部一致时，Finalizer 才从业务字段和可信 context 新建 `ScoreResult`。三条路径均
必须经过它：

- primary scoring candidate；
- 唯一 repair candidate；
- persisted cache recovery。

Cache reader 只能恢复 untrusted persisted payload，再由 Finalizer 重建 `ScoreResult`。
禁止把 `model_copy(update=...)`、`model_construct()` 或已构造 instance 当成可信捷径。

### 5. Quality PASS attestation

完整 PASS decision 的唯一 canonical binding 定义为：

```text
validated_quality_result
  = ContentQualityResult.model_validate(untrusted mapping/JSON)
  -> cross-field PASS matrix validation
  -> normalized signals/evidence IDs

quality_result_hash
  = SHA256(
      canonical_json(validated_quality_result.model_dump(mode="json"))
    )
```

`canonical_json` 必须复用项目现有规则：UTF-8、`ensure_ascii=False`、key lexicographic
sorting、紧凑 separators `(",", ":")`。Signals 按枚举值排序去重，evidence IDs 按稳定 ID
排序去重；完成这些 normalization 后重新执行完整领域校验，再序列化。Hash 输入是完整
`ContentQualityResult`，不是 PASS 所需字段子集，覆盖 schema/policy/prompt version、status、
decision source、三项 confidence、全部 signals、rejection reason（模型字段 `reason`）、
evidence IDs、candidate/input bindings、Judge provenance 及模型未来增加的所有 canonical
字段。Unchecked instance、`model_copy`、`model_construct`、Mapping 或 JSON 都必须先重建并
通过上述两层验证，不能直接参与可信 hash。

每个最终 `PASS` 必须先在内存中构造并验证 `quality-pass-attestation-v1`，至少绑定：

- `candidate_hash`；
- `quality_input_hash`；
- `quality_result_hash`；
- quality policy version；
- scoring 与 quality schema version；
- scoring 与 quality prompt version；
- Judge provider；
- Judge model；
- Judge expected model digest；
- Judge operation identity、request hash 与 attempt role；
- 三项 confidence 与已验证 evidence IDs。

Attestation 由应用根据已验证 Judge response 和可信配置构造，模型不能自报。其 canonical
payload 计算 SHA-256 `attestation_hash`。Attestation 不是第二份 PASS decision；其中既有
confidence/evidence mirror 只能与完整 validated result 做精确 equality binding，不能独立
解释、补写或覆盖 result 的 signals/confidence/reason。该内存对象不是 Artifact、cache entry
或成功 ProviderCall，只是 Finalizer 输入。

v1 不新增 Artifact kind 或数据库字段。Finalizer 成功且最终 bytes 已通过 pre-write validation
并形成内存 plan 后，正式 `SCORING_RAW` 使用固定 quality-qualified composite envelope，保存
最终 scoring provider raw response、完整 `ScoringCandidate` / finalized scoring binding、可完整
重建的 validated `ContentQualityResult(PASS)`、该 attestation，以及必要的 request/config/
producer/ProviderCall provenance；`SCORING_STRUCTURED` 仍保持 canonical `ScoreResult` JSON。
Attestation 作为 raw envelope 的受版本化组成部分与 raw Artifact 一起持久化，不伪造第三种
Artifact kind。

Attestation integrity 是现有本地信任模型内的交叉一致性，不是对拥有 SQLite 与 DATA
写权限的攻击者提供密码学不可伪造性。恢复时必须从 raw envelope 重建并完整验证
`ContentQualityResult(PASS)`，重算 quality-result/candidate/input/attestation hash，核对当前
配置、Artifact metadata/content hash，以及对应 Judge ProviderCall 的
`SUCCEEDED` 状态和相同 response artifact。任一不一致都不得成为 cache hit。

### 6. Judge 调用预算与 operation identity

每个 scoring request 的质量 Judge 预算冻结为：

- `PRIMARY` candidate：最多一次；
- `REPAIR` candidate：最多一次；
- 总计最多两次；scoring repair 自身仍最多一次。

每次 Judge 使用两个不可混用的 hash layer。Layer 1 是 normalized input identity：

```text
scoring_request_hash
attempt_role (PRIMARY | REPAIR)
candidate_hash
quality_input_hash
policy_version
prompt_version
schema_version
judge_provider/model/digest
```

```text
H1 = judge_normalized_input_hash
   = SHA256(canonical_json(validated QualityJudgeOperationInput))
```

Layer 2 必须直接复用 ADR-003 与现有 `build_provider_request_hash(...)`：

```text
H2 = judge_request_hash
   = build_provider_request_hash(
       operation="local-content-quality-v1",
       normalized_input_hash=H1,
       provider=trusted_judge_provider,
       model=trusted_judge_model,
       prompt_version=quality_prompt_version,
       schema_version=quality_schema_version,
     )
```

PRIMARY 与 REPAIR 都使用同一固定 operation；`attempt_role` 已在
`QualityJudgeOperationInput` 中，因此 H1/H2 对两个 role 分别稳定且不同。H1 是 H2 的输入，
不是 ProviderCall key；H1 与 H2 语义不同且正常预期不相等，任何位置都不得互相替代。冻结
等式：

```text
QualityPassAttestation.judge_request_hash
  == Quality Judge ProviderCall.request_hash
  == DerivedScoringCacheView.quality_provider_call_request_hash
  == H2
```

不得修改 `build_provider_request_hash` 或 ADR-003 的六维语义（operation、normalized input
hash、provider、model、prompt version、schema version）。

调用前必须以 H2 在既有 ProviderCall store 原子保留 identity。Restart 必须从同一可信输入
重建 H1，再经既有 builder 得到同一 H2；若不一致则 fail-closed。已存在或 unknown 的 H2
不得因重新计算 H1 而派生一个替代 ProviderCall identity。TASK-016C 的 one-shot wrapper
必须先只读查询 identity。记录不存在时才可 reserve 并外部调用；live PENDING 只能等待或
停止，expired PENDING 只允许以完整验证的 deterministic PASS raw envelope 与 promoted
files 进入专用 verified-file recovery 分支，绝不进入 takeover 后外部调用。它不得把既有 Repository 对
expired `PENDING` /
`FAILED_RETRYABLE` 的通用 takeover 能力用于 Judge。恢复规则：

| 持久状态 | 行为 |
|---|---|
| 无记录 | 可保留并调用一次 |
| `SUCCEEDED` 且 PASS attestation 完整 | 恢复结果；Judge 调用为 0 |
| `FAILED_*` | 该 role 已消费；不得再次调用 |
| live `PENDING` | 等待或 fail-closed；此时通用 Repository 不执行 artifact recovery |
| expired `PENDING` + 完整验证的 deterministic PASS promoted files | 原子 recovery claim 后只恢复/登记，不重新调用 |
| expired `PENDING` 且无完整 PASS promoted files | 外部结果未知；fail-closed，不重新调用 |
| record / attestation / Artifact 相互矛盾 | integrity failure；fail-closed，不重新调用 |

Primary Judge 明确 `REJECT` / `UNCERTAIN` 时，可用现有失败状态和有限安全码记录该 role
已消费，然后进入唯一 repair。若进程在外部调用后、持久完成前崩溃，不能证明调用是否
发生，必须按 unknown state 停止；只有显式的新产品操作 identity 才能再次尝试，自动
restart/retry 不得重置预算。

### 7. Confidence 与组合契约

`ContentQualityResult` 使用三项独立有限 confidence：

- `decision_confidence`；
- `grounding_confidence`；
- `usefulness_confidence`。

值只允许 `LOW | MEDIUM | HIGH`。`PASS` 固定门槛为：

```text
decision_confidence == HIGH
grounding_confidence in {MEDIUM, HIGH}
usefulness_confidence in {MEDIUM, HIGH}
```

并且必须同时具有 `MINIMAL_CLAIM_PRESENT`、`GROUNDING_PRESENT`、至少一个当前 registry
evidence ID，且不得含 rejection reason 或负向冲突 signal。完整 status/reason/signal
矩阵由 Interface Design 冻结；非法组合必须在应用 wrapper、JSON restore 和 Finalizer
三处 fail-closed。

### 8. Repair 与持久化顺序

```text
candidate
  -> schema validation
  -> language
  -> quality
  -> in-memory PASS attestation
  -> TrustedScoringFinalizer
  -> construct canonical raw/structured bytes
  -> pre-write reparse + full validation
  -> in-memory ValidatedScoringWritePlan
  -> temporary file write
  -> file fsync
  -> hash/length verification
  -> no-clobber promote
  -> parent-directory fsync
  -> final file verification
  -> atomic SQLite registration
```

primary 或 repair 都必须完整执行这一顺序；repair 只是产生新的 candidate，不能跳过任何
节点。schema、language 或 quality 失败共享同一个 repair budget。第二次仍非 `PASS` 或
Judge 不可用时返回 `INVALID_RESPONSE`。

Finalizer 前严格禁止：

- 正式或已登记的 `SCORING_RAW`；
- `SCORING_STRUCTURED`；
- 任何成功 `response_artifact_id`；
- scoring 或 quality ProviderCall `SUCCEEDED`；
- 当前运行可返回的 cache hit。

该禁止项约束当前执行产生的新状态转换。Cache recovery 可以只读观察历史原子提交留下的
`SUCCEEDED`/Artifact/attestation，但在当前 Finalizer 成功前不得把它返回为 cache hit、
不得写入新完成状态，也不得推进当前 stage。

Finalizer 成功不直接授权文件写入。应用先从 finalized `ScoreResult`、完整 validated
`ContentQualityResult(PASS)`、attestation 与当前可信 provenance 构造 canonical raw/structured
bytes，再执行 pre-write validation：

- 从最终 raw bytes 严格重建完整 `ContentQualityResult`，重跑 model/domain validation 与
  PASS matrix，重算并核对 `quality_result_hash`；
- 核对 candidate/input binding、Judge ProviderCall H2、finalized `ScoreResult`、
  producer/version/request/config provenance，以及 raw envelope 中完整 attestation；
- 拒绝 summary-only、decision 缺失，或 signals/confidence/evidence/source 任一篡改；
- 从 structured bytes 严格重建可信 `ScoreResult`，核对 request/provider/model/language/
  prompt/schema 与 Finalizer 输出；
- 对两份 bytes 做 canonical reserialization equality，再计算期望长度与 SHA-256，并核对
  planned `ArtifactWrite` metadata。

两份最终 bytes 均通过后，应用才可创建 `ValidatedScoringWritePlan`。该对象只存在于当前
进程内，不是 DB row、Artifact、cache identity、migration 或可恢复文件。它完整绑定：

- finalized trusted `ScoreResult`；
- canonical raw/structured bytes；
- raw/structured `ArtifactWrite` 的 expected key/path/version/producer metadata；
- 两份 bytes 的 expected length 与 SHA-256；
- `QualityPassAttestation` 与 `quality_result_hash`；
- scoring ProviderCall identity、quality Judge ProviderCall H2；
- 当前 request/config provenance。

Writer 只能接受由该 pre-write boundary 创建的 plan，不接受调用方直接传入 bytes 或
`ArtifactWrite`。Pre-write validation 失败时，禁止创建 plan，且不得产生 tmp/final file、
Artifact、ProviderCall completion、`response_artifact_id`、stage advance 或 cache hit。

获得 plan 后，Round 4 已冻结的文件提交协议固定为：

```text
ValidatedScoringWritePlan
  -> same-filesystem temporary file write
  -> fsync each temporary file
  -> verify byte length and SHA-256 against planned ArtifactWrite
  -> no-clobber atomic rename/promote to deterministic final path
  -> fsync every affected parent directory
  -> re-open final files and verify type/path/length/SHA-256
  -> one SQLite transaction
```

Raw/structured 两个文件都必须在同一 DATA filesystem 上完成该协议。Promote 必须
no-clobber：若 final path 不存在才可原子创建；若已存在，只能在其普通文件、受控路径、
长度和 hash 与本次计划全部相同后视为幂等成功，绝不覆盖或删除已有正式文件。SQLite
transaction 只能登记已经 promote、目录 fsync 且重新 hash-verified 的 final 文件。它必须把
final files、Artifact metadata、ProviderCall identities、attestation 与 result hashes 防御性地
重验为等于同一 `ValidatedScoringWritePlan`；该复核发生在写盘之后，不能替代 plan 创建前的
完整 reparse/validation。

单一 transaction 原子登记 raw/structured Artifact、raw envelope 内的 attestation 绑定、
完成 scoring/quality ProviderCall，并推进 scoring stage。没有独立 cache record 或 cache
identity 写入。任何 DB 步骤失败全部回滚；未索引 final 文件是 orphan promoted files，
不是 Artifact、不是 cache hit，也不能单独证明 ProviderCall 成功。该事务可能需要新增
Repository 方法，但不需要数据库 migration。

Crash/restart 边界：

| crash 点 | 持久状态 | 恢复 |
|---|---|---|
| pre-write validation 前后 | 零文件、零 DB 成功状态 | 丢弃内存对象；不得创建 tmp 或返回 cache hit |
| temporary write/fsync 前后 | 只有本次 operation 命名空间的 tmp | 验证 owner/operation 后只清理这些 orphan tmp；不读为 cache |
| 一个或两个文件 promote 后、DB commit 前 | 可能有未索引 final 文件 | 不删除/覆盖；逐文件验证 hash 与 deterministic key，全部匹配才允许同 identity 继续 DB transaction |
| DB transaction 中 | SQLite 全回滚或全提交 | 重新查询完整关系；不得补写部分状态 |
| DB commit 后 | 完整 Artifact/call/stage graph | restart 重新验证文件和派生 cache view，零 Judge 调用 |

任一 final 文件 hash/type/path/version 不匹配都 fail-closed，不覆盖、不删除、不自动修复。
自动清理只允许本次 operation identity 创建且仍位于受控临时命名空间的 orphan temporary
files；已有 final 文件、已索引 Artifact 和其他 operation 的临时文件均不得删除。

### 9. Cache recovery

`ScoringCacheIdentity` 只是一份运行时 derived verification view，不是领域持久化对象、表、
Artifact、文件或可提交记录。它每次从以下既有事实重新计算：

- scoring 与 Judge ProviderCall `request_hash` / operation / trusted provenance；
- raw/structured Artifact deterministic key、producer version、content hash 与 metadata；
- raw envelope 内完整 validated `ContentQualityResult(PASS)`、其 `quality_result_hash` 与
  Quality PASS attestation；
- 当前 policy、scoring/quality schema、prompt、provider/model/digest 配置。

禁止新增 cache table、cache row、cache Artifact、migration 或独立 cache identity 文件。

Derived view 必须包含 `quality_result_hash`。Cache hit 不调用 Judge。恢复必须从 raw envelope
重建完整 result，执行 model/domain + PASS matrix validation，重算 canonical
`quality_result_hash`，并要求它与 attestation 及 derived view 三者相等，然后同时验证：

- 既有 scoring request/provider/model/output language/prompt/schema provenance；
- quality PASS attestation 的所有绑定字段与 canonical hash；
- Judge ProviderCall operation identity、`SUCCEEDED` 状态和 response Artifact 绑定；
- raw envelope 与 structured Artifact 的 ID/key/path/content hash/provider/model；
- quality-qualified producer versions；
- 从 persisted payload 重算的 candidate/input hash；
- Finalizer 对当前配置的完整重建。

Legacy entry 缺少完整 result/hash/attestation 时是 cache miss，保留旧审计并使用新 identity
计算；当前版本 envelope 的 result 缺失、非 PASS、矩阵非法，或 signals/reason/source/
confidence/evidence/hash 被篡改时是 integrity failure。两类情况都不得调用 Judge 来修补原
历史 identity；后者必须 fail-closed。

旧 Artifact 或缺少 attestation 的记录是普通 cache miss：保留审计并以当前新 identity
重新计算。版本变化生成新 Judge identity，可安全调用。已有当前 identity 的
`PENDING`、失败或矛盾记录不是普通 miss，必须 fail-closed，不能借 recompute 重复调用。

### 10. Reuse decision

- `ADAPT`：现有 Pydantic、标准库 hashing/JSON、受限 Ollama Adapter、ProviderCall、
  Artifact、派生 cache verification 与原子 stage completion；新增无 migration 的多 ProviderCall
  completion 原子 Repository 方法，以保证 Finalizer 后一次事务提交。
- `DIRECT`：已锁定 spaCy 只继续服务 TASK-016B；TASK-016C 不修改其职责。
- `REJECT`：品牌/公司/产品词典、网络查询、Wikipedia、外部 API、远程知识库、动态模型
  下载和新增依赖。

## Alternatives Considered

### 让 Deterministic Gate 判断 identifier / acronym

拒绝。它会不可避免地引入词表、token 或语言启发式，无法机械证明且会误杀正常技术内容。

### 让所有模块都能构造 ScoreResult

拒绝。Provider、repair 与 cache 的多入口会使 quality attestation 可以被绕过。

### 只用 producer version 代表 PASS

拒绝。版本只能证明预期策略，不能绑定具体 candidate、input、Judge identity 和实际调用。

### Cache hit 时重新调用 Judge

拒绝。它破坏 cache 语义、调用预算和崩溃恢复的 at-most-once 边界。

### 新增数据库字段或 Artifact kind

v1 拒绝。quality-qualified raw envelope、现有 Artifact metadata 和 ProviderCall 可以在
不迁移 Schema 的前提下表达可验证 attestation；若以后需要独立查询质量决策，再开 ADR。

## Consequences

- 所有成功评分多一个可验证 PASS attestation，恢复路径更严格且旧 cache 自动失效。
- 评分路径最多增加两次固定本地 Judge 调用；崩溃未知状态宁可停止也不重复调用。
- Deterministic Gate 召回率刻意很低；复杂垃圾必须交给 Local Judge。
- `ScoreResult` 外部形状不变，但内部构造权收敛到一个 Finalizer。
- SYSTEM_DESIGN 的旧 Provider->ScoreResult 契约被本 ADR supersede；实现后应由独立文档
  同步任务更新陈旧说明，但本轮设计修订不修改该文件。
- PASS 不等于事实核验；只代表当前输入内的最小内容价值与 grounding 达到固定门槛。
- 本 ADR 不授权 Local Deep Analysis、Cloud、Router、Weekly V2、数据库 migration、真实
  模型或网络操作。
