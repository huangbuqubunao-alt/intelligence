# TASK-016 — Deep Analysis Provider-Neutral Contract Amendment, Correction R1

Status: **ACCEPTED DESIGN / IMPLEMENTATION NOT AUTHORIZED**
Date: 2026-08-29
Correction basis: `docs/TASK-016-DEEP-ANALYSIS-PROVIDER-NEUTRAL-CONTRACT-INDEPENDENT-REVIEW.md`
Durable decision: [ADR-027](decisions/ADR-027-provider-neutral-deep-analysis-contract.md)

## 1. Scope, authority, and terms

This is the authoritative provider-neutral Deep Analysis contract. It corrects
the reviewed amendment; it authorizes no code, provider, credential, network,
model, persistence/cache, or TASK-016D/E/F work. `Deep Analysis` is the one
canonical subsystem name. `LOCAL`, `CLOUD_FREE`, and `CLOUD_USER_KEY` are
provider kinds, not trust levels.

Provider output, including provider JSON mode, JSON Schema, and tool/function
arguments, is untrusted. The application owns canonical input, payload
authorization, request construction, validation, provenance, cache admission,
and the sole `TrustedDeepAnalysisSuccess` mint. An adapter is a dispatch and
documented-envelope-extraction component; it has no authority to widen
provider-visible content or mint trusted data.

`VerifiedScoringRead.scoring_outcome.result.request_hash` is the only scoring
request identity accepted by Deep Analysis. `scoring_success_provenance` is
only `PRIMARY | REPAIR_H2C` classification and is never a request identity.

## 2. Canonical serialization: DACS-1

Every identity below is `SHA256` over UTF-8 bytes produced by
`DeepAnalysisCanonicalSerializationV1` (**DACS-1**). DACS-1 is JSON Canonical
Serialization (RFC 8785 / JCS) with these mandatory contract rules, which are
also the complete implementation requirements:

- The top-level value is a JSON object with a required `schema_version` field.
  Object member names sort recursively by Unicode UTF-16 code-unit order;
  duplicate keys are forbidden.
- Emit no insignificant whitespace. Encode as UTF-8. Strings use JSON escaping
  exactly as JCS: quote and reverse-solidus are escaped, control code points
  U+0000--U+001F use the shortest JSON escape, and all other Unicode scalar
  values are emitted literally; invalid UTF-8, surrogate code points, and
  non-finite numbers are forbidden.
- JSON booleans are exactly `true` and `false`; null is exactly `null`. An
  omitted field is absent, never interchangeable with a field whose value is
  null. Required-empty values (`""`, `[]`, `{}`) are likewise distinct.
- Arrays preserve declared order. Any order-insensitive collection must first
  be deterministically sorted by its documented semantic key; no serializer may
  reorder a semantic sequence such as messages, Evidence Registry items, tools,
  or fallback edges.
- Numbers use RFC 8785 ECMAScript-number serialization. Values outside that
  interoperable finite domain are invalid. A provider setting for which numeric
  lexical form itself is semantic is represented instead by a required string
  field containing the exact provider-visible lexical token.
- DACS-1 does not normalize, trim, fold case, alter line endings, or otherwise
  rewrite a provider-visible string. Earlier canonical-input construction may
  have a separately versioned transcript normalization rule, but the rendered
  request text and provider-native string values are hashed byte-for-byte after
  rendering. Thus NFC/NFD or LF/CRLF differences that reach the provider do not
  collide.

Each structure below rejects unknown fields unless its named version explicitly
adds them. SHA256 digests are lowercase hexadecimal over the DACS-1 UTF-8
bytes. A different serializer, schema version, omitted/null shape, array order,
or provider-visible character sequence is a different identity.

## 3. Canonical input and authorized payload boundary

`CanonicalDeepAnalysisInputV1` is immutable DACS-1 data. Its A1 identity is
`A1 = SHA256(DACS-1(CanonicalDeepAnalysisInputV1))`. It includes operation and
input schema versions; exact prompt-relevant video metadata identity; canonical
transcript identity/language/normalization version; selected Evidence Registry
identity and canonical selected items; selection/coverage policy; the exact
VerifiedScoringRead request hash and scoring-provenance class; requested output
language; KnowledgeContent schema version; prompt version; and operation
version. Timestamps, credentials, provider request IDs, diagnostics, and
transport observations are not A1 fields.

The application MUST construct `AuthorizedProviderPayloadProjectionV1` from
that canonical input before choosing an adapter. It contains only:

1. `payload_schema_version`, `payload_scope`, and `output_language`;
2. allowed immutable prompt metadata: `video_title`, `channel_name`,
   `published_at`, `duration_seconds`, `source_language`, and the bounded
   public description already included by the current prompt version;
3. the exact selected Evidence Registry items, in Registry order, each with
   only `evidence_id`, `source`, and exact `excerpt`; and
4. if and only if `payload_scope=FULL_TRANSCRIPT`, the exact canonical
   transcript text plus its content hash and normalization version.

No other field is allowed: no transcript path, Vault/user content, unselected
excerpt, diagnostics, internal IDs/hashes, scoring result/reason/dimensions,
credential identifier, or free-form adapter metadata. Every transcript-derived
provider byte therefore comes from a selected Registry item, except the single
explicit `FULL_TRANSCRIPT` field.

The only V1 scopes are `SELECTED_EVIDENCE_ONLY` and `FULL_TRANSCRIPT`.
`SELECTED_EVIDENCE_ONLY` is the default. `FULL_TRANSCRIPT` requires all of:
`coverage_complete=true`; a named-provider exact-run consent decision; an
authorization record allowing that scope; and a current prompt projection that
uses it. `cloud_allowed=true` is never sufficient.

The adapter interface receives exactly `(AuthorizedProviderPayloadProjectionV1,
DeepAnalysisRequestProjectionV1, non_secret_execution_material)`. It MUST NOT
receive a transcript object, transcript repository, artifact path, Vault
handle, or callback capable of recovering broader content. If an unavoidable
transport runtime owns broader storage, its contract still MUST make sending
any content outside the exact projection impossible and auditable; absence of
that capability proof makes the adapter ineligible. The application derives
the cloud payload mechanically from this projection, never from adapter input.

`PayloadConsentIdentityV1 = SHA256(DACS-1({schema_version, consent_mode,
authorization_record_identity, named_provider_id, provider_kind, payload_scope,
allowed_model_constraint, fallback_edge_identity_or_null, exact_run_nonce_or_null}))`.
It is semantic provenance. Scope and this identity enter A2, A3, trusted
provenance, persistence, and cache identity through A2/A3; no output made with
`FULL_TRANSCRIPT` can collide with `SELECTED_EVIDENCE_ONLY`.

## 4. Exact provider-semantic request projection (A2)

`DeepAnalysisRequestProjectionV1` is the complete canonical identity of what
can change provider behavior or output. The application renders it once from
the authorized payload, DACS-1 serializes it, context-checks that same exact
projection, then re-renders and re-hashes immediately before transport. Any
difference fails closed before contact.

`A2 = SHA256(DACS-1(DeepAnalysisRequestProjectionV1))`. Required fields are:

- `schema_version`, `operation`, `A1`, `payload_consent_identity`, exact
  `payload_scope`, and the exact `authorized_payload` object;
- `provider_visible_messages`: an ordered list of `{role, content}` with each
  final rendered text string exactly as sent; a raw single-prompt profile uses
  one `{role: "user", content: ...}` entry and no invented role;
- `provider_visible_request_shape`: the selected provider API semantic form,
  including role structure, input/message placement, and provider-native
  request fields that affect model-visible behavior;
- `structured_output`: selected mode, dialect ID/version, structured-output
  mode/settings, exact schema object or null, and exact ordered tool/function
  definitions plus selection/choice mode or null;
- `generation_semantics`: exact requested output cap, stop sequences, seed,
  temperature/top-p/top-k/reasoning or similar model-behavior settings, and
  every provider-visible semantic setting. Unsupported/omitted settings are
  represented as omitted; requested null is represented as null; and
- `prompt_identity`, `KnowledgeContent schema identity`, `output_language`,
  and `payload_projection_version`.

Transport-only fields are excluded from A2: credentials and references,
authorization headers, provider request/trace IDs, wall-clock timestamps,
timeouts, retry counters, TCP/TLS details, logging switches, and SDK user-agent
formatting. They cannot change the semantic request. Endpoint/deployment/model
execution choice belongs to A3, except a provider-native endpoint field that is
visible to the model or changes semantic decoding, which belongs in both the
provider-visible request shape and its A3 endpoint profile.

### 4.1 Mode-specific A2 coverage

| Mode | A2 must include, in addition to common fields |
| --- | --- |
| `RAW_JSON_PROMPT` | exact rendered prompt/message bytes, exact role structure, exact requested JSON instructions embedded in text, and generation semantics. `structured_output.schema` and tools are null. |
| `PROVIDER_JSON_MODE` | RAW fields plus exact provider JSON-mode switch/object and all provider-native JSON response settings. |
| `PROVIDER_JSON_SCHEMA` | JSON-mode fields plus the exact DACS-1 JSON Schema payload, dialect/version, schema name/strictness and all structured-output settings sent to the API. |
| `TOOL_STRUCTURED_RETURN` | exact messages plus every exact ordered tool/function declaration (name, description, parameters/schema and metadata), tool choice/selection mode, parallel/call limits, and the provider-native structured-return settings. |

An adapter may not substitute an SDK default, add a system instruction, alter a
schema/tool description, or choose a different provider request shape after A2
construction. Such a change requires a new A2. A dispatch-body hash remains an
audit-integrity field only; it is not a replacement for A2.

## 5. A3 execution identity, credential profile, and model policy

`DeepAnalysisExecutionProfileV1` is DACS-1 and
`A3 = SHA256(DACS-1(DeepAnalysisExecutionProfileV1))`. It binds A2 plus
provider kind/ID, adapter identity/version and SDK/HTTP-client version;
provider endpoint/deployment profile; selected model ID; model identity class;
resolved immutable revision/digest when available; qualified capability-profile
identity; context-authority identity; generation-profile identity; idempotency
support profile; and `CredentialExecutionProfileIdentityV1`.

`CredentialExecutionProfileIdentityV1` is an opaque, non-secret DACS-1 hash of
the safe provider account/project/organization scope (when safe to record),
region, endpoint/deployment binding, and provider-side execution-policy profile
that can route or materially alter the result. It changes when any such
semantic execution attribute changes. It never contains an API key, token,
secret, authorization header, credential reference/name, or a reversible secret
derivative. Secret rotation alone does not change it; a change that routes to a
different deployment or project does. A3, cache eligibility, and provenance
therefore change without exposing credentials.

Credential secret bytes, tokens, headers, credential references, and secret
derivatives are excluded from every identity/hash, cache key/value, log,
provenance record, raw-envelope record, and error. Only the non-secret opaque
execution-profile identity is retained where this section requires it.

Model identity is exactly one of `IMMUTABLE`, `VERSIONED`, or `FLOATING`.
`IMMUTABLE` has a stable digest/snapshot; `VERSIONED` has a provider-stable
revision/deployment identity; `FLOATING` is an alias without such a binding.
For `FLOATING`, cross-run cache reuse is disabled. A dispatch is allowed only
under explicit policy and records `reproducibility=NOT_GUARANTEED`; a response-
echoed stable revision may be recorded but cannot retrospectively turn the
attempt into an immutable cached result. Immutable/versioned cache eligibility
also requires the exact resolved identity in A3.

Declared capability describes an API surface, for example
`supports_json_schema=true`; it is never a trust assertion. A qualified
capability is a declared capability backed by an accepted
`ProviderQualificationRecordV1` test/evidence set for the exact adapter,
SDK, endpoint/deployment, model policy, and selected profile. Capabilities can
admit dispatch mechanics only. Every result still traverses all validators.

## 6. Context admission and generation profile

The application computes `ContextBudgetDecisionV1` over the final A2
projection before contact. It binds A2, model/context identity, context window,
input count or conservative bound, structured-output overhead budget,
tool/schema overhead budget, requested output budget, and pass/fail. No
post-response usage value can establish pre-dispatch safety.

| Authority | Safe admission predicate |
| --- | --- |
| `EXACT_LOCAL_TOKENIZER` | A frozen exact tokenizer/model mapping counts the final provider-semantic projection. `input_tokens + structured_output_overhead + tool_schema_overhead + requested_output_tokens <= documented_context_window`. |
| `PROVIDER_DOCUMENTED_TOKENIZER` | An accepted qualification record identifies stable provider documentation, exact model-to-tokenizer mapping, version, and an offline/pre-dispatch count mechanism or provably equivalent upper bound. The same full inequality applies. A vague provider estimate is not authority. |
| `CONSERVATIVE_PROVIDER_CONTRACT` | Accepted provider documentation supplies a stable context window and a versioned, safe upper bound for exact messages/payload plus explicit upper allowances for provider framing, structured-output metadata, and tool/schema metadata. The same inequality applies using bounds. If any overhead cannot be bounded, the profile is ineligible. |

`PROVIDER_REPORTED_USAGE` is corroboration only. It is never an authority kind.
The generation profile records requested/actual supported semantic settings and
its identity enters A2/A3. Unsupported requested settings fail before contact;
a request hash is not a generation determinism promise.

## 7. Consent and directed fallback policy

All cloud authorization is explicit and fail-closed. A consent record is
immutable for a dispatch and is identified by `PayloadConsentIdentityV1`.

| Mode | Cloud dispatch | Provider/payload authority | Fallback | Headless outcome |
| --- | --- | --- | --- | --- |
| `local_only` | Forbidden | One named qualified LOCAL profile; scope is `SELECTED_EVIDENCE_ONLY` unless an independently valid local full-transcript policy exists | No fallback | `PROVIDER_UNAVAILABLE` or other local result; never cloud |
| `cloud_explicit` | Allowed only after this run has an explicit named-provider/scope consent | Exactly one named qualified cloud provider, exact model constraint, credential execution profile, and scope | No fallback | Missing explicit consent is `AUTH_REQUIRED`, zero dispatch |
| `cloud_pre_authorized` | Allowed only by a matching prior authorization record | Each named allowlist entry binds provider ID/kind, model constraints, credential execution-profile identity, payload scope, and allowed directed edges | Default no edge; only named edges below | Valid prior authorization may operate headlessly; otherwise `AUTH_REQUIRED` |
| `per_run_cloud_approval` | Allowed only after a non-expired run-specific affirmative decision | Decision binds named provider/kind, model constraint, scope, credential execution profile, and any one named fallback edge | No automatic fallback; a new per-run decision is required | `AUTH_REQUIRED`, zero dispatch |

`cloud_pre_authorized` is not a Boolean. Its prior record MUST contain issuer,
record version/identity, eligible named providers/provider kinds, allowed model
constraints, allowed payload scopes, credential execution-profile identities,
explicit directed fallback edges, whether new semantic attempts are allowed,
and expiry/revocation policy. An empty, duplicate, or multiple-current provider
selection is `PRE_DISPATCH/PROVIDER_UNAVAILABLE`; a missing credential is
`AUTH_REQUIRED`; neither selects another provider.

Fallback is an explicit directed graph. Default graph: **no edges**. An edge
`from_profile -> to_profile` is valid only if its immutable policy authorizes
that exact edge, the destination is currently qualified/eligible, the same
payload scope is authorized for both profiles, and the destination has its own
matching consent identity. In V1 an edge may automatically advance only after
`PRE_DISPATCH/PROVIDER_UNAVAILABLE`, proven before any request byte is sent.
Every other class, including `TIMEOUT`, `RATE_LIMITED`, `QUOTA_EXCEEDED`,
`STRUCTURED_OUTPUT_INVALID`, `SCHEMA_INVALID`, `GROUNDING_INVALID`, and
`PROVENANCE_INVALID`, is `STOP`; it cannot silently create a new provider or
semantic attempt. A human may later issue a new explicit authorization, which
is a new semantic attempt with a new A3/provenance record. Each attempted
profile is separately recorded.

## 8. Dispatch, retries, and idempotency

One `SemanticAttemptV1` is one intended model generation under one A1/A2/A3.
It may contain `TransportAttemptV1` only if the application proves the provider
did not accept/process the request: DNS resolution failure before connection,
TCP connect failure, or TLS negotiation failure before an HTTP request. These
are recorded individually.

Timeout after body send, connection reset after upload, HTTP 5xx, HTTP 429,
and any incomplete/ambiguous delivery are unknown-delivery terminal results:
no resend and no automatic fallback. A provider response or any validation/
quality/trust failure also ends the semantic attempt. These rules distinguish
idempotent transport replay from a new quality attempt.

SDK/HTTP automatic retries MUST be disabled. An adapter is ineligible if it
cannot disable them or externally surface every attempted send. The only
exception requires an accepted provider qualification proof of provider-side
idempotent deduplication, an A3-bound idempotency support profile, and complete
per-send provenance. Where supported, the non-secret idempotency key is
`SHA256(UTF8("deep-analysis-idempotency-v1\\0" + A2 + "\\0" + A3))`; it is a
transport key, not cache identity and not permission for quality retry.

## 9. Response identity, validation, and mint ownership

`UntrustedDeepAnalysisResponseV1` retains bounded raw provider-envelope bytes
and their hash separately from the semantic payload hash. It has the expected
dispatch hash, response metadata, every transport attempt, provider request ID
if available, and delivery certainty. It contains no secret.

`ProviderEnvelopeIdentity` is SHA256 of exact captured envelope bytes where
available. `ValidatedPayloadIdentity` is mode-specific:

- text-bearing `RAW_JSON_PROMPT`, `PROVIDER_JSON_MODE`, and
  `PROVIDER_JSON_SCHEMA`: SHA256 of the exact complete UTF-8 payload bytes as
  extracted from the documented envelope field, without mutation;
- provider-decoded structured object: SHA256 of DACS-1 canonical JSON only if
  qualification proves the SDK object is lossless for that documented field;
  otherwise the adapter is ineligible; and
- `TOOL_STRUCTURED_RETURN`: SHA256 of DACS-1 canonical JSON of the exact
  selected tool-arguments object, after qualification proves tool selection and
  argument extraction are documented and lossless. The tool name/call choice is
  envelope provenance, not an incidental SDK-format hash.

Validation order is normative:

1. bounded transport and documented-envelope capture;
2. **early dispatch binding**: dispatch hash and expected provider, adapter,
   endpoint/deployment, model/resolved revision, structured mode, A1/A2/A3 and
   scoring request identity must match the response metadata/evidence available
   before semantic parsing;
3. complete documented payload extraction, strict whole-document UTF-8 JSON
   parse, canonical schema/domain validation, Registry grounding, KG2, and
   output-language validation; and
4. **final provenance completeness**: payload consent/scope, all attempt
   history, response identities, validation policy, qualified profile, and
   required immutable revalidation artifacts must bind before mint.

No repair, fence stripping, first-object extraction, truncation, synthesis,
second model, hidden quality retry, alternate provider, cache trust shortcut,
or public/raw-data constructor is permitted. Only the complete application
validator/finalizer pipeline can mint `TrustedDeepAnalysisSuccess`; raw adapter
code, DTO/cache deserialization, and callers cannot fabricate it.

## 10. Failure taxonomy and deterministic precedence

Adapters map provider observations through an accepted, versioned mapping table
that records delivery certainty, bounded provider code, HTTP status, and
envelope state. Provider code/message is observational and redacted; it never
overrides this precedence:

1. `PRE_DISPATCH`: authorization, qualification, credential-reference,
   configuration, selection, or context admission failures. No bytes sent.
2. `TRANSPORT`: no complete provider response. Proven-no-send is
   `NETWORK_FAILURE`; ambiguous or post-send timeout/reset is `TIMEOUT` with
   `delivery=UNKNOWN` and is terminal.
3. `PROVIDER_ACCOUNT` / `PROVIDER_MODEL`: a complete documented provider error
   response maps `AUTH_INVALID`, `QUOTA_EXCEEDED`, `RATE_LIMITED`,
   `MODEL_UNAVAILABLE`, or `PROVIDER_UNAVAILABLE`. For HTTP 429, an accepted
   quota indicator wins over rate-limit; HTTP 401/403 maps `AUTH_INVALID` only
   after credential was supplied, otherwise stage 1 `AUTH_REQUIRED`. A 5xx
   with no complete response remains stage 2 unknown delivery.
4. `RESPONSE_ENVELOPE`: a received response that is not the qualified documented
   envelope or exceeds capture bounds.
5. `PROVENANCE`: early identity/dispatch mismatch, including valid tool
   arguments reporting the wrong provider/model/deployment.
6. `STRUCTURED_OUTPUT`, `SCHEMA`, `DOMAIN`, `GROUNDING`, `KG2`, then
   `LANGUAGE`, in exactly that order.
7. `PROVENANCE`: final provenance-completeness mismatch. `UNKNOWN` is last and
   includes a bounded safe diagnostic.

The first applicable stage wins. Thus a schema-valid fabricated citation is
`GROUNDING_INVALID`; a payload with both malformed envelope and semantic text
is `RESPONSE_ENVELOPE`; and a model mismatch is `PROVENANCE_INVALID` before
tool/JSON semantics are considered.

## 11. Cache identity and revalidation

`DeepAnalysisCacheIdentityV1 = SHA256(DACS-1({schema_version, A1, A2, A3,
validation_policy_identity}))`. `validation_policy_identity` includes every
validator/schema/domain/grounding/KG2/language/provenance policy version. No
provider request ID, timestamp, latency, usage, secret, or observational field
is part of the key.

By construction a cache MISS results from different selected evidence (A1/A2),
prompt bytes/roles (A2), schema/tool schema or structured mode (A2), provider,
model/revision, deployment/endpoint or credential execution profile (A3),
generation profile (A2/A3), output language/payload scope (A1/A2), floating
model use (cache ineligible), or validation policy. Cache lookup must also
verify the complete persisted record; matching hashes alone never mint trust.

016D must persist, in a protected app-only revalidation retention class valid
for no longer than the cache entry, the exact DACS-1 bytes or immutable
content-addressed references to: canonical input; selected Registry including
exact excerpts; authorized payload projection; rendered messages; schema/tool
objects; semantic request projection; context decision; and all validation
artifacts needed to re-run grounding/KG2/language/provenance. It must retain
the source/transcript authority needed by a `FULL_TRANSCRIPT` entry. If any
artifact is unavailable, altered, unauthorized, or fails its content hash, the
entry is a cache miss/failure, never a trusted hit. These protected artifacts
are not logs and are inaccessible to adapters except through a newly built
authorized projection.

Persisted audit data additionally includes A1/A2/A3/cache IDs; provider kind,
ID, adapter/SDK version; endpoint/deployment and credential execution-profile
identities; model ID/class/revision/digest; mode/dialect; payload scope and
consent identity/policy; prompt/schema/generation/context/validation identities;
VerifiedScoringRead request hash and scoring-success provenance; Evidence
Registry identity; envelope/payload hashes and the trusted KnowledgeContent
identity/hash; qualified capability identity; response extraction identity; and
full bounded attempt/failure history. No secret, credential reference, raw authorization data, or
unredacted provider error is persisted. A cache read freshly revalidates all
retained evidence and only then uses the sole mint pipeline.

## 12. Provider qualification gate

Before a candidate may dispatch, an approver must accept immutable
`ProviderQualificationRecordV1`. It includes provider identity; adapter/API and
SDK/client identity/pin; model identity policy and resolved-identity behavior;
selected structured mode/dialect; golden request/response fixtures proving A2
construction and lossless extraction; A3 endpoint/deployment and credential
execution-profile evidence; declared-versus-qualified capability evidence;
context authority proof including schema/tool overhead; consent/payload-scope
compatibility; bounded failure mapping; SDK retry-disable or idempotency proof;
response extraction semantics; strict validator/mint compatibility; provenance
and 016D persistence support; cache eligibility; and privacy/logging/redaction
audit evidence.

The record has one required, independently reviewable evidence item for each
of these acceptance gates:

| # | Qualification proof |
| --- | --- |
| 1 | immutable provider kind/ID and legal endpoint identity |
| 2 | adapter/API surface and SDK/client version/configuration identity |
| 3 | `IMMUTABLE`/`VERSIONED`/`FLOATING` model-identity policy and response-echo behavior |
| 4 | exactly one selected structured-output mode and dialect |
| 5 | golden request fixture proving exact A2 projection/render/hash construction |
| 6 | exact A3 endpoint/deployment, model, and execution-profile fixture |
| 7 | safe pre-dispatch context-authority proof including hidden provider overhead |
| 8 | non-secret credential execution-profile identity/redaction proof |
| 9 | consent and payload-scope compatibility, including selected-only authority |
| 10 | bounded provider-observation to failure-taxonomy mapping |
| 11 | SDK/HTTP retry-disable evidence, or qualified idempotency/retry observability proof |
| 12 | documented complete/lossless response and tool-argument extraction fixture |
| 13 | strict JSON/schema/domain/grounding/KG2/language validator compatibility |
| 14 | complete attempt/provenance/payload/response identity persistence support |
| 15 | cache eligibility proof, including floating-alias exclusion and revalidation artifacts |
| 16 | privacy, retention, and logging-redaction audit with no secret or unauthorized payload disclosure |

The acceptance predicate is all-or-nothing: each required field is immutable,
versioned, reproducible from cited fixtures/documentation, and independently
verified for the exact selected profile. A provider self-attestation, marketing
claim, undocumented estimate, lossy SDK object, hidden retry, or missing proof
makes that capability declared-only and the profile ineligible. This protocol
is the complete next-step gate and requires no reopening of core architecture.

## 13. Supersession matrix

This correction is globally authoritative for **Deep Analysis** and leaves
TASK-016B/C scoring/repair/lineage/Phase G and non-Deep-Analysis subsystems
unchanged.

| Earlier statement | Disposition |
| --- | --- |
| ADR-023 Decision 3/4/5/12 and Consequences: Local-only mandatory / Hybrid cloud-to-local fallback | **SUPERSEDED GLOBALLY FOR DEEP ANALYSIS** by §§3--8. Local remains an explicit profile, not a delivery prerequisite. |
| `SYSTEM_DESIGN.md` §11.1 Ollama/raw/format settings | **RETAINED FOR LOCAL SCORING PROFILE ONLY**; not a Deep Analysis global requirement. |
| `SYSTEM_DESIGN.md` §11.2 and ADR-008 A-03--A-13 old OpenAI AnalysisPayload, retry, cache, and provider assumptions | **SUPERSEDED GLOBALLY FOR DEEP ANALYSIS**; retained as **HISTORICAL EVIDENCE ONLY** for the old OpenAI design and any separate non-Deep-Analysis scoring rules. |
| `SYSTEM_DESIGN.md` §12 generic three retries and Ollama format repair | **SUPERSEDED GLOBALLY FOR DEEP ANALYSIS**; retained for existing scoring/other jobs only. |
| `TrustedLocalDeepAnalysisSuccess`, local A1/A2/A3 names | **SUPERSEDED GLOBALLY FOR DEEP ANALYSIS** by provider-neutral identities and `TrustedDeepAnalysisSuccess`. |
| exact local tokenizer / raw=true / omitted format / Ollama loopback details in local qualification records | **RETAINED FOR LOCAL PROFILE ONLY** and historical qualification evidence; never cloud/global Deep Analysis requirements. |

## 14. Adversarial outcome matrix

| Scenario | Deterministic safe outcome |
| --- | --- |
| A. `local_only` and local unavailable | `PROVIDER_UNAVAILABLE`; zero cloud dispatch and no fallback. |
| B. `cloud_pre_authorized` free quota exhausted | `QUOTA_EXCEEDED`; STOP. No paid/local advance and every attempted send remains recorded. |
| C. Schema-valid fabricated evidence | `GROUNDING_INVALID`; no mint, retry, fallback, cache write, or repair. |
| D. Floating alias silently updates | Attempt records `FLOATING` / non-reproducible; cross-run cache disabled. |
| E. SDK hidden retry after timeout | Adapter is ineligible; no dispatch authorization. |
| F. Adapter has transcript but scope is selected-only | Interface/qualification violation; adapter ineligible and no dispatch. |
| G. Cached X output under current Y provider/model configuration | A3/cache mismatch; cache MISS. |
| H. Wrong VerifiedScoringRead request hash | Early dispatch/final provenance `PROVENANCE_INVALID`; no mint. |
| I. Valid tool result with wrong provider/model identity | Early dispatch binding `PROVENANCE_INVALID`; tool arguments are never semantically parsed as trusted. |
| J. Credential switch changes deployment | Credential execution-profile/A3/cache mismatch; cache MISS and fresh explicit eligibility/consent check. |

## 15. Independent-review closure

| Finding ID | Severity | Original issue | Correction | Normative location | Status |
| --- | --- | --- | --- | --- | --- |
| P0-1 | P0 | A2/cache omitted exact semantic projection | Complete DACS-1 request projection and cache binding | §§2, 4, 11 | FIXED |
| P1-1 | P1 | Adapter could widen transcript payload | Application-owned allowlisted projection; no adapter transcript authority | §3 | FIXED |
| P1-2 | P1 | Deployment/account semantic identity absent | Non-secret credential execution profile in A3/cache/provenance | §5, §11 | FIXED |
| P1-3 | P1 | SDK retries hidden | Retry disable/surface requirement and idempotency exception | §8, §12 | FIXED |
| P1-4 | P1 | Consent/fallback matrix ambiguous | Exact modes, preauthorization record, directed graph, terminal classes | §7 | FIXED |
| P1-5 | P1 | Hashes insufficient for cache revalidation | Protected exact/recoverable revalidation artifacts and fail-closed cache read | §11 | FIXED |
| P1-6 | P1 | Failure mapping/precedence ambiguous | Stage order, delivery certainty, adapter mapping requirements | §10 | FIXED |
| P1-7 | P1 | Older retry/fallback rules conflict | Explicit global Deep Analysis supersession matrix | §13 | FIXED |
| P1-8 | P1 | Capability/qualification gate incomplete | Immutable evidence-backed qualification record and acceptance predicate | §§5, 12 | FIXED |
| P2-1 | P2 | Structured response hash ambiguous | Mode-specific lossless/canonical payload identity | §9 | FIXED |
| P2-2 | P2 | Capability versus trust unclear | Declared vs qualified capability separation | §§5, 12 | FIXED |
| P2-3 | P2 | Local loopback wording missing | Local loopback restriction retained in qualified profile / supersession scope | §§8, 13 | CLARIFIED AS NON-BLOCKING |

P0 unresolved: **0**.
P1 implementation-critical unresolved: **0**.

**DEEP ANALYSIS IMPLEMENTATION REMAINS UNAUTHORIZED.**
**TASK-016B REMAINS CLOSED.**
**TASK-016C REMAINS CLOSED.**
