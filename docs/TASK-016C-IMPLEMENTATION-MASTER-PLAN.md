# TASK-016C Implementation Master Plan

## Frozen design authority

- Accepted design baseline: `c547b7c46afbf254979331c2c56cddb93a8503f2`
- Governing decision: [ADR-025](decisions/ADR-025-content-quality-layer-scope-boundary.md)
- Interface and test authority: [Interface Design](TASK-016C-CONTENT-QUALITY-INTERFACE-DESIGN.md) and [Test Plan](TASK-016C-CONTENT-QUALITY-TEST-PLAN.md)

The accepted architecture is immutable for implementation purposes:

```text
untrusted Provider response
→ ScoringCandidate
→ schema validation
→ TASK-016B Language Validator
→ TASK-016C Content Quality
→ QualityPassAttestation
→ TrustedScoringFinalizer
→ TrustedScoreResult（内部保存已验证的 ScoreResult）
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
| E | TrustedScoringFinalizer | READY / AUTHORIZED | D APPROVED；Round 3 design review passed |
| F | PREWRITE_VALIDATE / ValidatedScoringWritePlan | NOT AUTHORIZED | E accepted |
| G | Filesystem + Atomic DB Registration | NOT AUTHORIZED | F accepted |
| H | Primary/Repair Orchestration and Budget | NOT AUTHORIZED | G accepted |
| I | Cache Recovery / Derived Verification View | NOT AUTHORIZED | H accepted |
| J | Adversarial / Crash / Bypass Verification | NOT AUTHORIZED | I accepted |
| K | Full Regression / Acceptance Evidence | NOT AUTHORIZED | J accepted |

Every phase follows RED → minimal GREEN → focused checks → independent review. A rejected phase returns only to its owning implementation scope; it never authorizes a later phase.

## Non-negotiable boundaries

- Do not modify TASK-016B Language Validator or ADR-024 scope.
- No brand/entity dictionary, token/POS heuristic, cloud/network fallback, external knowledge, new dependency, migration, table, or Artifact kind.
- Reuse existing Pydantic validation, canonical JSON/SHA-256, local Ollama guard, ProviderCall identity, Artifact metadata, and atomic stage completion by adaptation only.
- Phase A cannot create artifacts, cache entries, ProviderCall success, response artifact IDs, filesystem writes, or database registrations.

## Review and integration

WorkBuddy must stop after its assigned phase. Codex performs the independent review. Only an independent
approval of a phase may lead to a separately authorized next phase. Phase D and Phase E are APPROVED;
Phase E is limited to canonical identity, runtime-owned scoring context and pure finalization only. No later
phase is authorized or merge-authorized by this plan.
