# TASK-016 Kimi Live Reference Provider Qualification

Status: `IMPLEMENTED / LIVE UNQUALIFIED` — the raw R2 profile passed `2/2`,
but the production adapter passed only `1/2` and its second case was
`SCHEMA_INVALID`. R1 remains historical `1/2` evidence (30-second transport
timeout); it is not the current profile result. The adapter is not a runtime
default or fallback-eligible provider.

## Approved runtime credential gate

`MOONSHOT_API_KEY` was available through approved ephemeral runtime injection.
It was used only in the provider-call process and was not written to source,
tests, fixtures, logs, identities, provenance, database state, or this record.

## R1 official API profile discovery (historical)

Moonshot documents an OpenAI-compatible Chat Completions API callable through
the existing OpenAI Python SDK configured with `base_url`. The English global
endpoint is `https://api.moonshot.ai/v1`; the matching official China endpoint
is `https://api.moonshot.cn/v1`.

The global endpoint/account availability probe returned only `AUTH_INVALID`.
Before any successful qualification attempt, the profile was corrected once for
that factual regional endpoint mismatch. `GET /v1/models` on the final endpoint
confirmed the selected model is available to the account.

| Field | Frozen Kimi qualification value |
| --- | --- |
| Provider kind / canonical ID | `CLOUD_USER_KEY` / `kimi` |
| Endpoint | `POST /v1/chat/completions` at `https://api.moonshot.cn/v1` |
| SDK | Existing locked `openai==2.46.0`, with `base_url`; no dependency change |
| Model / identity class | `kimi-k3` / `FLOATING`, with no claimed resolved revision |
| Structured-output mode | `PROVIDER_JSON_MODE`, `response_format={"type":"json_object"}` |
| Schema trust | Application-owned schema instruction only; JSON mode is an untrusted output constraint, not trusted schema validation |
| Generation | `reasoning_effort="low"`; K3 fixed defaults are not sent |
| Output / context | `max_completion_tokens=4096`; documented 1M context with conservative UTF-8-byte prompt accounting, 16,384 instruction reserve, and 4,096 output reserve |
| Context authority | `CONSERVATIVE_PROVIDER_CONTRACT` |
| Timeout / SDK retries | 30 seconds / `max_retries=0` |
| Payload scope | `SELECTED_EVIDENCE_ONLY` |
| Credential execution identity | Static non-secret execution-profile identity only; never based on API-key bytes |

Moonshot documents K3’s 1M context, `reasoning_effort`, and fixed generation
parameters in its [model parameter reference](https://platform.moonshot.cn/docs/api/models-overview).
The [Chat Completions API](https://platform.moonshot.cn/docs/api/chat) documents
JSON object mode, its prompt requirement for expected fields/types, and
`max_completion_tokens`. Although a JSON Schema mode is documented, this profile
does not claim a strict-schema guarantee. The [Quickstart](https://platform.moonshot.cn/docs/guide/start-using-kimi-api)
documents SDK/base URL compatibility; [List Models](https://platform.moonshot.cn/docs/api/list-models)
documents availability lookup.

## Harness and outcomes

An ephemeral, isolated non-production harness built an admitted
`CanonicalDeepAnalysisInputV1`, authorized selected-evidence projection, A2,
A3, and a conservative context profile. It made one Chat Completions request
per case, then fed the exact untrusted response to the existing
provider-neutral finalizer. It did not mint trust, repair output, retry, use a
fallback, or persist request/response data.

| Case | Representative input | Result |
| --- | --- | --- |
| 1 | Privacy-preserving research workflow; selected evidence requires generated claims to be tied to corroborated excerpts | `PASS` through strict JSON, schema, grounding, KG2, language, and provenance |
| 2 | Reliable incident communication; selected evidence requires an evidence-linked handoff timeline | `FAIL` at `TRANSPORT` with `TIMEOUT` |

Case 2 emitted no completion marker before the frozen 30-second request bound
ended, and no harness process remained afterward. Delivery is treated as
unknown and the request was not resent. This is a failure of the tested frozen
profile, not evidence that Kimi generally cannot satisfy the application
contract.

## Decision and preserved boundaries

Kimi is **unqualified under this tested frozen profile** (`1/2`). No
`KimiDeepAnalysisProviderAdapter`, fake or real adapter qualification, product
pipeline, 016D persistence run, Note V2/Weekly V2 acceptance artifact, or
TASK-016G code was created. OpenAI and TASK-016B/C/D/E/F semantics were not
modified. Local remains currently unqualified as a future offline/privacy
capability.

Output repairs: `0`. Semantic retries: `0`. Provider fallback: `0`.

## R2 timeout-profile correction — frozen before fresh qualification

R1 remains historical evidence: its 30-second profile passed Case 1 and timed
out at transport on Case 2 (`1/2`). It is not counted toward R2.

The committed provider-neutral contract makes **bounded transport** normative;
it does not set a globally required 30-second value. The exact current types
also place `timeout_profile_identity` on the prepared dispatch envelope rather
than as a direct `DeepAnalysisExecutionProfileV1`/A3 field. A2 remains the
complete provider-semantic request projection and does not contain this
transport timeout. A1 is the authoritative input identity and is unaffected.

The change is nevertheless material to the qualification profile. R2 therefore
uses a new A3-bound `qualified_capability_profile_identity` and a new dispatch
timeout-profile identity. Cache identity changes transitively through A3 (and
the selected floating model remains cache-ineligible). No other profile field
changes.

| Field | R2 frozen value |
| --- | --- |
| Qualification profile | `kimi-deep-analysis-reference-capabilities-r2-timeout-120s-v1` |
| Timeout profile | `moonshot-chat-timeout-120s-v2` |
| Timeout | 120 seconds, bounded |
| SDK / semantic retries | `0` / `0` |
| Provider / model / endpoint | `kimi` / `kimi-k3` / unchanged China Chat Completions endpoint |
| Structured mode, messages, prompt/schema/operation, generation, context, scope | Unchanged from R1 |

The 120-second value is a single bounded correction: R1 reached the full
30-second client bound, K3 is a reasoning model, and Moonshot documents a large
context/output capability. It is within the authorized 90–120 second range and
is neither streaming nor an unbounded timeout. A second timeout escalation is
not authorized.

Contract evidence: [provider-neutral amendment, §§5 and 8–10](TASK-016-DEEP-ANALYSIS-PROVIDER-NEUTRAL-CONTRACT-AMENDMENT.md)
and [ADR-027](decisions/ADR-027-provider-neutral-deep-analysis-contract.md).

## R2 fresh qualification result

Fresh R2 qualification began at `0/2`; neither R1 case was reused. Both
independent representative calls passed the full untrusted-response finalizer
chain, including strict whole-document JSON, schema, domain, grounding, KG2,
language, provenance, and runtime-owned trusted-success verification.

`R2 RAW QUALIFICATION: 2/2 PASS`.

## Production-adapter qualification result

The thin `KimiDeepAnalysisProviderAdapter` was implemented only after raw R2
passed. Its deterministic no-network boundary suite passes, including R2 profile
mapping, selected-evidence-only request projection, timeout/retry binding,
credential sentinel non-leakage, envelope normalization, malformed envelope,
model mismatch, usage/request-ID observationality, error mapping, no repair,
and no trust mint.

Fresh real qualification through that exact adapter is **not qualified**:

| Adapter case | Result |
| --- | --- |
| 1 | `PASS`: actual adapter response → finalizer → verified trusted success |
| 2 | `FAIL`: `SCHEMA_INVALID` at `SCHEMA` |

Adapter Case 2 was one new Kimi request under R2. Its actual provider payload
failed application schema validation; it was neither repaired nor retried. The
successful raw R2 Case 2 is not substituted for this adapter-path failure.
Accordingly `REAL KIMI ADAPTER QUALIFICATION: 1/2`, and no real product
acceptance pipeline, 016D persistence run, Note V2, Weekly V2, or acceptance
artifact is authorized.
