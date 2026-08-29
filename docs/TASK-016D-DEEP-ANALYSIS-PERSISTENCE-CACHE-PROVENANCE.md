# TASK-016D — Deep Analysis Persistence / Cache Provenance

Status: `COMPLETE` pending orchestrator acceptance.

## Persisted boundary

Migration `003_add_deep_analysis_persistence.sql` advances SQLite from schema
version 2 to 3. It adds append-only `deep_analysis_persisted_results` and the
partial unique `uq_deep_analysis_persisted_cache_identity` index. Existing
`BEGIN IMMEDIATE`, WAL, foreign-key, checksum, and `user_version` conventions
apply; historical migrations and existing data remain unchanged.

The record retains DACS-1-reconstructable canonical input, selected Evidence
Registry, authorized payload, request/execution/consent/context/validation
profiles, response identities, validated KnowledgeContent, scoring request hash
plus separate `PRIMARY | REPAIR_H2C`, and bounded attempt/fallback provenance.
Provider/adapter/endpoint/model and non-secret credential execution provenance
are carried through A3. `SELECTED_EVIDENCE_ONLY` rejects transcript fields.

No API key, token, authorization header, credential reference, provider request
ID, or unselected transcript is stored. OpenAI live qualification remains
`PENDING / CREDENTIAL BLOCKED`.

The protected revalidation artifacts and the exact cache entry share this one
app-only row and lifetime: there is no independent artifact read or retention
path. This satisfies the contract's relational no-longer-than-cache-entry
limit without inventing an unapproved TTL.

## Trust and cache semantics

`persist_trusted_deep_analysis_success` captures data only from a live
runtime-finalizer admission. Forged, copied, `object.__new__`, and reconstructed
successes have no runtime sidecar admission and are rejected before a
transaction begins. The process-local admission is not persisted.

The reader returns `VerifiedPersistedDeepAnalysisRead`, never
`TrustedDeepAnalysisSuccess`. It parses rows as untrusted and recomputes
A1/A2/A3, validation-policy, response, KnowledgeContent, provenance, attempt,
and cache identities; it rechecks response/content, grounding, KG2, and
language. Any mismatch is a cache miss.

Matching is exact `DeepAnalysisCacheIdentityV1`: A1/A2/A3/validation policy.
Floating profiles are audit-persistable but cache-ineligible. A duplicate exact
key with different KnowledgeContent fails on the unique index; no replacement
or latest-wins behavior exists.

## Reuse

`DIRECT`: existing SQLite, DACS-1, runtime finalizer, Evidence Registry,
KnowledgeContent, and fake OpenAI adapter primitives. No dependency, provider
runtime, credential storage, or second provider was introduced.

## Validation

- Focused persistence/migration/Deep Analysis suite: `146 passed`.
- Full pytest: `1873 passed, 1 existing warning`.
- Target test mypy and `uv run mypy src`: pass.
- Ruff and `git diff --check`: pass.
- `uv run mypy .`: existing `1019 errors / 44 files` baseline; no new TASK-016D
  error.
