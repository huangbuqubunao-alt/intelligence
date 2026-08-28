# TASK-016 — Independent Review of the Provider-Neutral Deep Analysis Contract

Status: **REQUEST CHANGES**

Date: 2026-08-28

## 1. Review scope

This was an independent, adversarial, review-only assessment of the
provider-neutral Deep Analysis contract. No implementation, provider call,
credential access, network activity, cache/persistence change, or contract
amendment was performed.

Reviewed primary materials:

- `docs/TASK-016-DEEP-ANALYSIS-PROVIDER-NEUTRAL-CONTRACT-AMENDMENT.md`
- `docs/decisions/ADR-027-provider-neutral-deep-analysis-contract.md`
- `docs/SYSTEM_DESIGN.md`
- `tasks/TASK-016-intelligence-output.md`
- `handoffs/TASK-016.md`

Compatibility and authority materials reviewed:

- `docs/decisions/ADR-023-local-hybrid-cloud-intelligence.md` and ADR-007/008;
- the closed TASK-016B archive and TASK-016C final-freeze, authoritative
  lineage, and graph-schema records;
- the existing `AuthoritativeScoringReader` / `VerifiedScoringRead` contract
  and Evidence Registry, `KnowledgeContent`, grounding, and KG2 references;
- `docs/TASK-016-LOCAL-DEEP-ANALYSIS-PROVIDER-ARCHITECTURE-REVIEW.md`, including
  its 016D and reference-provider expectations.

The review did not inspect `.workbuddy/`.

## 2. Exact reviewed commit

- Branch: `main`
- Commit: `be5a78a5889b39ba32656332081313bd75818a1a`
- Baseline state before this review report: clean

## 3. Overall assessment

The contract correctly preserves the central trust rule: provider JSON,
provider JSON Schema, and tool-return constraints are all untrusted until the
application completes documented-envelope extraction, strict parse,
schema/domain/grounding/KG2/language/provenance validation, then mints a
trusted result. It also correctly retains the authoritative scoring request
binding to `VerifiedScoringRead.scoring_outcome.result.request_hash`, separate
from `PRIMARY | REPAIR_H2C` provenance.

It is nevertheless **not implementation-ready**. One defined cache identity
can collide across materially different provider requests, which is a P0.
Eight P1 gaps would require an implementer to invent privacy, retry, fallback,
credential-profile, persistence, classification, supersession, or
qualification semantics.

## 4. P0 findings

### P0-1 — A2 does not mechanically bind the exact semantic request projection

**Evidence.** Amendment §8 defines A2 with version labels and a
`payload ... projection hash`, but does not define that hash as the canonical
complete provider request projection. §9 places a `request-body hash` only in
the dispatch envelope, outside `DeepAnalysisCacheIdentityV1`.

**Failure case.** Two dispatches can retain the same A1/A2/A3/cache key while
the adapter changes rendered prompt instructions, provider-native schema/tool
declaration, or an SDK request projection. For example, changing a tool's
description or a JSON Schema constraint without changing a manually maintained
version label leaves all stated cache inputs unchanged. The dispatch-envelope
request-body hashes differ, but cache lookup does not consume them.

**Impact.** A cache hit can return output produced under materially different
prompt/schema/input semantics. This violates the stated A2 identity purpose
and the explicit requirement that cache identity invalidate on request change.
It is a trust/provenance cache collision, not a wording issue.

**Required correction.** Define one canonical, versioned
`DeepAnalysisRequestProjectionV1`, or an equivalently complete canonical hash,
that covers the exact semantic outbound projection: rendered prompt messages
and roles, input projection, schema/tool declaration and dialect, output mode,
requested output cap, and every provider-visible setting that is not expressly
an A3 execution-profile field. Make that canonical projection/hash a required
A2 field and cache input. Define which transport-only fields are excluded, and
require re-render/re-hash before contact. The dispatch request-body hash may
remain an audit integrity field, but cannot be the sole binding outside cache
identity.

## 5. P1 findings

### P1-1 — Payload minimization is policy text, not a mechanically closed outbound boundary

**Evidence.** §7 says the payload contains selected Registry items and
“authorized prompt material,” while the adapter is expected to receive the
canonical input. “Authorized prompt material” is not enumerated or tied to a
typed outbound projection. An adapter that can also reach the original
transcript has no stated capability boundary preventing it from placing
unselected transcript text into that material.

**Impact.** The FULL_TRANSCRIPT gate can be bypassed in practice without using
the literal full-transcript field, and reviewers cannot mechanically distinguish
allowed metadata from unselected evidence. This weakens the Evidence Registry
and cloud data-minimization boundary.

**Required correction.** Make the application, not the adapter, construct an
exact outbound `DeepAnalysisPayloadV1` from an allowlisted projection. Give the
adapter only that payload plus non-secret execution material; prohibit original
transcript access at the interface. Enumerate allowed metadata and state that
every transcript-derived byte must be an item in the selected Registry unless
the separately represented, exact-run `FULL_TRANSCRIPT` capability is present.

### P1-2 — Credential secrets are correctly excluded, but safe credential/deployment profile identity is absent

**Evidence.** §16 excludes credential references from A1/A2/A3, cache,
provenance, and the hashed envelope. §8/A3 records endpoint *class*, and §9's
cloud profile mentions a deployment identifier, but neither requires a
non-secret account/project/deployment/endpoint-profile identity in A3 and
provenance.

**Impact.** Rotating a secret is rightly non-semantic, but switching the same
provider/model configuration to a different project, deployment, regional
endpoint, or account policy may change model routing, retention, safety, and
availability while retaining the same cache identity. The contract cannot
represent or audit that distinction.

**Required correction.** Define an opaque, non-secret
`CredentialExecutionProfileIdentity` (or equivalent deployment/endpoint profile
identity) with an explicit rule: it changes when account/project/deployment,
endpoint, or provider-side policy that can affect execution changes; it never
contains secret material. Include it in A3, trusted provenance, 016D records,
and cache eligibility where semantic execution changes.

### P1-3 — SDK automatic retry control is not mandatory or auditable

**Evidence.** §11 permits only one semantic attempt and records application
transport attempts, but does not require adapters to disable SDK automatic
retries or to expose each SDK retry before the first payload byte is sent. The
older cloud contract explicitly requires `max_retries=0` (ADR-008 A-07/A-09).

**Impact.** An SDK may resend an unknown-delivery timeout or a 429 internally.
The payload can leave the machine more than once, the provider can generate
more than once, and `transport_attempt_count` remains false. That defeats the
one-semantic-attempt provenance and can exceed a consent/budget expectation.

**Required correction.** Require automatic SDK/HTTP retries to be disabled.
An exception is allowed only for an adapter that can prove provider-side
idempotent deduplication and externally reports every attempted send; bind that
idempotency proof to A3 and persist all attempts. State that an unobservable
SDK retry makes the adapter ineligible.

### P1-4 — `cloud_pre_authorized` lacks a deterministic fallback admission matrix

**Evidence.** §13 says every validation failure stops with no alternate
provider. §16 nevertheless lets an ordered cloud allowlist select the next
provider after a “classified failure,” without defining eligible classes,
whether a new explicit consent event is needed for each selected provider, or
what happens for missing credentials, quota/rate limit, model removal,
unknown-delivery timeout, and headless per-run approval.

**Impact.** A reasonable implementation can differ on whether quota, model
unavailable, timeout, `PROVIDER_ENVELOPE_INVALID`, or an invalid response may
advance to another provider. That makes privacy egress and provenance behavior
incompatible. The prose “NO SILENT PROVIDER FALLBACK” also becomes ambiguous
when a pre-authorized automatic advance is permitted.

**Required correction.** Add a fail-closed configuration schema and fallback
matrix. For every failure class specify `STOP`, `REQUIRE_NEW_PER_RUN_APPROVAL`,
or `MAY_ADVANCE_TO_NAMED_ALLOWLIST_ENTRY`; make all output/validation/trust and
unknown-delivery failures `STOP`. Bind selected provider, exact payload scope,
and fallback consent basis to the new dispatch A3/provenance. Define missing
provider, empty/multiple selection, missing credential, disappearing free
provider, and headless approval as explicit pre-dispatch outcomes.

### P1-5 — 016D persistence fields are insufficient to perform the required fresh revalidation

**Evidence.** §17 requires persistence of the canonical-input, Registry, and
payload-projection *hashes*, then says cache reads must verify and revalidate
before a fresh mint. The selected Registry's canonical items, canonical input
bytes, and immutable source needed to recompute grounding are not required to
be retained or recoverable by an exact authoritative reference.

**Impact.** A later cache reader can compare hashes but cannot mechanically
re-run grounding or provenance binding if the current transcript/configuration
has changed or is unavailable. Persisting hashes alone encourages either an
unsafe “hash match means trusted” shortcut or an ad-hoc reconstruction policy.

**Required correction.** State the exact revalidation source of truth. Either
persist canonical input/selected Registry bytes (under the specified protected
retention policy), or persist immutable, content-addressed authoritative
artifacts sufficient to reconstruct them exactly. Require a cache miss/failure
when that material is unavailable. Define which raw/structured bytes are
retained, their retention class/access policy, and the revalidation procedure.

### P1-6 — Failure taxonomy lacks deterministic precedence and provider mapping rules

**Evidence.** §15 lists classes, but no classification order or mapping is
given for overlapping conditions: DNS/TLS vs provider unavailable, a timeout
after bytes may have been accepted, HTTP 401 vs missing credential,
429-with-quota body, 5xx-plus-malformed body, a schema-valid payload with a
provenance mismatch, or a response metadata identity mismatch.

**Impact.** Retry/fallback/persistence behavior will differ by adapter and can
mislabel an unsafe or unknown-delivery event as retryable availability. The
reference-provider gate cannot mechanically verify its advertised mapping.

**Required correction.** Define a provider-neutral classification precedence
and a required adapter mapping table. Include delivery certainty, HTTP/provider
status, envelope state, and validator stage. Preserve a bounded provider code
as observational data only, and make unknown delivery a terminal no-resend
class unless the A3-bound idempotency proof applies.

### P1-7 — Supersession leaves actionable retry/fallback contradictions in older normative text

**Evidence.** ADR-023 §Decision 4 still says Hybrid falls back from Cloud to
Local on failure, missing key, budget, or input failure. `SYSTEM_DESIGN.md`
§12 specifies three general retries and an Ollama format repair. The amendment
only lists superseded areas as provider architecture/selection, structured
mode, context authority, identities, and local-only assumptions (§18); it does
not explicitly supersede Deep Analysis retry/error/fallback clauses. ADR-027
also narrows supersession of ADR-023 to architecture and historical router
assumptions.

**Impact.** A future Deep Analysis implementer can reasonably apply the older
generic retry policy or hybrid fallback, contrary to the new one-semantic/no
repair/no alternate-provider rule. This is an implementation-critical
normative conflict.

**Required correction.** Add an explicit supersession matrix naming ADR-023
Decision 4/Consequences, `SYSTEM_DESIGN.md` §12, and any ADR-008 Deep Analysis
retry/failure/caching clauses. State whether they apply only to scoring/legacy
analysis or are superseded for all provider-neutral Deep Analysis. Update the
System Design cross-reference so a reader does not need to infer specificity.

### P1-8 — Capabilities and the first reference-provider gate are not mechanically qualified

**Evidence.** §3 calls capabilities “qualification evidence,” and §17 says a
cloud provider “must prove” a list of properties, but it does not define an
accepted qualification record, evidence required for each capability, test
fixtures, SDK/version pinning, or an approval predicate. In particular,
`supports_strict_json` is advisory and provider claims may be copied into a
capability record without an observed adapter test.

**Impact.** The next task cannot consistently determine whether a provider is
qualified, especially for complete raw capture, hidden token/tool overhead,
model/deployment identity, retry behavior, and credential/redaction handling.

**Required correction.** Specify `ProviderQualificationRecordV1`: immutable
provider/adapter/SDK/model/deployment identity; capability evidence source;
tested request/response fixtures for the selected mode; context proof;
failure-map proof; retry configuration proof; credential/redaction audit; and
an explicit acceptance predicate. A self-attested capability without the
corresponding evidence must be ineligible.

## 6. P2 findings

### P2-1 — Structured object response identity needs one serialization sentence

§12 requires raw complete payload bytes/text, while tool structured returns may
arrive as a decoded object. Specify that a provider is eligible only when it
exposes original arguments bytes, or define the canonical JCS object bytes to
hash after documented extraction. This is not a bypass because lossy SDK
objects are already ineligible, but the wording will improve adapter tests.

### P2-2 — Capability fields should label profile requirements more consistently

`supports_strict_json` is correctly non-trust advisory, but its relationship to
the selected `RAW_JSON_PROMPT` profile is unclear. A short per-mode eligibility
table would avoid treating observed reliability as a capability assertion.

### P2-3 — Local compatibility should explicitly preserve the existing loopback proof wording

The amendment retains local strengthening evidence, but a single reference to
the existing local loopback/address revalidation policy would prevent an
adapter from treating an arbitrary hostname that resolves locally as a local
endpoint. This is clarification only; §11 already gives the right direction.

## 7. Adversarial scenario results

| Scenario | Deterministic safe result under the current text? | Review result |
| --- | --- | --- |
| A. `local_only`, local unavailable | Yes | Explicit `PROVIDER_UNAVAILABLE`; no cloud dispatch. |
| B. `cloud_pre_authorized`, free quota exhausted | No | §16 may permit an allowlist advance but omits the class/consent matrix; P1-4. |
| C. Native JSON Schema output fabricates evidence | Yes | It remains untrusted and fails Registry grounding before mint. |
| D. Floating cloud alias silently changes | Yes for cache safety | Mutable aliases are marked non-reproducible and cache-ineligible; successful provenance must retain that class. |
| E. SDK retries after timeout | No | The one-attempt rule lacks a mandatory SDK retry-disable/audit control; P1-3. |
| F. No FULL_TRANSCRIPT permission but adapter can access transcript | No | “Authorized prompt material” leaves the outbound capability boundary open; P1-1. |
| G. Cache created under provider/model revision X, config now Y | No in the general case | Revision changes should alter A3, but P0-1 allows a different request projection with the same cache key; P1-2 covers deployment/profile changes. |
| H. Response carries the wrong verified scoring request hash | Yes | A1 and validation binding require the exact `VerifiedScoringRead...request_hash`; mint must reject. |
| I. Tool arguments are valid but metadata reports a different model/deployment | Partly | Reported identity must be checked against dispatch; the deployment/profile identity gap remains P1-2. |
| J. Secret changes to another project/deployment | No | Secret exclusion is right, but the non-secret execution/deployment profile is not bound; P1-2. |

## 8. Closed-scope confirmation

- No source, tests, configuration, schema, lockfile, credentials, provider
  implementation, or reviewed contract file was modified.
- No network/cloud/local-model/Vault activity was performed.
- The only intended change is this independent review report.
- TASK-016B and TASK-016C semantics were checked, not reopened or changed.

## 9. Implementation-readiness decision

**REQUEST CHANGES.**

P0 count: **1**

P1 count: **8**

P2 count: **3**

The next implementation gate is not mechanically clear until the required
amendment corrections are accepted. The correction task must resolve P0-1 and
P1-1 through P1-8 without implementing Deep Analysis.

## 10. Required correction checklist

1. Bind A2/cache identity to a complete canonical semantic request projection.
2. Make the outbound payload an application-owned allowlisted type and remove
   adapter access to unselected transcript content.
3. Bind a non-secret execution/deployment profile identity while keeping secret
   values excluded.
4. Disable or fully observe SDK retries and bind any idempotency exception.
5. Define a failure-class fallback/consent matrix and fail-closed config rules.
6. Persist or immutably reference the exact material needed for cache
   revalidation, including Registry grounding.
7. Define failure classification precedence and adapter mapping requirements.
8. Explicitly supersede contradictory Deep Analysis retry/fallback provisions.
9. Define a mechanically checkable provider qualification record and acceptance
   predicate.

## 11. Required reporting answers

| Item | Result |
| --- | --- |
| Reviewed commit | `be5a78a5889b39ba32656332081313bd75818a1a` |
| Strongest finding | P0-1: A2/cache identity does not bind the exact semantic request projection. |
| Scoring binding correct | YES |
| Evidence Registry boundary safe | NO |
| Cloud consent/fallback safe | NO |
| Credentials boundary safe | NO |
| A1/A2/A3 unambiguous | NO |
| Context authority safe | YES |
| Retry semantics safe | NO |
| Cache semantics safe | NO |
| `TrustedDeepAnalysisSuccess` mint safe | YES |
| 016D handoff sufficient | NO |
| Supersession conflicts resolved | NO |
| Reference-provider qualification gate ready | NO |
| Decision | REQUEST CHANGES |

Push/tag: **NO**
