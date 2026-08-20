# TASK-016C Implementation Master Plan

## Frozen design authority

- Accepted design baseline: `c547b7c46afbf254979331c2c56cddb93a8503f2`
- Governing decision: [ADR-025](decisions/ADR-025-content-quality-layer-scope-boundary.md)
- Interface and test authority: [Interface Design](TASK-016C-CONTENT-QUALITY-INTERFACE-DESIGN.md) and [Test Plan](TASK-016C-CONTENT-QUALITY-TEST-PLAN.md)

The accepted architecture is immutable for implementation purposes:

```text
untrusted Provider response
→ PrimaryScoringAttempt（untrusted、PRIMARY、内存 raw continuation；以同一 canonical parser 从 exact raw 重建 ScoringCandidate，并封存 raw/candidate/request hashes）
→ ScoringCandidate
→ schema validation
→ TASK-016B Language Validator
→ TASK-016C Content Quality
→ QualityPassAttestation
→ TrustedScoringFinalizer
→ TrustedScoreResult（内部保存已验证的 ScoreResult）
→ PhaseFTrustedScoringSuccess（TrustedScoreResult + PrimaryScoringAttempt；sealed raw/candidate/request binding）
→ canonical serialization
→ PREWRITE_VALIDATE
→ ValidatedScoringWritePlan
→ filesystem persistence
→ DB registration
→ recoverable cache
```

No Provider-to-`ScoreResult`, Candidate-to-Artifact, attestation-only, pre-write, cache, or DB-registration bypass is permitted.

## Ordered TDD phases

| Phase | Scope | Status | Dependency |
|---|---|---|---|
| A | Domain Contracts and Candidate Boundary | READY / assigned to WorkBuddy | accepted design |
| B | Deterministic Safety Gate | NOT AUTHORIZED | A accepted |
| C | Local Judge Contract and H1/H2 | NOT AUTHORIZED | B accepted |
| D | PASS Attestation and Canonical Hashing | APPROVED / `2c11faf41e17c3b823a39bfd1018c5c876b236c5` | C accepted |
| E | TrustedScoringFinalizer | APPROVED / `9b92946…` | D APPROVED；pure-memory finalization accepted |
| F | Candidate-only in-memory runtime integration（含 PRIMARY raw-response continuation） | APPROVED；integrated equivalents `61bb0bb… -> d059bea… -> 2f6e30b…` | E accepted；original accepted provenance `c0268a… -> df920cc… -> 931674e…`，以 conflict-free cherry-pick 内容等价整合 |
| G | Pre-write validation + persistence registration boundary + normal runtime cutover | READY / AUTHORIZED；IMPLEMENTATION NOT STARTED | F approved；[Phase G Amendment](TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md) 与正式 authorization |
| H | Repair/retry/recovery/budget orchestration | NOT AUTHORIZED | G accepted |
| I | Production hardening / release acceptance（含 derived cache verification、adversarial/crash/bypass 与完整验收） | NOT AUTHORIZED | H accepted |

Every phase follows RED → minimal GREEN → focused checks → independent review. A rejected phase returns only to its owning implementation scope; it never authorizes a later phase.

## Non-negotiable boundaries

- Do not modify TASK-016B Language Validator or ADR-024 scope.
- No brand/entity dictionary, token/POS heuristic, cloud/network fallback, external knowledge, new dependency, migration, table, or Artifact kind.
- Reuse existing Pydantic validation, canonical JSON/SHA-256, local Ollama guard, ProviderCall identity, Artifact metadata, and atomic stage completion by adaptation only.
- Phase A cannot create artifacts, cache entries, ProviderCall success, response artifact IDs, filesystem writes, or database registrations.

## Review and integration

WorkBuddy must stop after its assigned phase. Codex performs the independent review. Only an independent
approval of a phase may lead to a separately authorized next phase. Phase D、E 与 F 均已 APPROVED；F 的
三段 accepted history 已以用户授权、无冲突、线性且 tree/content-equivalent 的 commits
`61bb0bb… -> d059bea… -> 2f6e30b…` 整合。`PhaseFTrustedScoringSuccess` 在 G 实现时必须最小扩展为
完整、sealed 的 F→G evidence continuation，禁止以 caller DTO 补入 scoring/quality evidence。
Phase G 已完成设计并获得 implementation authorization，但尚未启动；只有 G 才拥有 pre-write/persistence
registration 与正式 runtime cutover。Phase H 才拥有 repair/retry/recovery/budget；Phase I 才拥有
derived cache verification 和 release acceptance。没有后续 phase 获得实现、整合或发布授权。
