# TASK-016 — Local + Optional Cloud Provider Architecture Review

Status: **DECISION COMPLETE — NO IMPLEMENTATION AUTHORIZED**

Date: 2026-08-28
Scope: architecture and trust contract after the deterministic local-model
qualification protocol. This document changes neither production code nor the
authorization state of TASK-016D/E/F.

## 1. Decision and evidence boundary

The selected architecture is **Option C — Provider-neutral architecture:
local and cloud are peers behind one Deep Analysis trust contract**.

`QUALIFIED_LOCAL_MODEL=NONE` has one precise meaning: no model qualified under
the predefined local qualification protocol. It does **not** establish that all
local models are incapable. The recorded outcomes are deliberately kept at
their observed granularity:

| Candidate | Observed conclusion | What it does not prove |
| --- | --- | --- |
| `qwen3:8b` | Rejected for structured output under its exact raw/no-format profile | The model cannot work with another approved output constraint or profile. |
| `qwen2.5:7b` | Rejected for structured output under its exact raw/no-format profile | All local models are unreliable. |
| `phi4-mini:latest` | Rejected for structured output under its exact raw/no-format profile | The provider-neutral trust pipeline is invalid. |
| `gemma3:4b` | Blocked by tokenizer identity | It failed a generation or quality test. |
| `llama3.1:8b` | Blocked by tokenizer identity | It failed a generation or quality test. |
| `mistral:7b-instruct-v0.3` | Blocked by acquisition/tag | It failed a generation or quality test. |

The product requirement is trustworthy KnowledgeContent from authoritative
transcript and scoring/evidence. It is not preservation of raw/no-format local
inference. The three evidenced structured-output failures, exact-tokenizer
proof cost, model acquisition/runtime complexity, and M1 Pro resource/latency
observations make further Local-only search an unjustified blocker to that
product outcome. Local still has substantial privacy, offline, zero-marginal
cost, and reproducibility value, so it is retained as an optional mode rather
than discarded.

This review relies on the deterministic qualification record and the existing
Knowledge V2 / Evidence Registry contracts. It introduces no provider choice,
network request, model acquisition, benchmark, credential, dependency, schema
migration, or implementation authorization.

## 2. Options considered

Ratings are relative to the TASK-016 goal under the current evidence; they are
not claims about model capability in general.

| Option | Trust | Privacy | Reliability | Engineering complexity | User cost | Offline capability | Time to product | Reproducibility | Future flexibility |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A. Continue Local-only search until qualification | High if a candidate qualifies; currently blocked | High | Currently low | High and open-ended | High benefit | High | Low | High for a frozen candidate | Low |
| B. Local-primary with optional cloud | High with a shared boundary | High by default | Medium; local remains release-critical | Medium-high | Medium | High | Medium | Medium | Medium |
| C. Provider-neutral local/cloud peers | High with one validator/mint boundary | High by explicit dispatch policy | High; a qualified provider can be selected without implicit fallback | Medium | Configurable | High when local is selected | High | High when the full envelope is persisted | High |
| D. Cloud-primary, local later | High with a shared boundary | Lower default exposure | High where cloud is available | Medium | Medium-high | Low | Medium-high | Medium | Medium |

**Selection: Option C.** It separates product correctness from the current
Local-only qualification dead end without making cloud dispatch implicit or
making local mode disposable. Option B leaves local capability as the primary
release dependency despite the result; Option D weakens the local-first privacy
and offline proposition. Option A optimizes sunk proof work instead of
KnowledgeContent reliability.

## 3. Required decisions

| Decision | Result | Architecture consequence |
| --- | --- | --- |
| Local-only remains mandatory | **NO** | Local-only cannot block trustworthy Deep Analysis delivery. |
| Local mode retained | **YES** | It remains an explicit offline/privacy/zero-marginal-cost provider mode. |
| Cloud mode authorized for future design | **YES** | Design only; each adapter, credential path, network test, and data transmission remains separately authorized. |
| Free-cloud allowed as optional provider | **YES** | It is interchangeable and optional, never a correctness dependency. |
| Paid user-key cloud allowed | **YES** | Only with an explicit provider selection, user-supplied key, and approval of key/data policy. |
| Raw/no-format mandatory for all providers | **NO** | It is one auditable request profile, not the global policy. |
| Provider-native JSON schema may be used | **YES** | It is an output constraint; it does not cross the trust boundary. |
| Application-side output repair allowed | **NO** | No extraction, stripping, syntactic repair, or second-model repair in this architecture. |
| Silent local-to-cloud fallback allowed | **NO** | Cloud dispatch requires an explicit preauthorization or per-run approval. |
| Provider-neutral architecture selected | **YES** | Local/cloud adapters feed the same validation and trusted-success mint. |
| Exact local tokenizer proof required for every provider | **NO** | It remains required only when the selected context authority depends on it. |
| Deferred Gemma/Llama local investigation retained | **YES** | They remain deferred compatibility candidates, not the next critical path. |

## 4. Output constraint is not trust

All provider output is untrusted, whether it arrives as raw text, a provider
JSON mode response, a provider JSON-schema response, or a function/tool
argument. Provider enforcement can reduce malformed-response frequency; it
does not establish grounding, factuality, authorized evidence references,
domain semantics, or provenance truth.

| Output approach | Transport/output constraint | What the application must still do | Policy |
| --- | --- | --- | --- |
| A. Raw / no format | No provider output constraint; application owns the complete visible prompt. | Strict whole-document parse, exact schema, domain, grounding, KG2, and provenance validation. | Supported only where the provider profile qualifies. |
| B. Provider-native JSON mode | Provider requests JSON-shaped output, generally without the full schema guarantee. | The full validation pipeline, including rejection of extra/missing/invalid values. | Supported, but weaker than schema mode. |
| C. Provider-native JSON schema / structured output | Provider constrains decoding to the submitted schema or declared subset. | Parse and validate the received bytes/value; then domain, grounding, KG2, and application-owned provenance validation. | Preferred where accurately advertised and accepted by the adapter contract. |
| D. Tool/function structured return | Provider returns declared tool arguments or function arguments; no tool is executed. | Treat arguments exactly like untrusted structured output; validate every layer. | Optional capability, not a requirement; no provider tool side effects. |

Therefore provider-native JSON schema preserves the trust boundary **when it is
treated solely as an output constraint**. Only the local application validates
and mints a trusted success. A provider cannot create an Evidence Registry,
choose an unauthorized evidence ID, set provider/model/request provenance, or
turn a parseable object into trusted KnowledgeContent.

### Output-mutation policy

| Mechanism | Policy | Reason |
| --- | --- | --- |
| Provider-native constrained decoding | **Permitted** | A declared dispatch capability, captured in request/profile provenance; validation remains downstream. |
| Application-side syntactic repair | **Prohibited** | Mutates the provider bytes and creates ambiguous semantic/provenance ownership. |
| Second-LLM repair | **Prohibited** | It is a second untrusted generation and, if cloud, can create unexpected data egress. |
| First-JSON extraction | **Prohibited** | It silently discards bytes and can accept a different response than the provider returned. |
| Fence stripping | **Prohibited** | It is output mutation, even when deterministic. |

No exception is implied by this review. A future repair design would require a
separate versioned policy, independently auditable input/output artifacts,
explicit dispatch authorization, its own request identity, and unambiguous
provenance. It is not an acceptable hidden fallback.

## 5. Provider modes, explicit dispatch, and privacy

All three conceptual modes belong in the architecture:

| Mode | Purpose | What may leave the machine | Default behavior |
| --- | --- | --- | --- |
| L — Local | Offline, privacy, and zero marginal-cost analysis. | Nothing leaves the machine; loopback is local only. | Available only when its named local provider passes its capability/preflight and context gate. |
| F — Optional free cloud | An optional no-spend route where an available service meets the contract. | Only the approved minimal cloud payload for the named provider/run. | Disabled unless explicitly selected/authorized. Quota, terms, model, and availability are treated as variable. |
| P — User-supplied paid cloud | User-selected higher-quality/reliability option. | Only the approved minimal cloud payload for the named provider/run. | Disabled unless explicitly selected and a user-provided key is available through an approved mechanism. |

The canonical cloud payload is data-minimized, not a copy of local runtime
state. It consists only of the selected, authorized Evidence Registry slices
needed for the request; required output language and schema/prompt material;
and the least video context necessary for the requested analysis. By default it
does **not** include the full transcript, transcript path/hash, Vault content,
user content, diagnostics, internal IDs, request hashes, API-key names,
scoring dimensions, channel/video identity, or the scoring result. A title,
channel name, publication date, duration, or final score may be added only if
the approved prompt requires that field and the provider payload policy lists
it. The local application makes the high-value decision before dispatch.

Sending every selected Registry slice is still a transcript disclosure. A full
transcript is allowed only if the selected Registry is complete and the user
has explicitly authorized that full-payload scope for the named cloud provider
and run/policy. It must be recorded in the dispatch envelope. No mode may send
Obsidian user sections or weekly aggregate transcript text by default.

Free cloud cannot be a primary hard dependency: free tiers, quota, terms,
availability, supported model, and rate limits can change. A free provider is
an optional adapter selected by capability and explicit user policy, never the
basis of product correctness or a silent substitute for a local failure.

### Safer configuration semantics

Do not expose an ambiguous `auto` setting. A future configuration surface
should express consent and provider identity separately:

| Conceptual policy | Meaning |
| --- | --- |
| `local_only` | Dispatch only to the named local provider; failure is explicit. |
| `cloud_explicit` | Dispatch only to one named cloud provider selected for this run/configuration; no fallback. |
| `cloud_pre_authorized` | The user has declared an ordered allowlist of named cloud providers and an exact payload/privacy policy; only then may the router select the next listed provider after a classified failure. |
| `per_run_cloud_approval` | The run stops before cloud dispatch and requires an affirmative per-run approval identifying provider and payload scope. |

`cloud_pre_authorized` is policy-based fallback, not default `auto`. It must
be visible in the configuration and dispatch provenance; a local provider is
never implicitly promoted to a cloud route.

## 6. Generic provider capability contract

Each provider adapter must publish a versioned, immutable capability profile;
unsupported capabilities are explicit `false` or absent, never inferred.
Representative fields are:

```text
provider_kind                 local | free_cloud | paid_cloud
supports_strict_json          boolean
supports_json_schema          boolean
supports_tools                boolean
supports_seed                 boolean
supports_temperature_zero     boolean
supports_deterministic_request boolean
supports_usage_reporting      boolean
supports_input_token_reporting boolean
supports_model_revision_identity boolean
supports_local_only           boolean
supports_offline              boolean
supports_stream_false         boolean
supports_timeout_control      boolean
context_window                positive integer | unavailable
max_input_tokens              positive integer | unavailable
max_output_tokens             positive integer | unavailable
context_budget_authority      versioned provider-specific authority
payload_policy_version        versioned data-minimization policy
```

`supports_deterministic_request` means the application can deterministically
construct and hash the request; it does not promise deterministic generation.
`supports_seed` and `supports_temperature_zero` improve reproducibility but
are not prerequisites for safety. A provider claiming JSON schema/tools must
also record the exact structured-output mode and accepted schema dialect or
profile, so an adapter cannot silently downgrade it.

Minimum Local Deep Analysis requirements are: a fixed provider/model identity;
an explicit endpoint class; bounded non-streaming response handling;
timeout control; a versioned context-budget authority capable of accepting or
rejecting the exact request before dispatch; deterministic application request
identity; a known structured-output mode; raw response capture/hash; and the
full local validation pipeline. Native schema, tools, seed, temperature zero,
usage reporting, and exact tokenizer control are conditional capabilities—not
universal preconditions. A provider lacking a needed capability is rejected
before dispatch with an explicit classified failure.

## 7. Context and token-accounting policy

Every dispatch is preceded by provider-specific context safety. The selected
`ContextBudgetAuthority` receives the exact rendered request, requested output
budget, and capability profile, then produces either a versioned acceptance
record or an explicit pre-dispatch rejection. It must reserve for output and
provider framing; post-response usage can validate accounting but cannot make
an unsafe pre-dispatch request safe retroactively.

| Mode/authority | Pre-dispatch authority | Post-dispatch evidence |
| --- | --- | --- |
| Exact local tokenizer mode | Frozen tokenizer identity/artifact, no-special-token rules, exact rendered-prompt count, and local runtime parity where required. | Provider evaluated-token count where available; mismatch fails integrity checks. |
| Cloud provider-authoritative mode | Documented provider model/context contract plus a conservative, versioned byte/character/prompt bound and a configured output reserve. | Returned usage/input token report when available; absence is recorded, not invented. |
| Cloud documented-tokenizer mode | Frozen documented provider tokenizer/mapping, if independently available and approved, plus exact request count and output reserve. | Returned usage reconciled against the request/profile when available. |

Thus exact local tokenizer proof remains a valuable local authority but is not
mandatory for every cloud provider. Cloud adapters must never pretend a
byte/character bound is an exact token count. If the provider cannot furnish a
safe documented context contract and no conservative authority can establish a
pre-dispatch bound, the adapter is not eligible for that request.

The generic acceptance predicate is:

```text
accepted only if
  input_budget(exact request, selected authority)
  + requested_max_output_tokens
  + provider_reserved_tokens
  <= advertised_context_window
```

All inputs to that predicate, its authority version, and whether the bound is
exact or conservative belong to provenance. The application must not truncate
after computing request identity; any selection/reduction occurs before the
final canonical input and hash are constructed.

## 8. Provider trust envelope and ownership

For one dispatch, define a versioned conceptual object
`AnalysisDispatchTrustEnvelopeV1`. It is application-created before contact and
completed after local validation. At minimum it contains:

```text
envelope_schema_version
provider_kind, provider_id, provider_version, endpoint_class
model_id, model_revision_or_digest, model_identity_source
capability_profile_version, context_budget_authority_version
request_profile_version, prompt_version, schema_version
analysis_policy_version, privacy_payload_policy_version
requested_mode, executed_mode, structured_output_mode
input_identity, canonical_analysis_input_hash
evidence_registry_identity, scoring_request_identity
generation_settings, request_hash, request_body_hash
context_budget_decision, requested_output_tokens
dispatch_consent_kind, cloud_payload_scope
started_at, finished_at, response_metadata, usage_metadata
raw_response_hash, raw_response_length, structured_content_hash
validation_policy_version, validation_result, failure_class
```

`input_identity` binds authoritative transcript/content identity, selected
evidence identity/coverage, verified scoring request identity, output
language, and canonical analysis input. `response_metadata` is bounded and
safe: status/result classification, provider request ID if available, and
reported model/usage values. It never contains a credential or unbounded raw
provider body.

Trust ownership is deliberately asymmetric:

| Owned by | May supply | May not supply |
| --- | --- | --- |
| Application | Canonical input, Registry, prompt/schema/profile versions, request hash, provider selection, consent, context decision, and all provenance fields. | Trust in provider content without validation. |
| Provider adapter | A bounded transport request and raw response plus observed response/usage metadata. | Domain objects, Registry entries, trusted provenance, state transitions, cache decisions, or fallback decisions. |
| Provider/model | Candidate JSON or structured arguments only. | Evidence text/IDs outside the Registry, provenance, trusted success, or hidden repair instructions. |
| Validator/mint boundary | A trusted provider-neutral success only after every required validation passes. | Mutation/repair of candidate output. |

## 9. Validation and trusted success

```text
Authoritative Transcript
        -> application-owned Evidence Registry
        -> Canonical Analysis Input
        -> selected Provider Adapter
        -> Provider Structured Output (UNTRUSTED)
        -> strict JSON / structured-value parse
        -> KnowledgeContent schema validation
        -> domain validation
        -> grounding validation against authorized Registry only
        -> KG2 validation
        -> provenance and envelope validation
        -> TrustedDeepAnalysisSuccess | explicit failure
```

The successor name should be **`TrustedDeepAnalysisSuccess`**. It describes the
trust property rather than the execution locality. The local-specific
`TrustedLocalDeepAnalysisSuccess` should not be repurposed as a broad alias;
the new provider-neutral mint must validate a complete envelope and retain
local compatibility fields as local-mode provenance. Because Local Deep
Analysis implementation and 016D serialization are still unauthorized, no
runtime compatibility migration is required now. The future contract-freeze
task must define the exact successor type and any explicit boundary adapter.

Every failure remains explicit. Examples include unavailable local runtime,
missing key, disabled cloud policy, quota/rate limit, provider timeout,
context rejection, unsupported capability, malformed output, validation
failure, and unapproved fallback. None may yield a trusted success or be
rewritten as a different provider outcome.

## 10. Fallback and offline semantics

The default fallback policy is **A — no automatic fallback**. A local failure
must not send a transcript or Evidence Registry to any cloud endpoint. The
router may use a cloud provider only under `cloud_pre_authorized` or after
`per_run_cloud_approval`, and the envelope must record that consent basis,
selected provider, and payload scope before contact.

| Condition | `local_only` | `cloud_explicit` / approved cloud mode |
| --- | --- | --- |
| Configured provider unavailable | Explicit `PROVIDER_UNAVAILABLE`; no cloud dispatch. | Explicit `PROVIDER_UNAVAILABLE`; no alternate provider unless the configured policy explicitly authorizes one. |
| Network unavailable | Not applicable to local provider; local failure remains classified. | Explicit network/provider failure; no local substitution unless separately configured. |
| Cloud quota exhausted / rate limited | Not applicable. | Explicit `RATE_LIMITED` or budget failure; no hidden provider/model switch. |
| Cloud key missing | Not applicable. | Explicit `CREDENTIAL_UNAVAILABLE`/configuration failure before dispatch. |
| Local fails and cloud is configured but not preauthorized | Explicit local failure; stop. | Cloud dispatch requires a fresh per-run approval. |

Offline behavior is deterministic: local mode can succeed only when the named
local provider and its capability/context prerequisites are available; cloud
modes fail explicitly when their network/credentials/quota prerequisites are
not available. The system must never report an empty analysis as a successful
provider substitution.

## 11. Provenance, cache, and persistence implications

016D must persist enough exact information that local, optional-free-cloud,
and user-key paid-cloud outputs cannot be confused. At a minimum persist the
completed trust envelope’s provider kind/id/version, endpoint class, model
id/revision/digest, capability and request profile versions, structured-output
mode, prompt/schema/policy versions, canonical analysis-input and Evidence
Registry identities, scoring request identity, generation settings, request
and body hashes, payload/consent scope, response/usage metadata, raw and
validated-content hashes, and validation-policy/result.

Provider output itself never supplies those fields. Any mismatch between a
persisted structured result and its envelope is a trust-integrity failure, not
a cache hit.

The conceptual cache key must include at least:

```text
operation
provider_kind + provider_id + provider_version + endpoint_class
model_id + model_revision_or_digest
request_profile_version + structured_output_mode
prompt_version + schema_version + validation_policy_version
analysis_input_hash + Evidence Registry identity + scoring request identity
generation settings profile + privacy payload policy version
```

This intentionally prevents a result from one provider/model/profile/privacy
scope being returned for another. Provider-reported usage and an availability
timestamp are audit fields, not cache-key substitutes. Cache recovery must
verify the complete provenance binding, hashes, and validation result before
the result can be trusted again.

## 12. What survives from local qualification

None of the completed local evidence is discarded. It becomes a local-provider
capability record and informs generic abstractions:

| Existing evidence | Surviving generic abstraction |
| --- | --- |
| Model acquisition method, exact digest, runtime version | `ModelIdentity` / `ProviderIdentity` evidence. |
| `TokenizerIdentity` and special-token rejection | A local `ContextBudgetAuthority` option. |
| `RawProfileIdentity` and exact prompt accounting | Versioned `RequestProfile` and reproducibility evidence. |
| Raw/non-raw parity observations | Local adapter capability qualification evidence. |
| M1 Pro latency, RSS, memory-compression/swap observations | Local feasibility/operational capability evidence. |
| Strict parse/schema/grounding/KG2 failures | Negative qualification evidence for the exact profile only. |

Gemma and Llama remain **deferred local compatibility candidates**. They are
not abandoned, and they are not immediately investigated before this
architecture change. Their current blockers are tokenizer identity, not model
output quality; resolving access/proof work has lower expected product value
than establishing a reliable provider-neutral contract. They may be revisited
only under a separate bounded authorization with an updated capability profile.

## 13. Release implications

Multi-provider support adds release gates; it does not clear existing ones.
Before a cloud adapter can ship, its task must address: provider-specific
privacy disclosure and payload scope; API-key storage/isolated-process
handling; provider terms, quota, and pricing disclosure; model and SDK
license/dependency review; data-transmission and retention behavior; telemetry
defaults and opt-in; configuration and offline-failure documentation; bounded
logs/artifacts; and real-provider smoke authorization. A free tier receives
the same review as a paid provider. No key, cloud request, telemetry, SDK
addition, lockfile change, or release policy is authorized by this review.

## 14. Required next engineering sequence

1. **Next implementation gate:** approve a provider-neutral TASK-016 contract
   amendment that freezes the capability profile, trust envelope,
   context-budget authorities, explicit dispatch/consent policies, trusted
   successor boundary, cache-key dimensions, and permitted payload schemas.
   It must reconcile the Task-016 M1/M2 sequencing with this decision before
   any source change.
2. Create a narrowly scoped implementation task for the provider-neutral
   boundary and its offline Fake/contract tests. It must not contact local or
   cloud models.
3. Select and authorize exactly one reference structured-output adapter only
   after provider terms, payload scope, dependency/key handling, and model
   identity are approved. Do not select a commercial provider in advance.
4. Implement the selected adapter with provider-native structured output where
   supported, bounded transport, explicit failure mapping, and the generic
   validation/mint pipeline.
5. Independently validate the trust pipeline using offline fixtures, including
   malformed, extra-field, unauthorized-evidence, grounding, KG2, provenance,
   and no-fallback cases.
6. Implement 016D as provider-aware provenance/cache persistence and recovery
   only after the generic trusted-success contract is accepted.
7. Implement 016E Note V2 against provider-neutral trusted KnowledgeContent.
8. Implement 016F Weekly V2 against the same trusted/provenance-aware result.
9. Revisit optional local-provider compatibility, including Gemma/Llama, only
   in a separately authorized bounded qualification task.

This sequencing makes reliable analysis the critical path while preserving a
strict local/offline mode and preventing uncontrolled data egress.

## 15. Final required answers

```text
1.  Local-only remains mandatory: NO
2.  Local mode retained: YES
3.  Cloud mode authorized for future design: YES
4.  Free-cloud allowed as optional provider: YES
5.  Paid user-key cloud allowed: YES
6.  Raw/no-format mandatory for all providers: NO
7.  Provider-native JSON schema may be used: YES
8.  Application-side output repair allowed: NO
9.  Silent local-to-cloud fallback allowed: NO
10. Provider-neutral architecture selected: YES
11. Exact local tokenizer proof required for every provider: NO
12. Deferred Gemma/Llama local investigation retained: YES
13. Next implementation gate: approve the provider-neutral TASK-016 contract
    amendment described in section 14.1 before any provider boundary, adapter,
    credential, or 016D/E/F implementation work.
```

**LOCAL DEEP ANALYSIS IMPLEMENTATION REMAINS UNAUTHORIZED.**

**TASK-016B REMAINS CLOSED.**

**TASK-016C REMAINS CLOSED.**
