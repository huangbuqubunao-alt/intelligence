# V1X-DR-001: V1.x Content Deep Analysis

## Status

Accepted — records Owner-frozen V1.x product scope and the R3 architecture
consensus. Implementation proceeds on a separate V1.x branch; M13 dogfood stays
isolated.

## Date

2026-10-01

## Authority and scope of this record

This is a **new V1.x decision record**. It does **not** amend
`PRODUCT_CONSTITUTION.md`, `V1_PRODUCT_SPEC.md`, or
`V1_IMPLEMENTATION_ROADMAP.md`.

Deep Analysis, Obsidian Deep Analysis publishing, Home Knowledge Delta,
Research History, and Research Diff are **V1.x** capabilities. They were never
V1 commitments, and the historical V1 scope documents must not be rewritten to
imply otherwise. Product vocabulary authority remains
`PRODUCT_CONSTITUTION.md` > `V1_PRODUCT_SPEC.md` > `V1_IMPLEMENTATION_ROADMAP.md`
> Demo, unchanged by this record.

Deep Analysis extends the product; it does not rewrite V1 scope.

## Context

The M13 7-Day Dogfood closed a Summary/Evidence provenance P0 set whose design
lesson generalizes beyond Summary:

> MODEL-LOCAL OR TEMPORARY REFERENCES MUST NEVER BECOME DURABLE USER-FACING
> PROVENANCE. Backend Evidence authority owns durable Evidence identity. Any
> capability that cites Evidence must converge onto that same authority rather
> than introducing a parallel Evidence system.

Repository inspection during R3 confirmed that a large Deep Analysis
implementation already exists and is **dormant**: contracts, an admission
runtime, an append-only persistence store, cache/provenance machinery, and three
provider adapters. It is reachable only from the synthetic OpenAI qualification
harness. No HTTP route, no orchestration entry, and no user-facing surface exist.

R3 reviewed the proposed V1.x direction and returned product and technical
consensus, with the claim-structure fork resolved by Owner as option **B1-a**.

## Decision

### 1. Product position

Deep Analysis (深度分析) is a **Content-level advanced action**. Its
first-version product responsibility is *"Analyze one piece of Content deeply."*

It is **not** a primary navigation section, **not** a Summary replacement, and
**not** a new domain chain parallel to `Content → Intelligence → Topic`.

Initial scope is **Content only**. Deep Analysis of Intelligence or Topic is
deferred.

Deep Analysis answers a different question from Summary:

- Summary: "What does this content say?"
- Deep Analysis: "What are the important conclusions, what evidence supports
  them, what is uncertain, what it means for me, and what should I investigate
  next?"

### 2. Five-role first-version product contract

User-facing output focuses on exactly five concepts:

1. `CORE_CONCLUSION` / 核心结论
2. `KEY_EVIDENCE` / 关键证据
3. `UNCERTAINTY` / 不确定性
4. `RELEVANCE_TO_USER` / 对我的意义
5. `NEXT_QUESTION` / 下一步追问

Each projected claim carries text, epistemic type, confidence, and output
language. Stance is claim-relative. No single global result-level stance may
override claim-level semantics.

The five roles are enforced at the **model boundary**, not only in the UI: the
live provider request asks for these five concepts and nothing else (§4a). They
are carried in the existing frozen `KnowledgeContent` structure through a
deterministic compatibility mapping. They are not a second persistence schema,
and they do not weaken or fork the existing validated content contract.

### 3. RELATION_TO_KNOWLEDGE and KNOWLEDGE_DELTA are deferred

Neither role is model-answerable in the first version. R3 verified that
`CanonicalDeepAnalysisInputV1` carries no Intelligence, Topic, or prior-state
context, so asking the model for these roles would fabricate authority.

They belong to later Knowledge Delta / bounded knowledge-context work. They must
not be silently reintroduced.

Knowledge Delta is a **separate subsystem**, not part of Deep Analysis.

### 4. Backend durable Evidence becomes the citation authority (Phase 1B)

The dormant Deep Analysis `EvidenceRegistry` must **not** remain an independent
provenance authority. It is demoted: it may exist only as an internal transient
candidate set inside the admission boundary.

**Phase 1B final requirement (unchanged and not weakened).** A transient ref must
be resolved through backend validation into durable Evidence identity
(`evidence.evidence_id`, minted deterministically by `state.build_evidence_id`)
**before** it becomes a persisted authoritative citation.

**Phase 1A transitional reality (recorded honestly).** Phase 1A does **not** yet
add `deep_analysis_evidence`, so it cannot mint or persist that durable
relationship. In Phase 1A the contract that actually holds is narrower:

- Transient candidate refs exist only inside the admission boundary.
- They are **never** user-facing: no API, frontend, Note, or Obsidian projection
  exposes a candidate ref, and no projection labels one as `evidence_id`.
- They are **never** authoritative provenance. Nothing reads them as Evidence
  authority; `evidence_citation_status` stays
  `PENDING_DURABLE_EVIDENCE_CONVERGENCE` until Phase 1B.
- The frozen dormant persistence contract still stores the model-visible registry
  internally for compatibility. Those stored ids are marked
  `TRANSITIONAL_NON_AUTHORITATIVE` and no trusted read path treats them as
  durable Evidence.

No alias, backfill, or synthetic promotion is introduced to paper over this gap.
The gap closes in Phase 1B, not in the presentation layer.

**Phase-1A results are not trusted Note / export authority.** Until Phase-1B
durable-Evidence convergence completes, a Phase-1A result is categorically
ineligible as a trusted Note V2 source, Obsidian source, Evidence-bearing export
source, durable citation authority, Topic authority, or Knowledge Delta fact
source. This is a **fail-closed compatibility gate**, derived from the durable
persisted request projection so it survives restart and cannot be forged by a
caller. Phase-1A results may be persisted, read after restart, and shown in the
Content panel.

**Compatibility `knowledge_graph.topics` is inert carrier data only.** It exists
solely because the frozen historical validator requires compatibility material.
It is not a product Topic, not a relation to existing user knowledge, not
Intelligence, and not Knowledge Delta. Because trusted Note/export eligibility is
disabled, it never reaches any trusted projection.

For the first version:

- **Citable:** trusted timed-transcript Evidence only.
- **Context only:** title, channel, description, other metadata. Context may
  inform reasoning but can never become citation authority.

No fabricated timestamps. No fabricated Evidence. No metadata promoted merely
because a model cited it.

### 4a. The five-concept model boundary holds at the provider (Phase 1A)

Hiding a field in the UI is not sufficient. The **live** activated provider
request must not ask the model to author it either, and neither may a response
bypass the contract on the way back.

The Phase-1A model contract requests exactly the five first-version concepts and
nothing else. `RELATION_TO_KNOWLEDGE`, `KNOWLEDGE_DELTA`, and
`knowledge_graph.related_themes` / `future_watch_topics` / `entities` are **not
requested**, because the model is not given the personal knowledge context they
would require.

**Every model response entering the live path must validate as the five-role
contract.** There is no pass-through for a historical `KnowledgeContent` payload:
such a response is itself schema-valid for the frozen carrier and would otherwise
be admitted. A response that fails five-role admission is rejected outright,
persists nothing, and cannot be resurrected by a restart. The historical carrier
is *output* of the compatibility mapper, never an alternate admission contract.

Where the frozen structure still requires deferred fields, the backend fills them
deterministically as empty compatibility values; they are never model-authored and
never presented. The final versioned five-role durable contract remains Phase 1B
work.

**Epistemic meaning is never rewritten.** Each role is routed to a carrier field
that accepts its permitted claim kinds. A payload the carrier cannot represent
faithfully — or that exceeds a carrier field's capacity — is rejected by the
Phase-1A schema itself with an explicit contract rule, rather than crashing the
mapper, being silently truncated, or being relabelled. `why_it_matters` is
derived only from genuinely inference-typed material; a fact conclusion is never
relabelled as an inference to satisfy a historical validator.

**Phase-1A provider contract limits are intentionally bounded by the lossless
capacity of the historical compatibility carrier.** Phase 1A is a compatibility
activation layer, so its provider-facing schema is deliberately narrower than the
future durable schema: a `core_conclusion` claim is capped at the carrier's
500-character summary limit, and each role's cardinality is capped at its carrier
target's capacity. This narrowing is **temporary and deliberate** — it guarantees
that anything the Phase-1A model contract accepts is representable without
truncation or claim loss. Phase 1B may introduce a native durable five-role
contract with independently chosen limits.

**Accepted input must always map.** If `DeepAnalysisPhase1AModelOutput` accepts a
payload, the deterministic compatibility mapping MUST succeed. No schema-valid
input may crash mapping.

**`why_it_matters` derives only from `relevance_to_user`.** The frozen historical
carrier requires a semantically valid `why_it_matters`, and in the Phase-1A
five-role contract only relevance material may supply it. `relevance_to_user` is
therefore **required and must contain at least one claim**. A payload without it
is rejected by the Phase-1A schema. No conclusion, uncertainty, or next-question
claim is ever relabelled as a relevance inference, and relevance is never
synthesized. This is a **temporary compatibility constraint forced by the frozen
carrier**, not a statement about the product: Phase 1B may define a native
five-role contract without it.

**Text is canonicalized at the admission boundary.** Leading and trailing Unicode
whitespace is trimmed exactly once, when the Phase-1A model contract accepts a
claim. Length limits are evaluated on the canonical value, text that becomes
empty is rejected, and the accepted model object already holds its final text.
Mapping, persistence, restart, and public projection then preserve that value
verbatim; no further trimming or truncation happens at read time. This keeps the
accepted-input mapping invariant and the round trip lossless in the same
boundary.

**No public projection loss.** Each of the five public roles is projected from
exactly one carrier field, so the round trip model output → mapping → persistence
→ restart → API → frontend preserves claim count, text, epistemic kind, and
ordering. Nothing is silently dropped, and a plural role is never reduced to its
first element.

### 4b. Qualification is never configuration truth

`CONFIGURED != AVAILABLE != QUALIFIED != PRODUCTION_ELIGIBLE`.

Phase 1A ships no qualification authority or receipt, so production composition
resolves to an **empty capability** and the product reports a truthful
`NOT_QUALIFIED` state. A raw environment variable may not mint qualification
truth; the retired `YIA_DEEP_ANALYSIS_LOCAL_QUALIFIED` flag no longer registers
any route. Tests and local development inject a route explicitly through the
service constructor. `qwen2.5-coder:7b` remains a dev/test candidate.

### 4c. Generation time is authoritative

A result's generation time is read from the persisted row, never from the current
read time, so repeated reads and a full restart report the same value. A missing
or malformed persisted timestamp fails verification instead of being replaced
with a fabricated time.

### 4d. Reason codes drive localized copy

The backend exposes a stable machine `reason_code` alongside its developer
diagnostic prose. The user interface localizes on the code, so Chinese mode never
surfaces raw English status, reason, POST-error, or confidence text. This applies
to read states, run failures, and per-claim confidence codes alike; localization
never relies on string-matching arbitrary backend prose.

The local HTTP boundary preserves safe machine-readable error details
(`reason_code`, `availability`, `consent_required`) so real loopback clients
localize by code rather than prose, and `ErrorState` renders the backend message
as diagnostic text instead of primary product copy. Normal Deep Analysis UI does
not render raw backend prose at all: the backend message stays on the error
object, in logs, and in debug instrumentation, while the panel shows localized
copy only. Role headings use the same UI-language mechanism in both directions: no
hardcoded Chinese label leaks into English mode, and no engineering enum name is
ever shown.

### 4e. Trusted timestamps must be timezone-aware

Persisted Deep Analysis timestamps (`created_at`, `validated_at`) must carry an
explicit offset. A timezone-free value is ambiguous rather than implicitly UTC
and fails verification, so no forged generation time is ever served. On corruption
the product substitutes neither the current time nor an assumed UTC offset.

### 5. Canonical-only / no-timed-Evidence Content fails closed

`evidence` requires a Content identity and a mandatory `start_ms`/`end_ms` span,
so a Content with a canonical transcript but no verified timed cues can never
mint durable Evidence. Deep Analysis for such Content must fail closed with an
honest unavailable state. It must never degrade to metadata-only citation and
must never invent a timestamp.

### 6. No generic router

No generic advanced model/task router is introduced. Narrow Deep Analysis
capability qualification is used, reusing the existing contract surface
(`DeepAnalysisProviderCapabilities.qualified_capability_profile_identity`,
`DeepAnalysisExecutionProfileV1.qualified_capability_profile_identity`).

### 7. Model qualification is an activation gate, not an architecture gate

Architecture consensus does not require a qualified model to exist.
Implementation may proceed; **user-visible production activation remains gated**
until at least one model/provider combination qualifies.

When nothing qualifies, the Deep Analysis path must truthfully show an
`UNAVAILABLE` / `NOT_QUALIFIED` state. It must never silently use a weaker
model, and must never fabricate a result.

`CONFIGURED ≠ AVAILABLE ≠ QUALIFIED ≠ PRODUCTION_ELIGIBLE`. Small local models
such as `qwen2.5-coder:7b` remain dev/test-only and are not assumed
production-qualified.

### 8. Cloud requires explicit per-run consent

If a cloud route is used: explicit user initiation, explicit per-run consent,
cost status disclosed **before** consent, no silent local→cloud fallback, no
surprise paid call, and no automatic retry that could duplicate a paid dispatch.
Bounded Evidence/context packaging is the default; an unrestricted full
transcript is not.

### 9. Cache identity

Results created under materially different Deep Analysis validation rules must
not alias each other. The existing distinct `validation_policy_identity` is the
capability identity for this purpose and is already part of cache identity
(A1 + A2 + A3 + validation policy). No existing unrelated scope field is
overloaded, and no new field is introduced for this.

### 10. Obsidian merge-key correction

Obsidian remains a one-way, user-owned projection; SQLite remains authority.

The Deep Analysis Obsidian **merge key is not `result_identity`**.
`result_identity` equals `provenance_identity` and incorporates the provider
envelope and payload identity, so it changes on every execution and cannot merge.

The merge key is a deterministic derivation of:

```text
content_identity + output_language + knowledge_content_schema_identity
```

`result_identity` and `cache_identity` are retained inside the note as
provenance fields. The Deep Analysis note uses its own note builder, validator,
and merge key, and is not forced through the existing video-note path. Obsidian
Deep Analysis publishing is deferred to Phase 2.

### 11. Branch and migration isolation

M13 dogfood continues independently. V1.x development uses a **clean separate
worktree and branch**, never branched from the dirty M13 working tree. No V1.x
feature is backmerged into M13 during the 7-day dogfood. M13 fixes may later be
forward-merged or cherry-picked into V1.x through normal reviewed Git history.

**Migration ordinal hazard.** M13 holds an in-flight migration `029` in its dirty
remediation. The clean reviewed anchor carries migrations only through `028`.
V1.x must not independently allocate a conflicting `029`; it reserves `>= 030` or
re-reads the actual next ordinal after M13 integration.

**Backup/Restore verification gap (identified by R3).** `_REQUIRED_TABLES` in
`backup_restore.py` is a 23-entry subset of 63 durable tables, checked with
subset semantics, and has no coverage test. `deep_analysis_persisted_results` is
already outside it. Phase 1B must add the new table and the existing Deep
Analysis table to backup verification, and add a coverage assertion. Until then,
"no durable table silently outside backup authority" is **not** enforced and must
not be claimed as satisfied.

## Consequences

- Phase 1A activates the existing dormant path without a schema migration. The
  five-role contract is delivered as a backend projection, and user-facing
  citations stay unavailable until Phase 1B durable-Evidence convergence.
- No new migration is allocated in Phase 1A. The ordinal stays at `028`.
- No qualified production model is implied. The honest unavailable state is the
  expected default until one qualifies.
- Knowledge Delta, Research, and Obsidian Deep Analysis remain unimplemented by
  design.

## Deferred

Generic router; Deep Analysis of Intelligence/Topic; persisted Knowledge Delta;
read watermarks; durable Research diff; Obsidian→SQLite round-trip; per-Following
output-language override; non-YouTube Evidence types (structurally impossible
under the current `evidence` schema and requiring a Constitution-level decision).
