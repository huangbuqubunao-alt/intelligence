# ADR-027: Provider-Neutral Deep Analysis Contract

## Status

Accepted — design only; no provider implementation is authorized.

## Date

2026-08-28

## Context

The completed local qualification protocol found no model qualified under the fixed raw/no-format local profile. Local remains valuable for privacy, offline use, and reproducibility, but it cannot remain a hard delivery requirement. The architecture review selected local and optional cloud as peers behind one untrusted-output validator/mint boundary.

Older local/hybrid descriptions include Ollama and raw-profile assumptions that cannot safely become generic cloud requirements. Conversely, cloud output must not become trusted merely because a provider advertises structured output.

## Decision

Adopt the provider-neutral Deep Analysis contract in TASK-016-DEEP-ANALYSIS-PROVIDER-NEUTRAL-CONTRACT-AMENDMENT.md.

- Provider kinds are LOCAL, CLOUD_FREE, and CLOUD_USER_KEY.
- Provider output is always untrusted. Only the application pipeline may mint TrustedDeepAnalysisSuccess.
- Native JSON/schema/tool output is permitted only as an output constraint. Application repair, first-object extraction, fence stripping, and hidden quality retry are prohibited.
- Dispatch is explicit and privacy-bounded. There is no silent local-to-cloud or free-to-paid fallback.
- Analysis consumes scoring only through VerifiedScoringRead. Its request binding is VerifiedScoringRead.scoring_outcome.result.request_hash. Scoring provenance remains only PRIMARY or REPAIR_H2C.
- Provider/model/profile-aware identities are required. A floating cloud alias is explicitly non-reproducible and cache-ineligible.

## Consequences

Local adapters may retain exact digest, tokenizer, raw-profile, and context proof without imposing them on cloud adapters. Cloud remains behind a provider-specific qualification/authorization gate covering identity, context authority, payload disclosure, credential redaction, failure mapping, and validation/provenance compatibility.

This ADR supersedes ADR-023 only for Deep Analysis provider architecture and its historical local-only/hybrid/cloud router assumptions. It preserves ADR-023 application-owned Evidence Registry, trusted provenance, and no-empty-success intent. It does not alter TASK-016B/C scoring, repair, lineage, Phase G, or AuthoritativeScoringReader semantics.

## Alternatives considered

- Continue local-only qualification: rejected as a product blocker after the fixed protocol, while retaining local explicit mode.
- Cloud-primary: rejected because it weakens the local/offline privacy default.
- Local-primary with implicit cloud escape hatch: rejected because it permits unapproved data egress and leaves local qualification release-critical.
