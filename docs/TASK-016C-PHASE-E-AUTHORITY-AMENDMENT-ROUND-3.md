# TASK-016C Phase E Authority Amendment Round 3 Decision

## Conclusion

**DESIGN READY / IMPLEMENTATION NOT AUTHORIZED**

本修订关闭 Round 2 的两个设计 P1：可信 scoring request identity 没有唯一来源，以及公开
`ScoreResult` 无法表达 Finalizer trust boundary。它只冻结未来 Phase E 的最小接口与授权边界，
不实现任何生产代码、测试、依赖、持久化或运行时编排。

## Git 与阶段状态

- Accepted TASK-016C design：`c547b7c46afbf254979331c2c56cddb93a8503f2`
- Accepted Phase A：`e8ccc2d9e3b348d23942450b3f99861cdbc25aa3`
- APPROVED Phase D：`2c11faf41e17c3b823a39bfd1018c5c876b236c5`
- Phase D authority chain：`AppConfig → RuntimeOperations → QualityProvenanceAuthority → QualityPassAttestation`
- Phase E：仅完成设计，尚未获得 implementation authorization。

本决定不改写 A–D 历史；后续 Phase E implementation 必须是已验收 Phase D 历史的 descendant，
不得 squash、rebase 或 rewrite history。

## 1. Canonical Scoring Request Identity

Phase E 必须在 `scoring.py` 抽取唯一的纯内存函数
`build_scoring_request_identity()`。该函数不是 authority，也不接受调用方声称的 hash。

它的输入是经重建的 `ScoringInput` 与 Finalizer 已验证的 scoring identity material；其输出是
canonical identity（包括 request hash 及其可验证组成）。实现必须复用既有
`build_scoring_input()`、`_provider_request()` 和当前 canonicalization / SHA-256 行为。

兼容性不变量：同一有效输入在抽取前后的 `request_hash` 必须 byte-for-byte 等值。该函数必须是
pure function：不读写 DB、cache、Artifact、ProviderCall、filesystem，不调用网络或 provider，也不
改变 provider 行为。`state.py` 的既有 hash primitive 继续复用，不修改其行为。

## 2. 两个不同的 Runtime Authority

`QualityProvenanceAuthority` 保持 Phase D 定义不变，只拥有 Judge provider/model/digest、quality
policy/prompt/schema 和 H1/H2 所需受控 identity。它不能拥有 scoring provider、output language 或
scoring request hash。

新增的 `TrustedScoringContext` 是独立的 runtime-owned opaque capability。唯一创建路径为：

```text
validated AppConfig
→ RuntimeOperations
→ private mint + private sentinel
→ TrustedScoringContext
```

它含有：`scoring_provider`、`scoring_model`、`scoring_model_digest`、`output_language`、
`scoring_schema_version`、`scoring_prompt_version`、`scoring_operation`、`temperature`、
`max_output_tokens`、`max_description_chars`。它不含 `scoring_request_hash`、Judge provenance、
quality policy 或 H1/H2。`max_transcript_chars` 仍由既有 sample 内容及 sampling metadata 贡献给
legacy identity，不能通过本 amendment 改变 hash 语义。

该 capability 必须 non-Pydantic、exact-type-only，并使用私有 sentinel constructor；禁止 subclass、
proxy/property spoof、copy、deepcopy、pickle 与 serialization。`LocalScoringSettings`、`AppConfig`
DTO、Mapping、JSON、provider response、cache、Artifact 和测试 fixture 都不得 mint 它。Finalizer 必须
先验证 capability，再读取它的字段。

## 3. Trusted ScoreResult Boundary

采用 **Option A：新增 `TrustedScoreResult` wrapper**，不试图把公开 Pydantic `ScoreResult` 本身变为
不可构造模型。

| 方案 | 结论 | 原因 |
|---|---|---|
| A：opaque `TrustedScoreResult` | 采用 | 兼容现有 `ScoreResult` shape，同时把 trusted pipeline 的类型边界显式化。 |
| B：封死 `ScoreResult` 的所有 Pydantic 构造路径 | 拒绝 | 会破坏 provider/兼容解析所需的公开 DTO 路径，且无法让 `model_construct` 成为可信来源。 |

`TrustedScoreResult` 是 Finalizer 唯一铸造的 non-Pydantic opaque wrapper，内部保存已验证的
`ScoreResult`；它 exact-type-only、不可复制、不可序列化、不可继承，并无公开 constructor。
provider 与 compatibility boundary 可以短暂持有裸 `ScoreResult`，但 Phase F–I trusted pipeline 只能
接受 wrapper。直接构造、`model_validate`、`model_construct`、JSON restore、copy 的裸结果一律不能
获得 trusted 身份。

## 4. TrustedScoringFinalizer 冻结契约

输入：

1. `ScoringCandidate`；
2. `ScoringInput`；
3. `ContentQualityInput`；
4. `ContentQualityResult(PASS)`；
5. `QualityJudgeOperationInput`；
6. `QualityPassAttestation`；
7. 已验证的 `QualityProvenanceAuthority`；
8. 已验证的 `TrustedScoringContext`。

处理顺序固定为：先重建所有不可信 DTO；先 exact-type 验证两个 opaque capability；重跑 candidate、
language 与 PASS matrix；重算 quality hash；用唯一 request identity builder 重算 scoring identity；
校验 provider/model/digest/language/schema/prompt/operation 与 identity 参数；调用既有
`verify_quality_pass_attestation()` 重验 quality/H1/H2 binding；最后从 candidate 业务字段新建底层
`ScoreResult` 并包装为 `TrustedScoreResult`。

任一失败 fail-closed。Phase E 本身没有 DB、cache、Artifact、ProviderCall、filesystem、Ollama、网络、
persistence 或 repair orchestration；因此没有任何副作用。

## Allowed implementation scope（未来、需另行授权）

- `src/youtube_intel/scoring.py`：仅 canonical request identity extraction，保持 hash 行为完全兼容；
- `src/youtube_intel/quality.py`：Finalizer、opaque wrapper/capability verification 与 attestation 消费；
- `src/youtube_intel/runtime.py`：在已有 validated-config composition boundary 私有铸造/注入
  `TrustedScoringContext`；
- `src/youtube_intel/domain.py`：与 wrapper / untrusted reconstruction 所必需的最小类型契约；
- Phase E 专用 unit/integration tests 与对应 handoff。

## Forbidden scope

禁止修改 `providers/ollama.py`、`state.py`、DB、migration、Artifact、cache、ProviderCall persistence、
filesystem protocol、primary/repair orchestration，以及 Phase F–K。禁止依赖/`uv.lock`、网络、云端、模型
调用或 TASK-016B Language Validator 变更。

## Risks 与建议

风险是 Python 进程内 capability 不是对任意恶意反射代码的密码学隔离；本项目边界是拒绝普通调用方、
provider、Mapping/JSON、cache 和 Artifact 的可构造伪造。实现前的独立设计审查必须重点验证：
request-hash equivalence、authority spoof/copy/serialization 拒绝、裸 `ScoreResult` 不能进入 trusted
pipeline，以及 Finalizer 的零 I/O。

**建议：可以发起 Phase E implementation authorization 的审查流程，但尚不可开始 Phase E 实现。**
