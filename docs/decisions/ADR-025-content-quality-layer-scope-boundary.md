# ADR-025：Content Quality Layer 职责、可信终结与恢复边界

## Status

Proposed；2026-08-13 Round 2 修订待 Independent Design Review

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

其中 `EXACT_REPETITION` 只允许比较经过 schema whitespace normalization 后完全相同的
非空 segment；不得做模糊匹配、case folding、token 分析或语义归并。

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

Provider Adapter 的返回类型固定为不可信 `ScoringCandidate`。Provider、repair、Artifact
reader 和 cache recovery 均不得直接构造、反序列化为或返回可信 `ScoreResult`。

`TrustedScoringFinalizer` 是唯一允许创建 `ScoreResult` 的应用边界。它必须同时接收并
重新验证：

1. canonical `ScoringCandidate`；
2. 当前可信 scoring context（provider/model/output language/prompt/schema）；
3. 完整且有效的 Quality PASS attestation；
4. 当前 scoring request 与 quality input 的重算 hash。

只有全部一致时，Finalizer 才从业务字段和可信 context 新建 `ScoreResult`。三条路径均
必须经过它：

- primary scoring candidate；
- 唯一 repair candidate；
- persisted cache recovery。

Cache reader 只能恢复 untrusted persisted payload，再由 Finalizer 重建 `ScoreResult`。
禁止把 `model_copy(update=...)`、`model_construct()` 或已构造 instance 当成可信捷径。

### 5. Quality PASS attestation

每个最终 `PASS` 必须有 `quality-pass-attestation-v1`，至少绑定：

- `candidate_hash`；
- `quality_input_hash`；
- quality policy version；
- scoring 与 quality schema version；
- scoring 与 quality prompt version；
- Judge provider；
- Judge model；
- Judge expected model digest；
- Judge operation identity、request hash 与 attempt role；
- 三项 confidence 与已验证 evidence IDs。

Attestation 由应用根据已验证 Judge response 和可信配置构造，模型不能自报。其 canonical
payload 计算 SHA-256 `attestation_hash`。v1 不新增 Artifact kind 或数据库字段：最终
`SCORING_RAW` 改为固定版本的 quality-qualified composite raw envelope，保存最终
scoring provider raw response、已验证且有限的 Judge PASS decision 与该 attestation；
`SCORING_STRUCTURED` 仍保持现有 canonical `ScoreResult` JSON，避免破坏 Runtime、
Report 和 Weekly consumer。最终 scoring call 与 Judge call 可以引用同一 composite raw
Artifact，但两者必须分别具有正确 operation identity；该 Artifact 的 provider/model 必须
与两次调用共同使用的固定本地 provider/model 精确一致。

该 envelope 只有在 Quality `PASS` 后才能成为正式 Artifact。`REJECT` / `UNCERTAIN`
candidate 不产生正式 scoring raw/structured Artifact。

Attestation integrity 是现有本地信任模型内的交叉一致性，不是对拥有 SQLite 与 DATA
写权限的攻击者提供密码学不可伪造性。恢复时必须重算 candidate/input/attestation hash，
核对当前配置、Artifact metadata/content hash，以及对应 Judge ProviderCall 的
`SUCCEEDED` 状态和相同 response artifact。任一不一致都不得成为 cache hit。

### 6. Judge 调用预算与 operation identity

每个 scoring request 的质量 Judge 预算冻结为：

- `PRIMARY` candidate：最多一次；
- `REPAIR` candidate：最多一次；
- 总计最多两次；scoring repair 自身仍最多一次。

每次 Judge 的 operation identity 由以下 canonical 字段派生：

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

调用前必须在既有 ProviderCall store 原子保留该 identity。TASK-016C 的 one-shot wrapper
必须先只读查询 identity。记录不存在时才可 reserve 并外部调用；live PENDING 只能等待或
停止，expired PENDING 只允许以完整验证的 deterministic PASS artifact 调用通用 reserve
的 artifact-recovery 分支，绝不进入 takeover 后外部调用。它不得把既有 Repository 对
expired `PENDING` /
`FAILED_RETRYABLE` 的通用 takeover 能力用于 Judge。恢复规则：

| 持久状态 | 行为 |
|---|---|
| 无记录 | 可保留并调用一次 |
| `SUCCEEDED` 且 PASS attestation 完整 | 恢复结果；Judge 调用为 0 |
| `FAILED_*` | 该 role 已消费；不得再次调用 |
| live `PENDING` | 等待或 fail-closed；此时通用 Repository 不执行 artifact recovery |
| expired `PENDING` + 完整验证的 deterministic PASS artifact | 只恢复并完成记录，不重新调用 |
| expired `PENDING` 且无完整 PASS artifact | 外部结果未知；fail-closed，不重新调用 |
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
primary schema
  -> primary language
  -> quality primary
  -> (if non-PASS) repair once
  -> repair schema
  -> repair language
  -> quality repair
  -> TrustedScoringFinalizer
  -> formal Artifact / cache
```

schema、language 或 quality 失败共享同一个 repair budget。第二次仍非 `PASS` 或 Judge
不可用时返回 `INVALID_RESPONSE`。未通过 Finalizer 的 candidate 不得产生可信
`ScoreResult`、正式 `SCORING_RAW` / `SCORING_STRUCTURED`、成功 scoring provenance
或当前 cache。

### 9. Cache recovery

Cache hit 不调用 Judge。恢复必须同时验证：

- 既有 scoring request/provider/model/output language/prompt/schema provenance；
- quality PASS attestation 的所有绑定字段与 canonical hash；
- Judge ProviderCall operation identity、`SUCCEEDED` 状态和 response Artifact 绑定；
- raw envelope 与 structured Artifact 的 ID/key/path/content hash/provider/model；
- quality-qualified producer versions；
- 从 persisted payload 重算的 candidate/input hash；
- Finalizer 对当前配置的完整重建。

旧 Artifact 或缺少 attestation 的记录是普通 cache miss：保留审计并以当前新 identity
重新计算。版本变化生成新 Judge identity，可安全调用。已有当前 identity 的
`PENDING`、失败或矛盾记录不是普通 miss，必须 fail-closed，不能借 recompute 重复调用。

### 10. Reuse decision

- `DIRECT`：现有 Pydantic、标准库 hashing/JSON、受限 Ollama Adapter、ProviderCall、
  Artifact、cache identity 与原子 stage completion。
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
- PASS 不等于事实核验；只代表当前输入内的最小内容价值与 grounding 达到固定门槛。
- 本 ADR 不授权 Local Deep Analysis、Cloud、Router、Weekly V2、数据库 migration、真实
  模型或网络操作。
