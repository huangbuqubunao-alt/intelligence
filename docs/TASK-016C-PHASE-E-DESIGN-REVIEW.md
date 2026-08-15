# TASK-016C Phase E Maintainer Design Review

## 结论

`APPROVE FOR IMPLEMENTATION AUTHORIZATION`。

本审查以已批准 Phase D `2c11faf41e17c3b823a39bfd1018c5c876b236c5` 为代码基线，审阅
Round 3 authority amendment 与现有 `scoring.py`、`quality.py`、`runtime.py`、`domain.py`。
这是主控的独立式五轴设计复核；实现完成后仍必须由新的 Reviewer 会话复核实际 diff。

## 已核验事实

- `build_scoring_input()` 与 `_provider_request()` 当前重复计算同一 normalized input / request identity；
  可在不改 `state.py` 的前提下抽取 pure builder，且以现有 `build_provider_request_hash()` 保持兼容；
- `RuntimeOperations` 已持有 validated `AppConfig`，且已用该 composition point mint
  `QualityProvenanceAuthority`，因此是 `TrustedScoringContext` 的合法唯一铸造点；
- `QualityPassAttestation` 的 verify 函数已要求 exact `QualityProvenanceAuthority`，可由 Finalizer 直接复用；
- `ScoreResult` 是公开 Pydantic DTO，不能自行承担 provenance capability，采用 opaque wrapper 是最小且
  向后兼容的 trust boundary。

## 无 P1 的设计门禁

- request hash 不来自 caller/context；由 Finalizer 重算；
- Judge provenance 与 scoring provenance 不混合；
- wrapper 不修改既有 `ScoreResult` 业务字段、score 精度或 optional dimensions；
- Finalizer 不被授权触及 provider、persistence、cache、Artifact 或 filesystem；
- `max_transcript_chars` 已经通过 frozen sample/data metadata 进入 legacy normalized identity，不额外改变 hash 输入。

## 审查条件

implementation 必须严格按 task card 范围、TDD 和离线门禁执行；任何需要扩展到 `state.py`、provider、
persistence、cache 或 Phase F+ 的情形立即 BLOCKED，不得自行扩大。
