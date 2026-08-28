# TASK-016 — Deep Analysis Provider-Neutral Contract Amendment

Status: **ACCEPTED DESIGN / IMPLEMENTATION NOT AUTHORIZED**
Date: 2026-08-28
Decision basis: [provider architecture review](TASK-016-LOCAL-DEEP-ANALYSIS-PROVIDER-ARCHITECTURE-REVIEW.md), Option C.
Durable decision: [ADR-027](decisions/ADR-027-provider-neutral-deep-analysis-contract.md).

## 1. Scope and terminology

This is the exact implementation contract for the provider-neutral Deep Analysis layer. It authorizes no source change, provider adapter, credential, network call, persistence/cache work, or TASK-016D/E/F work.

The canonical subsystem name is **Deep Analysis**. Local Deep Analysis is historical local-profile/qualification terminology, not the subsystem or trusted-success name. Canonical future names are:

| Concern | Canonical name | Owner / trust |
| --- | --- | --- |
| provider interface | DeepAnalysisProvider | adapter boundary; cannot mint success |
| pre-contact request | DeepAnalysisDispatchEnvelopeV1 | application-created |
| provider result | UntrustedDeepAnalysisResponseV1 | untrusted observation |
| model business candidate | KnowledgeContent | untrusted until all validation passes |
| validated knowledge | KnowledgeResult | application-created |
| runtime mint | TrustedDeepAnalysisSuccess | provider-neutral trusted success |

No persisted/public interface is silently renamed. A future local-only compatibility path, if needed, is explicit and one-way; it must not let a historical local trusted type impersonate a provider-neutral success.

TASK-016B and TASK-016C remain closed. Their scoring admission, repair, lineage, Phase G, and AuthoritativeScoringReader semantics do not change. The sole scoring ingress is AuthoritativeScoringReader to VerifiedScoringRead. The trusted scoring request identity is exactly VerifiedScoringRead.scoring_outcome.result.request_hash. scoring_success_provenance remains only PRIMARY or REPAIR_H2C; it is never a request hash or substitute identity.

## 2. Provider model

The core contract contains no vendor/commercial names.

| provider_kind | Meaning |
| --- | --- |
| LOCAL | Endpoint meets local endpoint policy. |
| CLOUD_FREE | Optional free/no-spend route. It may still require account/key. |
| CLOUD_USER_KEY | Explicit user-key cloud route. |

Each dispatch has all three distinct fields:

| Field | Meaning |
| --- | --- |
| provider_kind | privacy, endpoint, and consent class |
| provider_id | stable opaque application ID for one adapter/provider integration; never URL, secret, or model |
| adapter_version | application translation/extraction/capability contract version |

## 3. DeepAnalysisProviderCapabilitiesV1

Every field is mandatory to declare; false or unavailable is explicit. Mandatory below means mandatory record field, not universally true.

| Field/type | Meaning | Required force | Unsupported result |
| --- | --- | --- | --- |
| capabilities_schema_version: str | record format | normative | provider ineligible |
| supported_structured_output_modes: set | executable modes without downgrade | normative | CAPABILITY_UNSUPPORTED |
| supports_strict_json: bool | can request one JSON document; not trust | advisory | raw prompt may remain eligible |
| supports_json_schema: bool | accepts declared schema/profile | required when schema mode | schema mode unavailable |
| supports_tools: bool | accepts declared no-side-effect tool return | required when tool mode | tool mode unavailable |
| supports_seed: bool | accepts seed | advisory | record unsupported |
| supports_temperature: bool | accepts explicit temperature | required when requested | profile ineligible |
| supports_temperature_zero: bool | accepts exactly zero | advisory | cannot claim zero |
| supports_stream_false: bool | bounded non-stream response | eligibility required | provider ineligible |
| supports_usage_reporting: bool | reports usage | advisory | usage unavailable |
| supports_input_token_reporting: bool | reports input usage | advisory | no reconciliation |
| supports_model_revision_identity: bool | exposes immutable revision/digest | required for reproducible cache reuse | mutable-alias rule |
| supports_deterministic_request: bool | app can deterministically construct request; no generation promise | eligibility required | provider ineligible |
| supports_offline: bool | dispatch without network | required only for offline claim | cannot satisfy offline config |
| supports_local_only: bool | meets local endpoint policy | required for LOCAL | not selectable as local |
| supports_timeout_control: bool | controls connect/whole-request deadlines | eligibility required | provider ineligible |
| context_authority_kind: enum | context proof kind in §10 | eligibility required | provider/request ineligible |
| max_context_tokens: positive int or unavailable | advertised total context | required for token authorities | safe conservative contract required |
| max_output_tokens: positive int or unavailable | safely requestable output cap | normative | profile ineligible |
| schema_dialect_id: str or unavailable | exact schema/tool dialect | required in schema/tool modes | mode unavailable |
| raw_response_limit_bytes: positive int | bounded envelope/payload capture | eligibility required | provider ineligible |
| failure_mapping_version: str | §15 mapping version | eligibility required | provider ineligible |

Capabilities are qualification evidence, not a provider claim that trusts output.

## 4. Minimum eligibility

Before any dispatch the selected adapter/profile MUST: have complete capabilities and provider identity; have known model ID and identity classification; use one selected structured mode without downgrade; retain documented complete response bytes and bounded raw envelope bytes; construct the request deterministically; support stream=false and bounded timeouts; have an accepted exact-projection context decision; map failures explicitly; pass endpoint/TLS-or-loopback, consent, credential-reference, and data-minimization checks before contact; and feed only the §13 validator/mint path.

Native schema/tools, seed, temperature zero, usage reporting, exact local tokenizer proof, and immutable cloud revision are not universal prerequisites. A capability needed by the selected profile fails closed before contact.

## 5. Structured output modes

| Mode | Constraint and allowed extraction | Schema sent | Still mandatory |
| --- | --- | --- | --- |
| RAW_JSON_PROMPT | prompt requests one JSON document; read documented complete response field | prompt description only | all validation |
| PROVIDER_JSON_MODE | provider JSON-output switch; read documented complete response field | not necessarily | all validation |
| PROVIDER_JSON_SCHEMA | provider constrains decoding to declared schema dialect | yes | all validation |
| TOOL_STRUCTURED_RETURN | declared no-side-effect tool/function arguments; read documented complete arguments and execute no tool | where supported | all validation |

Selecting a documented complete provider envelope field is normal transport extraction, not repair. The adapter preserves original bounded envelope and payload bytes. An SDK that exposes only a lossy parsed object is ineligible for V1.

Prohibited: fence stripping, first JSON/object extraction, trailing-prose truncation, regex/syntax repair, automatic missing-brace/quote/field synthesis, second-LLM repair, and hidden retry-until-valid. The complete extracted payload is accepted or rejected.

## 6. CanonicalDeepAnalysisInputV1

This immutable application object is canonical JCS UTF-8: sorted keys, no insignificant whitespace, finite values, no implicit defaults. A1 is SHA256 of exact canonical bytes.

All fields are semantic A1 fields:

- schema_version = canonical-deep-analysis-input-v1; operation = deep-analysis-v1; analysis_operation_version;
- video_content_identity: video_id and metadata_content_hash for exactly prompt-relevant metadata;
- authoritative_transcript_identity: transcript_content_hash, transcript_language, normalization_version;
- selected_evidence_registry: registry schema/hash/items, selected_evidence_count, total_evidence_count, coverage_complete;
- verified_scoring_request_hash;
- scoring_success_provenance: PRIMARY or REPAIR_H2C only;
- output_language, KnowledgeContent schema version, prompt version, and evidence-selection policy version.

verified_scoring_request_hash MUST equal VerifiedScoringRead.scoring_outcome.result.request_hash. A scoring result/reason/dimension is not input unless a future prompt version explicitly adds it and therefore changes A1. Timestamps, endpoint URL, credential reference, provider request ID, transport attempt count, host facts, and diagnostics are not A1 fields.

## 7. Evidence Registry and minimization

Transcript authority remains the verified canonical runtime transcript. Caller, provider, latest-artifact lookup, and cloud response cannot provide replacement text, path, slice, or evidence.

Retained V1 Registry construction:

1. Split canonical LF-terminated text by LF; remove only final mandatory empty item and blank/whitespace-only lines.
2. Preserve remaining lines exactly; split any line longer than 256 Unicode code points into consecutive non-overlapping exact slices.
3. Enumerate source order and select the deterministic prefix admitted by context/payload policy. IDs ev-0001 through ev-0032 match ^ev-[0-9]{4}$ and remain positional even for duplicate text.
4. Each application-created item has evidence_id, source=transcript_sample, exact excerpt, transcript source_content_hash, and no timestamp except a separately verified stable mapping.

Maximum selected entries remains 32 for V1. total_evidence_count counts the deterministic pre-selection universe; selected_evidence_count counts items. coverage_complete means every eligible slice was selected; it says nothing about output grounding/completeness. RegistryHash is SHA256 of canonical JSON object {schema, video_id, transcript_content_hash, items}; items are source order. Unknown, wrong-case, malformed, duplicate, unselected, or missing-required references fail grounding.

Provider payload contains only selected Registry items and authorized prompt material. Cloud default excludes full transcript, transcript path, Vault/user content, diagnostics, internal request hashes, API-key identifiers, scoring reason/dimensions/result, and channel/video identity.

Full transcript MAY be sent only if coverage_complete is true, named provider and exact run explicitly authorize FULL_TRANSCRIPT, policy/version plus projection hash bind A2/A3/provenance, and the prompt needs it. cloud_allowed=true alone is never that authority.

## 8. A1/A2/A3 request identity

All identities are versioned canonical JCS UTF-8 SHA256 values with validated fields.

| Identity | Canonical fields | Reuse invalidated by |
| --- | --- | --- |
| A1 CanonicalDeepAnalysisInputIdentityV1 | exact canonical input | semantic input, selection, scoring request/class, language, content/prompt/operation version |
| A2 DeepAnalysisRequestIdentityV1 | schema version, A1, prompt/content-schema versions, output mode/dialect, payload policy/scope/projection hash, requested max output | prompt/schema/payload/mode/output change |
| A3 DeepAnalysisExecutionProfileIdentityV1 | schema version, A2, provider kind/ID/adapter version/endpoint class, model ID/revision/class, capability hash, context-authority identity, generation-profile identity | provider/model/profile/context/generation change |
| DeepAnalysisCacheIdentityV1 | schema version, A2, A3, validation-policy version | any request/execution/validation change |

Provider request ID, timestamp, latency, status, and usage are observational and never cache key.

## 9. Dispatch envelope and model identity

DeepAnalysisDispatchEnvelopeV1 is created and hashed before transport. It includes schema version, A1/A2/A3; provider kind/ID/adapter version/endpoint class; model ID/revision/class; structured mode/dialect; prompt/schema; canonical input/evidence/scoring-request hashes; scoring provenance class; settings/context authority and accepted budget decision; timeout policy/values; payload policy/scope/consent; and request-body hash. Requested timestamp/trace IDs are observability only. It contains no credential or credential reference in hashed form.

| Identity profile | Minimum | Cache/reproducibility |
| --- | --- | --- |
| LOCAL | model ID and exact digest/revision when exposed; adapter/runtime proof | exact revision/digest required; TokenizerIdentity/RawProfileIdentity may strengthen A3 |
| cloud snapshot/deployment | model ID plus snapshot/revision/deployment ID | cache allowed with immutable identity |
| floating cloud alias | MUTABLE_ALIAS plus response-echoed identity if available | dispatch only under explicit allow_mutable_model_alias=true; non-reproducible and cache reuse prohibited |

Unknown requested model identity is ineligible. A floating alias is never called immutable.

## 10. Context authority and generation profile

| ContextAuthorityKind | Safe pre-dispatch predicate |
| --- | --- |
| EXACT_LOCAL_TOKENIZER | frozen tokenizer counts exact final projection; input + requested output + reserve <= max context |
| PROVIDER_DOCUMENTED_TOKENIZER | approved documented tokenizer/mapping counts exact projection and same predicate |
| CONSERVATIVE_PROVIDER_CONTRACT | versioned provider contract proves conservative upper bound for exact projection plus output/framing reserve; explicitly not exact token count |
| PROVIDER_REPORTED_USAGE | post-response corroboration only; never safe pre-dispatch authority by itself |

ContextBudgetDecisionV1 binds authority/version, exact projection hash, advertised bounds, calculated count/conservative bound, output/framing reserve, and pass/fail. Application re-renders, re-hashes, and rechecks before contact; it never truncates after decision. No safe accepted authority is pre-dispatch CONTEXT_BUDGET_EXCEEDED or CAPABILITY_UNSUPPORTED.

GenerationSettingsProfileV1 records requested and actual seed, temperature, output cap, stream flag, allowed settings, and determinism_claim: REQUEST_DETERMINISTIC, GENERATION_NOT_GUARANTEED, or stronger supported claim. Unsupported features are explicit; a hashable request is not deterministic generation.

## 11. Timeout, transport, and retry

V1 permits one semantic generation attempt. It requires stream=false, positive bounded connect and complete-request timeout, bounded reads, and redirects disabled. Cloud requires HTTPS normal certificate/hostname verification and no proxy/redirect substitution. Local permits HTTP only for explicitly verified loopback address/port and never a resolved remote host.

Transport retry is allowed only when no request bytes were sent, or provider idempotency derived from A3 contractually deduplicates. It uses the same envelope/profile and records transport_attempt_count. It is forbidden after payload receipt, unknown-delivery timeout, provider response, validation failure, quota/rate limit, or quality failure. It is not a quality retry or fallback.

## 12. UntrustedDeepAnalysisResponseV1

It captures schema version, dispatch-envelope hash, provider envelope format/version, raw provider envelope bytes/text with SHA256/length, raw complete structured payload bytes/text with SHA256/length, transport/HTTP status, finish/done reason, provider request ID if available, reported provider/model/revision if available, usage/timing metadata, and transport_attempt_count.

It remains untrusted despite authenticated transport or provider schema success. Raw retention/persistence mechanics are deferred to 016D.

## 13. Security-significant validation order

1. transport and documented envelope validity, including byte limit;
2. provider/model/adapter identity consistency with dispatch;
3. complete documented structured-payload extraction, with no mutation;
4. strict whole-document UTF-8 JSON parse;
5. canonical KnowledgeContent schema validation, including unknown-field rejection;
6. domain validation;
7. Evidence Registry grounding against exact selected registry;
8. Knowledge Graph V2 validation;
9. normative output-language validation;
10. canonical-input/request/scoring-request/provenance/payload-scope/identity/validation-policy binding validation;
11. mint TrustedDeepAnalysisSuccess.

Order is normative because each stage establishes the next input. No trusted success exists before all mandatory validators pass. Failure stops: no repair, alternate provider, persistence, or cache hit.

## 14. TrustedDeepAnalysisSuccess

Future exact-type/private-mint data has:

- trusted semantic data: validated KnowledgeResult (validated KnowledgeContent plus application-owned selected Registry), A1/canonical-input hash, Registry hash, exact verified scoring request hash, and separate scoring-success provenance class;
- bound provenance/observability: provider kind/ID/adapter version, model identity/class/revision, endpoint class, mode/dialect, prompt/schema/operation versions, A1/A2/A3/cache identities, settings profile, context decision, payload scope/consent, validation policy/version/result, response envelope/payload/content hashes, and bounded usage/timing/request-ID metadata.

It cannot be reconstructed from raw output, DTO, cache record, or caller mapping. Persistence remains untrusted evidence until revalidated and freshly minted.

## 15. Failure taxonomy

| Category | Classes |
| --- | --- |
| pre-dispatch/policy | PROVIDER_UNAVAILABLE, AUTH_REQUIRED, MODEL_UNAVAILABLE, CAPABILITY_UNSUPPORTED, CONTEXT_BUDGET_EXCEEDED |
| transport | NETWORK_FAILURE, TIMEOUT, PROVIDER_UNAVAILABLE |
| provider/account | AUTH_INVALID, QUOTA_EXCEEDED, RATE_LIMITED, MODEL_UNAVAILABLE, PROVIDER_ENVELOPE_INVALID |
| output/validation | STRUCTURED_OUTPUT_INVALID, SCHEMA_INVALID, DOMAIN_INVALID, GROUNDING_INVALID, KG2_INVALID, OUTPUT_LANGUAGE_INVALID |
| trust | PROVENANCE_INVALID |
| residual | UNKNOWN with bounded original diagnostic |

AUTH_REQUIRED means no approved credential reference before contact; AUTH_INVALID means provider rejected supplied credential. PROVIDER_ENVELOPE_INVALID is an undocumented/mismatched envelope; STRUCTURED_OUTPUT_INVALID includes strict parse failure. Future application error mapping must preserve class.

## 16. Fallback, configuration, credentials, and logs

Default: **NO SILENT PROVIDER FALLBACK**. Local failure never sends data to cloud; free failure never sends data to paid cloud. New provider/model selection means a new A3.

| Configuration mode | Behavior |
| --- | --- |
| local_only | one named local provider; no cloud or fallback |
| cloud_explicit | one named cloud provider with explicit payload scope/consent; no fallback |
| cloud_pre_authorized | ordered named cloud allowlist, each with payload policy/credential reference; may select next listed cloud after classified failure, never local-to-cloud |
| per_run_cloud_approval | stop before cloud dispatch for affirmative run-specific provider/payload choice |

There is no ambiguous provider=auto. cloud_allowed alone is neither provider selection nor full-transcript permission. Configuration includes selected provider, permitted model/profile override, fallback policy, payload permission, and credential reference.

Credentials are indirect future environment/keychain/secret-config references. They never enter A1/A2/A3, request/body hashes, cache keys, logs, provenance, raw envelope persistence, or exception text. CLOUD_USER_KEY requires explicit user-supplied credential. CLOUD_FREE uses the same boundary when it needs a key/account.

Default logs may include provider/model IDs, hashes, payload-scope label, timing, bounded usage, validation result, and failure class. They must not include keys, credentials, authorization headers, full cloud request/transcript/excerpts, raw output, Vault/user content, or unredacted provider errors. Debug raw evidence is a future access-controlled bounded-retention policy and disabled by default.

## 17. 016D handoff, local compatibility, and cloud gate

016D must persist provider kind/ID/adapter/endpoint; model ID/revision or mutable alias classification; mode/dialect; capability/context/settings/payload/validation identities; A1/A2/A3/cache identity; canonical input/Registry/payload-projection hashes and consent; exact verified scoring request hash plus separate provenance class; response envelope/raw/validated-content hashes; and bounded usage/timing/request-ID observations.

The cache key is DeepAnalysisCacheIdentityV1; provider request ID is excluded. Cache reads verify all provenance/content bindings and revalidate before a fresh mint.

Local may add exact digest, TokenizerIdentity, RawProfileIdentity, raw/no-format profile, runtime version, and exact token parity as stronger proof. Cloud need not acquire Hugging Face tokenizer artifacts or emulate Ollama. Historical raw=true, omitted format, Ollama endpoint/version, and num_ctx are local profile facts, not global requirements.

Gemma/Llama remain **DEFERRED LOCAL COMPATIBILITY CANDIDATES**. Their current tokenizer blockers are neither cloud choices nor output-quality failures; no test/acquisition is authorized.

Before a first cloud reference provider is authorized, it must prove provider/adapter/model identity; selected mode/dialect and complete raw capture; safe context authority; credential/redaction and data/retention policy; minimal/full payload consent; failure/timeout/no-fallback mapping; full validation/mint compatibility; and all 016D provenance fields without leakage.

## 18. Implementation order and hierarchy

Later order:

1. P0 independent contract and ADR review, no code.
2. P1 provider-neutral types, serializers, capabilities, identities, failures, offline contract tests.
3. P2 dispatch/eligibility/payload/context/untrusted-response/full validation pipeline with fakes, no real provider.
4. P3 separately qualified and authorized one reference adapter.
5. P4 runtime integration from VerifiedScoringRead to TrustedDeepAnalysisSuccess.
6. P5 TASK-016D provider-aware persistence/cache verification.
7. P6 TASK-016E Note V2.
8. P7 TASK-016F Weekly V2.

This amendment and ADR-027 supersede historical Local Deep Analysis statements only for provider architecture/selection, structured-output mode, context authority, request/provenance/cache identity, and local-only assumptions. They retain strict whole-document parse, application-owned Registry, domain/grounding/KG2 validation, and no trust before mint.

TrustedLocalDeepAnalysisSuccess and local A1/A2/A3 are superseded conceptual names. TokenizerIdentity and RawProfileIdentity are retained as optional local strengthening evidence. Gemma/Llama are deferred. The PRD retains product scope. TASK-016B/C documents retain priority for scoring admission, repair, lineage, Phase G, and AuthoritativeScoringReader.

**No implementation-critical trust question remains unresolved.**

**LOCAL DEEP ANALYSIS / DEEP ANALYSIS IMPLEMENTATION REMAINS UNAUTHORIZED.**
**TASK-016B REMAINS CLOSED.**
**TASK-016C REMAINS CLOSED.**
