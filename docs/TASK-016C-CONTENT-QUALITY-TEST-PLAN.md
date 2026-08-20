# TASK-016C Content Quality Test Plan — Phase F Round 3 Alignment

- 状态：Phase E 已批准；Phase F 为 `DESIGN READY / IMPLEMENTATION NOT AUTHORIZED`。
  本计划中的 repair/retry/recovery、持久化和 cache 项目分别归 H、G、I，不构成 Phase F
  实现授权。
- 依据：[ADR-025](decisions/ADR-025-content-quality-layer-scope-boundary.md)
- 接口：[TASK-016C Interface Design](TASK-016C-CONTENT-QUALITY-INTERFACE-DESIGN.md)
- 测试环境：完全离线；Fake scoring/Judge transport、临时 SQLite、临时 DATA root

## 1. 验收目标

TASK-016C 只有在以下事实都有独立证据时才可验收：

1. TASK-016B source、ADR-024 与 Language Validator 行为未修改；
2. Deterministic Gate 只有三个机械 reason，所有 identifier/entity 样例进入 Local Judge；
3. Provider Adapter 只返回 untrusted `PrimaryScoringAttempt`，其唯一业务 DTO 为
   `ScoringCandidate`，绝不返回 `ScoreResult`；
4. `TrustedScoringFinalizer` 只创建内部业务 `ScoreResult` 并输出 `TrustedScoreResult`；
   Phase F 仅验证 PRIMARY，repair/retry/recovery 属于 H，cache recovery 属于 I；
5. 每个成功结果的完整 validated `ContentQualityResult(PASS)` 有稳定 canonical
   `quality_result_hash`，且与 attestation 精确绑定；
6. cache hit 不调用 Judge，且从 ProviderCall、Artifact、producer metadata、attestation
   和当前配置重算 derived verification view；
7. Judge identity 严格分为 H1 normalized-input hash 与 ADR-003 H2 ProviderCall request hash；
8. H 的 PRIMARY/REPAIR Judge 预算及崩溃未知状态不得重调；F 不调用 repair/retry；
9. 三项 confidence 和 status/reason/signal 组合全部 fail-closed；
10. F 的 Finalizer 成功前后均无 scoring Artifact、response_artifact_id、ProviderCall SUCCESS、
    cache hit、DB 或 filesystem mutation；G 才实施 exact-byte pre-write validation 与
    `ValidatedScoringWritePlan`；
11. G 的 DB registration 只登记已 promote 且 final-verified 的 plan，不承担或替代首次
    写盘前验证；
12. 无新依赖、无 migration、无品牌词库、无网络或外部知识查询。

## 2. TDD 纵切顺序

实现须逐步形成可复现 RED，再实现 GREEN：

1. 三个 deterministic reason 与 Gate 组合；
2. `ContentQualityResult` 三 confidence、合法矩阵与完整 canonical hash；
3. `ScoringCandidate` Provider contract 与唯一 Finalizer；
4. `ContentQualityInput`、Evidence Registry、candidate/input hash；
5. Local Judge 固定请求与严格响应 wrapper；
6. Quality PASS attestation 与完整 result hash binding；
7. Phase F PRIMARY-only in-memory candidate composition 与 bare `ScoreResult` legacy rejection；
8. Phase G raw/structured canonical serialization、pre-write validation、
   `ValidatedScoringWritePlan`、文件协议与 atomic DB registration；
9. Phase H PRIMARY/REPAIR H1/H2 identity、一次性预算与崩溃 recovery；
10. Phase I derived cache verification/recovery、adversarial/crash/bypass 与 release acceptance。

不得删除、跳过、弱化断言、修改既有测试门禁或把失败样例移入生产词表。

## 3. Deterministic Gate tests

### 3.1 唯一允许拒绝

| 输入 | 预期 |
|---|---|
| 空/规范化后空的内容 | `REJECT / EMPTY_CONTENT` |
| 含禁止控制字符 | `REJECT / CONTROL_CHARACTER_INVALID` |
| 两个规范化后完全相同的相邻非空 segment | `REJECT / EXACT_REPETITION` |
| 大小写不同或近似重复 | `CONTINUE`，不得模糊判断 |

固定顺序和字符矩阵必须逐项覆盖：

- 严格 decode 失败在 Gate 前拒绝；
- NULL `U+0000` -> `CONTROL_CHARACTER_INVALID`；
- TAB `U+0009` 与 LF `U+000A` -> control scan 允许；
- CR `U+000D` -> 拒绝；
- ZERO WIDTH SPACE `U+200B` -> 拒绝；
- BOM `U+FEFF` -> 拒绝；
- 其他 Unicode `Cc` -> 拒绝。

EXACT_REPETITION 表格：

| reason | 预期 |
|---|---|
| `same\nsame` | `REJECT / EXACT_REPETITION` |
| ` same\nsame ` | 首尾 ASCII trim 后 `REJECT` |
| `same\n\nsame` | 删除空 segment 后 `REJECT` |
| `same\n same` | `CONTINUE`；segment 不二次 trim |
| `Same\nsame` | `CONTINUE`；禁止 lowercase/casefold |
| `same!\nsame` | `CONTINUE`；禁止标点 normalization |
| `same\nother\nsame` | `CONTINUE`；只比较相邻 segment |

静态扫描不得出现 casefold/lower、tokenization、NLP、Unicode/标点 normalization 或
非相邻 repetition 逻辑。

### 3.2 必须进入 Local Judge

以下逐项断言 Gate 为 `CONTINUE` 且 Judge Fake 被调用一次：

```text
API SDK GPT LLM
Docker Kubernetes Terraform
General Dynamics Corporation
Amazon Connect Salesforce
```

静态扫描 Gate production Diff 不得出现：

- identifier/acronym/technical/brand/product 词表；
- token 数量、大小写、首尾、位置、词尾规则；
- POS/dependency/NER/spaCy 调用；
- `PASS` 返回值。

## 4. ContentQualityResult contract matrix

### 4.1 合法矩阵

分别构造并 round-trip：

- Gate `REJECT`：三个 reason 各一例；Judge identity 全空；
- Judge `PASS`：decision=`HIGH`，grounding/usefulness=`MEDIUM` 与 `HIGH` 的边界组合；
- Judge `REJECT`：每个内容 reason 与同名负向 signal；
- Judge `UNCERTAIN`：`GROUNDING_INSUFFICIENT`、`JUDGE_UNAVAILABLE`、
  `JUDGE_INVALID_RESPONSE`。

### 4.2 非法组合

参数化拒绝：

- Gate + `PASS` / `UNCERTAIN`；
- Gate reason 与 Judge source，或 Judge reason 与 Gate source；
- Gate result 带 Judge identity/evidence；
- `PASS` decision 不是 `HIGH`；
- `PASS` grounding/usefulness 为 `LOW`；
- `PASS` 缺正向 signal、缺 evidence、带 rejection reason 或负向 signal；
- `REJECT` 缺 reason/同名 signal，或同时声称完整 PASS signals；
- identifier/entity/low-information/minimal-claim `REJECT` 的 usefulness 不是 `LOW`；
- grounding `REJECT` 的 grounding 不是 `LOW`，或带 `GROUNDING_PRESENT`；
- `UNCERTAIN` 任一 confidence 不是 `LOW`，或带完整 PASS signals；
- 重复/空白/registry 外 evidence ID；
- unknown enum/field、自由 diagnostics、错误 hash、超限集合。

每个非法组合必须覆盖五条入口：

1. 普通 constructor；
2. `model_copy(update=...)` 后进入 trusted wrapper；
3. `model_construct()` 后进入 trusted wrapper；
4. `model_validate_json()` restore；
5. subclass/Mapping instance 进入 wrapper。

断言 wrapper 总是从 canonical mapping/JSON 重建；对象已是目标类型也不能跳过验证。

### 4.3 Canonical quality result hash

- 使用项目现有 `canonical_json` 规则（UTF-8、非 ASCII 转义关闭、sort keys、compact
  separators）对完整 validated `model_dump(mode="json")` 计算 hash；
- signals 按 enum 排序去重、evidence IDs 按稳定 ID 排序去重后必须再次完整验证；
- 相同合法 PASS 的 Mapping/JSON round-trip 得到相同 `quality_result_hash`；
- schema/policy/prompt/status/source/confidence/signals/reason/evidence/candidate/input/request/
  Judge provenance 任一 canonical 字段变化，hash 必须变化或 validation 先失败；
- 静态扫描不得存在手写 PASS 字段子集 hash，也不得对 unchecked instance 直接 hash。

## 5. ScoringCandidate 与唯一 Finalizer tests

### 5.1 Provider boundary

- Phase F Fake PRIMARY Adapter 只返回 `PrimaryScoringAttempt(candidate=ScoringCandidate)`；repair
  Adapter/attempt 仅在 H 测试中出现；
- `score` 接受并 round-trip 非整数 `7.25`，不得丢失精度；
- `dimensions=None` 与完整 `ScoreDimensions` 都合法；
- Candidate 与 Finalizer 输出的 reason/topics/should_summarize/dimensions 业务字段保持等值；
- 静态契约确认 ADR-025 supersede SYSTEM_DESIGN 的 Provider->ScoreResult 旧语义，生产
  composition 只有 Provider->Candidate->Finalizer 一条可信路径；
- 返回 `ScoreResult`、带 provenance 的 candidate、未知 quality 字段全部拒绝；
- Provider response 在 quality `PASS` 前不能被 Runtime/Artifact/cache 当成结果。

### 5.2 Finalizer positive path

用合法 candidate/context/input/full-quality-result/attestation/quality-call identity 调用
Finalizer，断言：

- 返回 opaque `TrustedScoreResult`，其内部业务字段与现有公开 `ScoreResult` shape 等值；
- provider/model/output language/prompt/schema 来自 trusted context；
- candidate、input、attestation hash 全部重算；
- 完整 quality result 重建、PASS matrix 重验并重算 `quality_result_hash`；
- `computed_quality_result_hash == attestation.quality_result_hash`；
- Judge ProviderCall identity 由 H1 经既有 builder 得到 H2，并与 attestation 精确相等；
- TASK-016B language invariant 仍执行；
- Phase F 仅 PRIMARY 入口调用 Finalizer；H/I 的 repair/cache 路径在各自授权后也必须调用它。

### 5.3 Finalizer bypass matrix

逐字段篡改 candidate、context、quality result、attestation、quality call identity：

- `model_copy(update=...)`；
- `model_construct()`；
- Mapping / JSON；
- cache 中伪造的 ScoreResult instance；
- candidate/output language 不一致；
- candidate/input/attestation hash 任一不一致；
- policy/prompt/schema/provider/model/digest 任一不匹配；
- evidence registry 外引用；
- full quality result 与 attestation 的 `quality_result_hash` 不一致；
- attestation/result/ProviderCall/derived view 的 H2 任一不一致。

全部必须拒绝且无 ScoreResult/Artifact/cache。静态扫描生产代码确认除
`TrustedScoringFinalizer` 外，没有 TASK-016C 路径直接构造、copy、construct 或 restore
可信 `ScoreResult`。

### 5.4 Phase F → G raw continuation matrix

以下设计测试必须在未来 F/G 分别实现，且不要求或授权真实 Provider、DB 或 filesystem：

1. final raw response 在 F 内存中保留到 `PhaseFTrustedScoringSuccess`；
2. raw response 受既有 byte 上限约束，且是严格 UTF-8 decoded 完整 HTTP JSON response；
3. raw response 绑定同一 `scoring_request_hash`、provider/model/digest 与 `PRIMARY` role；
4. `raw A + candidate B` 组合拒绝；
5. attempt candidate hash 必须等于 Finalizer candidate hash；
6. legacy raw/result、bare `ScoreResult`、Mapping 或 JSON 不能成为 attempt 或 trusted success；
7. F 不产生 Artifact；
8. F 不产生 cache entry；
9. F 不完成 ProviderCall；
10. F 不写 DB 或 filesystem；
11. G 只接受 success aggregate 的 raw-response source；
12. caller/cache/legacy Artifact 不能替换该 raw source；
13. 单独 `TrustedScoreResult` 不足以构造 G raw envelope；
14. G cutover/recovery 不得 provider recall。

每个拒绝还必须证明没有 `response_artifact_id`、stage advance、cache hit 或 legacy upgrade；
F 的 PRIMARY quality/attestation 失败直接 fail-closed，repair/retry 测试只属于 H。
并且必须覆盖 aggregate private-sentinel/exact-type、封存 request/candidate hash 的 mutation/spoof
拒绝，以及 F-G-H 接口不 return/accept bare `ScoreResult`。

## 6. Local Judge contract tests

使用 Fake loopback transport，不启动真实 Ollama：

- endpoint 只能是已验证 loopback；
- provider/model/digest 精确来自当前 trusted local config；
- policy/prompt/schema 固定；
- `temperature=0`、`stream=false`、`think=false`、无 tools；
- 禁止 pull/download、remote base URL、cloud tag、dynamic prompt、network fallback；
- authentication、userinfo、query、fragment、非 loopback 在调用前失败；
- timeout、短读、超限、非 UTF-8、非 JSON、unknown field、invalid enum、registry 外 ID
  产生 `UNCERTAIN`；
- model missing/digest mismatch 在业务 generate 前 fail-closed；
- stdout/stderr/JSONL 不含 prompt、candidate、evidence excerpt、Transcript 或响应原文。

## 7. 精确内容质量案例

### 7.1 Attack / low-quality

以下四例必须由 Gate `CONTINUE`，再由 Judge Fake `REJECT` 或 `UNCERTAIN`；不得进入
Finalizer/Artifact/cache：

```text
Amazon Connect Salesforce
Docker Kubernetes Terraform
API SDK GPT LLM
General Dynamics Corporation
```

测试只证明 Judge 判定“不足以成为有 grounding 的评分理由”，不宣称识别了品牌、公司、
产品或实体事实。

### 7.2 Normal

当前 Evidence Registry 包含相应输入时，Judge Fake 可对以下候选返回合法 PASS：

```text
Docker containers help developers deploy applications
Redis stores data and improves application performance
OpenAI develops useful AI models
```

每例必须满足三项 confidence 门槛、两个正向 signal 和合法 evidence IDs。相同 Judge
response 若换成另一 request 的 evidence ID，必须拒绝。

### 7.3 Low information 与 injection

`good video`、`nice product`、`very useful` 必须进入 Judge 并非 PASS。Prompt injection、
Markdown/HTML/Obsidian 指令、Unicode confusables 和 stuffing 都不能改变 model、endpoint、
版本、schema 或 evidence registry，也不能触发文件、工具、subprocess 或网络访问。

## 8. Later-phase Fake flow 与事件顺序（非 Phase F 授权）

Phase F 只测试 `CANDIDATE_PRIMARY -> SCHEMA_PRIMARY -> LANGUAGE_PRIMARY -> QUALITY_PRIMARY ->
ATTESTATION_PRIMARY -> FINALIZE` 的纯内存前缀，并在任一失败时 fail-closed。下列 `SERIALIZE`
及之后的步骤属于 G；所有 `REPAIR` 步骤、共享 budget 和 recovery 属于 H；cache verification
属于 I。它们保留为后续任务的冻结验收要求，不得被解释为 F 要求或授权。

### 8.1 Phase G primary PASS continuation

```text
CANDIDATE_PRIMARY
SCHEMA_PRIMARY
LANGUAGE_PRIMARY
QUALITY_PRIMARY
ATTESTATION_PRIMARY
FINALIZE
SERIALIZE
PREWRITE_VALIDATE
WRITE_PLAN_CREATED
TMP_WRITE
FILE_FSYNC
VERIFY
PROMOTE
DIR_FSYNC
FINAL_VERIFY
DB_REGISTER
```

断言 Judge=1、repair=0。ATTESTATION_PRIMARY 结束时仍无 Artifact、response_artifact_id、
ProviderCall SUCCESS 或 cache hit。`SERIALIZE` 后先验证 exact bytes 并创建内存 plan；plan
之前无 tmp/final。随后完成两份文件的可验证 promote，再由一次事务登记 attested raw
envelope、structured result、两份 completion 与 stage。

`CANDIDATE_*` 是不可信 DTO 到达事件，严格 parsing 在紧随其后的 `SCHEMA_*` 完成；非法 DTO
在 language/quality 前停止并消费共享 repair。不得跳过 Candidate 或 schema validation。

### 8.2 Phase H primary quality failure, repair PASS

必须严格产生：

```text
CANDIDATE_PRIMARY
SCHEMA_PRIMARY
LANGUAGE_PRIMARY
QUALITY_PRIMARY
REPAIR
CANDIDATE_REPAIR
SCHEMA_REPAIR
LANGUAGE_REPAIR
QUALITY_REPAIR
ATTESTATION_REPAIR
FINALIZE
SERIALIZE
PREWRITE_VALIDATE
WRITE_PLAN_CREATED
TMP_WRITE
FILE_FSYNC
VERIFY
PROMOTE
DIR_FSYNC
FINAL_VERIFY
DB_REGISTER
```

不得遗漏 repair candidate/language，不得提前 Finalize，不得保存 primary raw。

### 8.3 失败矩阵

| Primary | Repair | 期望 |
|---|---|---|
| Gate REJECT | Judge PASS | primary 不调 Judge；repair Judge=1；只保存 repair |
| Judge REJECT | Judge PASS | Judge=2；只保存 repair |
| Judge UNCERTAIN | Judge PASS | Judge=2；只保存 repair |
| REJECT | REJECT | `INVALID_RESPONSE`；零正式 Artifact/cache |
| UNCERTAIN | UNCERTAIN | `INVALID_RESPONSE`；零正式 Artifact/cache |
| language invalid | quality PASS after repair | shared repair=1；只保存 repair |
| repair language invalid | 不执行 quality repair | `INVALID_RESPONSE`；零正式 Artifact/cache |

每条失败路径断言：无可信 ScoreResult/ScoringOutcome、无 `SCORING_RAW`、无
`SCORING_STRUCTURED`、无成功 scoring response_artifact_id、Pipeline/Job/score 不推进，
当前 cache 不命中，安全错误不含模型内容。

## 9. Judge budget、crash 与 recovery tests

为 PRIMARY / REPAIR operation 分别验证两层 identity。H1 必须等于完整 validated
`QualityJudgeOperationInput` 的 canonical SHA-256；H2 必须等于：

```text
build_provider_request_hash(
  operation="local-content-quality-v1",
  normalized_input_hash=H1,
  provider=trusted judge provider,
  model=trusted judge model,
  prompt_version=quality prompt version,
  schema_version=quality schema version,
)
```

断言 H1 不是 ProviderCall key，且 fixture 中 H1 != H2。冻结 equality：

```text
attestation.judge_request_hash
  == ProviderCall.request_hash
  == DerivedScoringCacheView.quality_provider_call_request_hash
  == H2
```

复用现有 `build_provider_request_hash` 的 golden/维度测试，证明 operation、H1、provider、
model、prompt、schema 任一变化按既有规则改变 H2；candidate/input/policy/role/digest 变化先
改变 H1 并进而改变 H2；相同 operation/input/config 在 restart 后
重建完全相同 H1/H2。PRIMARY/REPAIR 使用同一 operation，但 role 进入 H1，因此两者 identity
稳定不同。Unknown reservation 必须继续使用原 H2，不能因重算 H1 创建新 request hash。

另以 Fake Repository 证明 one-shot wrapper 先查询：record 不存在时可 reserve/call；
live PENDING 只能等待或停止；expired PENDING 只有在 deterministic PASS raw envelope 与
promoted files 完整验证后才可进入专用 recovery；任何既有 record 都不得进入通用 expired/failed
takeover 后再外部调用。

| 预置状态 | 运行行为 | 调用计数 |
|---|---|---:|
| missing PRIMARY | reserve -> call -> complete | 1 |
| missing REPAIR after explicit primary non-PASS | reserve -> call -> complete | 1 |
| live PENDING | fail-closed / in progress | 0 |
| expired PENDING + verified PASS promoted files | atomic recovery claim + DB registration | 0 |
| expired PENDING without verified PASS promoted files | `ATTEMPT_UNKNOWN`，不 reclaim | 0 |
| FAILED_RETRYABLE | role 已消费，不自动 retry | 0 |
| FAILED_FINAL | role 已消费 | 0 |
| SUCCEEDED + valid PASS attestation | recover | 0 |
| SUCCEEDED + missing/mismatched artifact | integrity failure | 0 |

故障注入点：reserve 后、transport 前；transport 后、response parse 前；PASS wrapper 后、
attestation 构造前；attestation 后、Finalizer 前；Finalizer 后、serialize 后、pre-write
validation 中/后、write-plan 创建后；每个临时文件 write/fsync/hash verify 后；每个 promote
后；parent dir fsync 后；transaction 内每个 Artifact/
completion/stage 步骤。任何“可能
已调用”的状态都不能重调同一 identity；transaction 内失败不得留下部分 DB 成功状态。

统计断言：PRIMARY<=1、REPAIR<=1、总 Judge<=2、scoring repair<=1；进程重启不能清零。

## 10. Quality PASS attestation tests

### 10.1 生成与 round-trip

- candidate/input/Judge operation 生成稳定 canonical hash；
- 完整合法 PASS result 生成稳定 `quality_result_hash`；
- attestation 的 `quality_result_hash` 与完整 result 精确一致；
- attestation hash 排除自身字段并稳定；
- attestation 首先只存在内存；Finalizer 前 Repository 中不存在其 Artifact/cache hit/成功调用；
- G 的 raw envelope round-trip 保留最终 provider raw、可完整重建的 validated quality result 与
  完整 attestation；
- G 的 Judge ProviderCall `SUCCEEDED.response_artifact_id` 指向同一 raw envelope；
- I 的 structured recovery 只能经 Finalizer 返回 `TrustedScoreResult`，而外部 ScoreResult JSON
  业务 shape 保持不变。

### 10.2 Quality decision binding 与单字段篡改

必须覆盖以下精确矩阵：

1. valid `ContentQualityResult(PASS)` -> canonical hash stable；
2. 修改 signals -> `quality_result_hash` mismatch；
3. 修改 rejection reason -> validation 或 hash mismatch；
4. 修改 decision source -> validation 或 hash mismatch；
5. 修改 decision confidence -> validation 或 hash mismatch；
6. 修改 grounding confidence -> validation 或 hash mismatch；
7. 修改 usefulness confidence -> validation 或 hash mismatch；
8. 修改 evidence binding -> validation 或 hash mismatch；
9. raw envelope decision A + attestation B -> recovery rejected；
10. `model_copy` / `model_construct` / Mapping / JSON restore -> 完整重建验证后才可 hash/finalize；
11. Artifact SHA 正确但 `quality_result_hash` 错误 -> integrity failure；
12. attestation hash 正确但完整 PASS matrix 非法 -> rejected。

并逐项篡改以下 provenance 后拒绝：

- candidate hash；
- quality input hash；
- quality result hash；
- scoring request hash；
- policy/schema/prompt version；
- scoring schema/prompt version；
- Judge provider/model/digest；
- operation/request hash/attempt role；
- 三项 confidence；
- evidence IDs；
- attestation hash；
- raw Artifact key/path/content hash/producer version；
- Judge ProviderCall status 或 response artifact ID。

任何篡改不得因重算 Artifact SHA 或单个外层 hash 而变成可信；Recovery 必须从 raw envelope
重建完整 ContentQualityResult，执行 model/domain + PASS matrix validation，重算 result hash，
再从当前 input/config、attestation、ProviderCall 和两份 Artifact 重建全链交叉关系。

### 10.3 Pre-write validation 与零写入 tests

Finalizer 成功前逐项查询并断言不存在：

- `SCORING_RAW` / `SCORING_STRUCTURED` Artifact record；
- scoring/quality `response_artifact_id`；
- scoring/quality ProviderCall `SUCCEEDED`；
- 任何独立持久化的 cache identity/table/row/Artifact/file；
- 当前运行可返回的 cache hit；
- pipeline `SCORED` 状态。

上面的“cache identity”只可作为运行时派生视图检查项，不得在 Repository/DB 中找到对应
table、row、Artifact 或文件。

Finalizer 成功后，使用 spy writer 与临时空 DATA root 验证成功事件严格为：

```text
SERIALIZE
PREWRITE_VALIDATE
WRITE_PLAN_CREATED
TMP_WRITE
```

`ValidatedScoringWritePlan` 必须是 opaque、immutable、process-memory-only capability；禁止
JSON/DB/Artifact/cache round-trip，禁止调用方以 Mapping、unchecked construct/copy 或散装
bytes/`ArtifactWrite` 伪造。Writer public boundary 只接受 plan。

在 `PREWRITE_VALIDATE` 中分别断言：

- raw exact bytes 可严格解析，完整 `ContentQualityResult` 重建并通过 model/domain validation、
  normalization 与 PASS matrix；
- 重算的 `quality_result_hash` 同时等于完整 result、raw attestation 和传入 attestation；
- candidate/input binding、Judge H2、scoring/quality ProviderCall identity、finalized
  `ScoreResult`、request/config/producer/version provenance 全部一致；
- structured exact bytes 可经可信 validation 重建与 finalized 完全一致的 `ScoreResult`，并
  精确核对 provider/model/language/prompt/schema；
- raw/structured canonical reserialization 分别 byte-for-byte 相等；长度、SHA-256 与两份
  `ArtifactWrite` expected metadata 精确一致。

参数化篡改 final raw bytes：Decision A + Attestation A 已通过 Finalizer，但 serializer 输出
Decision B + Attestation A；raw Decision A + Attestation B；decision 缺失；只保留 PASS
summary；分别修改 signals、三项 confidence、evidence、decision source、candidate/input
binding、Judge H2、producer/version/request provenance。再参数化篡改 structured bytes 的
任一业务字段及 provider/model/language/prompt/schema binding。即使攻击者同步重算外层
Artifact SHA，也必须在 plan 创建前拒绝。

每个失败必须精确产生 `SERIALIZE -> PREWRITE_VALIDATE_FAILED`，并证明事件流中不存在
`WRITE_PLAN_CREATED`、`TMP_WRITE`、`PROMOTE`、`DB_REGISTER`；DATA root 不存在本 operation
的 tmp/final path，DB 中无 Artifact、completion、`response_artifact_id`、stage advance 或
cache hit。

### 10.4 Artifact file commit protocol

以合法 `ValidatedScoringWritePlan` 对 raw/structured 分别验证固定顺序：same-filesystem
exclusive tmp write -> file fsync ->
length/hash verify -> no-clobber atomic promote -> parent dir fsync -> reopen final verify。

参数化故障/攻击：

- tmp 短写、fsync 失败、hash mismatch；
- tmp/final 是 symlink、非普通文件或路径逸出 DATA root；
- cross-filesystem promote；
- final 已存在且 hash 不同、key/operation ownership 不同；
- final 已存在且同 operation/key/length/hash 全同的幂等恢复；
- concurrent no-clobber promote，只有一方可成功；
- raw promote 成功而 structured 尚未 promote；
- 两文件 promote 成功而 parent dir fsync 或 DB 尚未完成。

每条失败断言：零 Artifact/ProviderCall SUCCESS/cache hit；不覆盖或删除任何已有 final 文件；
自动清理只触及当前 operation identity 的 orphan tmp，其他 operation tmp 不变。

### 10.5 Atomic DB registration

两份 final 文件全部重新验证后才调用一次 Repository API。对 raw insert、structured insert、
quality attestation binding、scoring completion、quality completion 和 stage update 逐点注入
异常，断言整个 SQLite transaction 回滚且零部分 DB 状态。全成功时单事务提交全部关系。
API 不接受或写入独立 cache identity；传入未 promote、未 dir-fsync 或未 hash-verified 的
proof 必须在事务前 fail-closed。

Atomic API 只接受原始 `ValidatedScoringWritePlan` 与 final-file verification proof，拒绝把
散装 finalized/result/attestation/ArtifactWrite 拼成等价调用。它在 DB transaction 前防御性
重验 final file path/type/length/hash/metadata、两份 ProviderCall identity、完整 result /
attestation hashes 与当前 provenance 全部等于 plan。可再次解析 final bytes 作为 defense in
depth，但测试必须证明即使移除 DB 复核，pre-write boundary 仍会在任何 tmp write 前拒绝
Decision A/B mismatch、summary-only 与所有字段篡改；DB 复核不得成为首次验证点。

### 10.6 Crash/restart matrix

| crash | restart 断言 |
|---|---|
| pre-write validation 前/中/后 | 丢弃纯内存状态；无 tmp/final/Artifact/cache，Judge 不重调 |
| tmp write 前/中/后 | 不读为 Artifact/cache；只清理当前 operation orphan tmp |
| raw promote 后、structured promote 前 | 重验 raw；可从可信 raw envelope 生成/验证 structured 并继续；Judge=0 |
| 两文件 promote 后、DB 前 | 重验 deterministic key/type/path/version/length/hash 后原子登记；Judge=0 |
| DB transaction 内 | SQLite 全回滚或全提交；不得补写部分行 |
| DB commit 后 | 完整重验 files/records/attestation/derived view；匹配才 hit；Judge=0 |

Promoted file 缺失或任一 mismatch 必须 integrity failure；不当成普通 miss，不删除 formal
file，不重调 Judge。Live operation owner 不得被 restart 抢占；expired/unknown operation
只有在原子 recovery claim 与完整文件证明同时成立时才可登记。

## 11. Cache recovery tests

在临时 SQLite/DATA 建立合法 PASS graph；不得建立独立 cache identity 持久化对象：

### 11.1 完整 hit

第二次运行必须：

- scoring transport=0；
- Judge transport=0；
- 从 ProviderCall request hashes、Artifact key/version/hash、producer metadata、attestation
  和当前 policy/schema/prompt/model digest 重算 derived verification view；
- 重算 candidate/input/full-quality-result/attestation hash；
- 断言 raw result hash == attestation quality_result_hash == derived view quality_result_hash；
- 断言 attestation H2 == quality ProviderCall request hash == derived view quality call H2；
- 验证 Judge call 与 raw envelope；
- 经 Finalizer 重建 ScoreResult；
- 返回 persisted cache hit。

允许只读观察历史 atomic commit 中已有的 `SUCCEEDED` 和 Artifact；断言当前执行在
Finalizer 成功前没有新 ProviderCall/Artifact/cache/stage 写入，也没有向调用方返回 hit。

### 11.2 普通 miss

以下视为 miss，保留旧审计并以新 identity 计算：

- legacy cache 无 quality attestation；
- legacy cache 无完整 quality result 或 `quality_result_hash`；
- quality/scoring policy、prompt、schema 版本变化；
- trusted Judge model/digest 变化；
- output language 或 scoring request 变化。

断言新 operation identity 的 scoring provider/Judge 各按预算调用，旧 Artifact 不删除、不覆盖。

### 11.3 Integrity failure / unknown attempt

以下不是普通 miss，不得重新调用同一 Judge identity：

- 当前版本 attestation 或 Artifact hash 矛盾；
- 当前 envelope result 缺失、非 PASS、matrix 非法或任一 canonical 字段/hash 被篡改；
- Judge call `SUCCEEDED` 但 response artifact 不一致；
- 当前 identity 为 live/expired PENDING；
- 当前 identity 已 FAILED。

断言 fail-closed、Judge=0、无新成功 Artifact/cache。

### 11.4 Derived identity persistence prohibition

- schema introspection 证明没有 cache identity table/column；
- Repository Fake/spy 证明没有 `put_cache_identity` 或等价写调用；
- DB snapshot 与 DATA tree 证明只有既有 ProviderCall、Artifact、producer metadata、raw
  attestation 和 stage facts；
- 分别篡改 derived view 的每个来源字段，均不得 hit；
- 仅修改当前 config 的 policy/schema/prompt/provider/model/digest 时为普通 miss，旧审计保留；
- 文件/记录/hash 互相矛盾时为 integrity failure，不得降级为 miss。

## 12. Production composition regression

以临时项目根、SQLite、DATA/logs 和测试 Vault 运行 Fake production composition：

- CLI 默认仍使用 `RuntimeOperations`；
- check/process/retry scoped 语义不变；
- ScoreResult 只由 Finalizer 返回；
- TASK-016B source、ADR-024、language tests 与 spaCy pipeline hash 均不变；
- scoring thresholds 与 `ScoringDecision` 不变；
- Cloud、Router、Weekly production、Knowledge V2、Obsidian 用户区、DB Schema/migration
  不变；
- restart 后合法 cache 不重复调用；失败或 unknown attempt 不变成 cache hit。

## 13. Scope、dependency 与 leakage checks

实现 Review 必须确认：

- `pyproject.toml` / `uv.lock` 无变化；
- migrations 与 state Schema 无变化；
- 允许为原子多 completion 增加 Repository 方法，但不得改变表、CHECK 或 migration；
- ADR-024、TASK-016B source/tests/archive/handoff 无变化；
- 没有品牌/公司/产品/技术词典；
- Gate 没有 token/case/POS/dependency/spaCy 逻辑；
- 没有 download/model pull/remote URL/Wikipedia/Web/API client；
- 没有真实网络、Key、Cloud、真实 Vault 或用户数据；
- stdout/stderr/JSONL/Artifact/test/handoff 不泄漏 candidate、evidence 或原始响应；
- Reuse 与 ADR-025 一致，且没有新增依赖。

## 14. Required gates

Implementer 与独立 Reviewer 均须在获批 worktree 运行：

```bash
uv lock --check
uv sync --locked --offline
uv run pytest -x -q <TASK-016C focused tests>
uv run pytest -x -q
uv run mypy src
uv run ruff check .
uv run youtube-intel --help
uv build --offline
bash scripts/security_scan.sh
git diff --check <base>...HEAD
```

另须执行：Finalizer 唯一构造点静态扫描、Judge one-shot operation 扫描、Gate 禁止规则
扫描、attestation/cache adversarial matrix、固定 loopback/model/digest/no-network 扫描和
全输出面泄漏扫描。

## 15. Independent Design Review checklist

- [ ] Deterministic Gate 是否精确只有三个 reason？
- [ ] 四个攻击样例是否全部进入 Judge？
- [ ] Provider 是否只能返回 ScoringCandidate？
- [ ] Finalizer 是否为 F PRIMARY、H repair、I cache recovery 的唯一 `TrustedScoreResult` 入口？
- [ ] Candidate 是否保持 score=float、dimensions 可选和全部现有业务字段？
- [ ] ADR-025 是否明确 supersede SYSTEM_DESIGN 的 Provider->ScoreResult 旧契约？
- [ ] PASS attestation 是否绑定用户要求的全部字段并可重算？
- [ ] 完整 PASS result 是否先完整验证，再 canonical hash，并与 attestation 精确绑定？
- [ ] Raw envelope recovery 是否重建完整 result，而非只信 attestation？
- [ ] H1 是否仅为 QualityJudgeOperationInput normalized hash，H2 是否复用 ADR-003 builder？
- [ ] Attestation、ProviderCall 与 derived view 的 H2 是否严格相等？
- [ ] Finalizer 前是否零 Artifact/call success/cache hit？
- [ ] Finalizer 后是否先验证 exact final raw/structured bytes，且只在两者通过后创建内存 WritePlan？
- [ ] WritePlan 是否不可持久化/恢复/伪造，writer 是否拒绝散装 bytes/ArtifactWrite？
- [ ] Decision A + Attestation A 被 serializer 写成 Decision B + Attestation A 时，是否零 tmp/final/DB 状态？
- [ ] Summary-only、decision omitted 与 signals/confidence/evidence/source/provenance 篡改是否都在写盘前拒绝？
- [ ] DB registration 是否只做相对同一 plan 的防御性复核，而不承担首次 pre-write validation？
- [ ] 是否严格执行 tmp write/file fsync/hash/no-clobber promote/dir fsync/final verify/DB transaction？
- [ ] Crash matrix 是否证明不删除 formal files 且只清理当前 operation orphan tmp？
- [ ] Cache identity 是否只由既有事实派生，且无 table/row/Artifact/file/migration？
- [ ] EXACT_REPETITION 和 CONTROL_CHARACTER 是否严格采用冻结算法与顺序？
- [ ] Cache hit 是否零 Judge 调用？
- [ ] PRIMARY/REPAIR 是否各最多一次，PENDING unknown 不重调？
- [ ] 三项 confidence 与 status/reason/signal 矩阵是否封闭？
- [ ] model_copy/model_construct/JSON restore 是否均不能绕过？
- [ ] Fake event 是否精确包含 SCHEMA/SERIALIZE/PREWRITE_VALIDATE/WRITE_PLAN_CREATED/TMP_WRITE/
      FILE_FSYNC/VERIFY/PROMOTE/DIR_FSYNC/FINAL_VERIFY/DB_REGISTER，且失败时无后续写事件？
- [ ] 无 migration 条件下 raw envelope 是否不破坏 structured consumer？
- [ ] ADR-023 是否明确 TASK-016C 被 ADR-025 supersede，Local Deep Analysis 为 TBD？
- [ ] TASK-016B、依赖、DB、Cloud、Router、Weekly 是否完全未改？

只有全部回答 YES，才可授权编码。
