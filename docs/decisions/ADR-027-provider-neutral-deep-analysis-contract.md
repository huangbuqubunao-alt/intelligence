# ADR-027: Provider-Neutral Deep Analysis Contract

## Status

Accepted — Correction R2; focused independent review is required before
implementation; design only; no provider implementation is authorized.

## Date

2026-08-28

## Context

The completed local qualification protocol found no model qualified under the fixed raw/no-format local profile. Local remains valuable for privacy, offline use, and reproducibility, but it cannot remain a hard delivery requirement. The architecture review selected local and optional cloud as peers behind one untrusted-output validator/mint boundary.

Older local/hybrid descriptions include Ollama and raw-profile assumptions that cannot safely become generic cloud requirements. Conversely, cloud output must not become trusted merely because a provider advertises structured output.

## Decision

Adopt the provider-neutral Deep Analysis contract in
`TASK-016-DEEP-ANALYSIS-PROVIDER-NEUTRAL-CONTRACT-AMENDMENT.md`, Correction R2.

- Provider kinds are LOCAL, CLOUD_FREE, and CLOUD_USER_KEY.
- Provider output is always untrusted. Only the application pipeline may mint TrustedDeepAnalysisSuccess.
- Native JSON/schema/tool output is permitted only as an output constraint. Application repair, first-object extraction, fence stripping, and hidden quality retry are prohibited.
- A2 is SHA256 of the complete DACS-1 canonical provider-semantic request
  projection, including final rendered role/text, authorized payload, selected
  structured-output mode, schema/tool declarations, and semantic generation
  settings. A3 binds provider/adapter/model/deployment and a non-secret
  credential execution profile. Cache identity binds A1, A2, A3, and validation
  policy.
- Dispatch is application-owned and privacy-bounded: adapters receive only the
  allowlisted authorized payload projection. Any fallback plan is a
  pre-dispatch-validated finite DAG with one explicit start node, unique
  semantic provider/model/profile nodes, authorized scope/consent edges, and
  deterministic failure-class matching. Cycles, re-entry, ambiguous matches,
  implicit retries, and silent local-to-cloud or free-to-paid escalation are
  invalid/fail-closed; attempts are bounded by unique authorized nodes.
- Analysis consumes scoring only through VerifiedScoringRead. Its request binding is VerifiedScoringRead.scoring_outcome.result.request_hash. Scoring provenance remains only PRIMARY or REPAIR_H2C.
- Provider/model/profile-aware identities are required. A floating cloud alias
  is explicitly non-reproducible and cache-ineligible. Credentials and their
  references remain absent from identities, caches, logs, provenance, and
  errors.
- SDK/HTTP hidden retries are prohibited. The full application
  validator/finalizer pipeline, not an adapter, cache DTO, or caller, is the
  only mint authority for `TrustedDeepAnalysisSuccess`.
- Fallback policy identity and the complete ordered attempt history are required
  audit/016D provenance, but not A1/A2/A3 or a cache-key dimension. A cached
  success remains bound to its exact successful A1/A2/A3, validation policy,
  provider/model/profile, scope/consent, and fresh revalidation.

## Consequences

Local adapters may retain exact digest, tokenizer, raw-profile, and context proof without imposing them on cloud adapters. Cloud remains behind a provider-specific qualification/authorization gate covering identity, context authority, payload disclosure, credential redaction, failure mapping, and validation/provenance compatibility.

Correction R2 globally supersedes, for Deep Analysis only, ADR-023 Decision
3/4/5/12 and Consequences, the old ADR-008 cloud-analysis request/retry/cache
clauses, and `SYSTEM_DESIGN.md` §12 generic retry/format-repair behavior. The
amendment's supersession matrix classifies old Ollama/raw/format and exact local
tokenizer statements as local-profile-only or historical evidence, rather than
cloud/global requirements. It preserves ADR-023's application-owned Evidence
Registry, trusted provenance, and no-empty-success intent. It does not alter
TASK-016B/C scoring, repair, lineage, Phase G, or
`AuthoritativeScoringReader` semantics.

## Alternatives considered

- Continue local-only qualification: rejected as a product blocker after the fixed protocol, while retaining local explicit mode.
- Cloud-primary: rejected because it weakens the local/offline privacy default.
- Local-primary with implicit cloud escape hatch: rejected because it permits unapproved data egress and leaves local qualification release-critical.
