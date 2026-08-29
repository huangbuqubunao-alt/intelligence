# TASK-016 Deep Analysis OpenAI Reference Provider Qualification

Status: `QUALIFIED` (offline implementation/contract evidence); live credential
qualification: `LIVE CREDENTIAL BLOCKED`.

OpenAI is the first reference provider for the provider-neutral Deep Analysis
runtime. It is neither the only provider nor a product-wide mandatory provider.

## Frozen profile

| Field | Qualified value |
|---|---|
| Provider kind / ID | `CLOUD_USER_KEY` / `openai` |
| Adapter | `openai-deep-analysis-responses` version `1` |
| SDK | existing locked `openai==2.46.0` |
| Endpoint | OpenAI Responses, `POST /v1/responses` |
| Model | `gpt-5.4-mini-2026-03-17` |
| Model identity class | `VERSIONED`; response model must exactly echo the selected snapshot |
| Capability profile | `openai-deep-analysis-reference-capabilities-v1` |
| Structured output | `PROVIDER_JSON_SCHEMA`; Responses `text.format` with `type=json_schema`, fixed name, `strict=true`, and the exact schema |
| Context authority | `CONSERVATIVE_PROVIDER_CONTRACT`, identity `openai-gpt-5.4-mini-conservative-context-v1` |
| Timeout / retry | 30 seconds / SDK `max_retries=0`; one semantic dispatch is one provider attempt |
| Credential policy | Ephemeral argument supplied only to an isolated child process; no credential reference, account, organization, or key bytes enter A2, A3, logs, exceptions, or persisted objects |
| Payload policy | `SELECTED_EVIDENCE_ONLY`; full transcript fields are rejected by both runtime authorization and adapter profile admission |

OpenAI documents `gpt-5.4-mini-2026-03-17` as a snapshot for the GPT-5.4 Mini
model, with the Responses endpoint, Structured Outputs, a 400,000-token context
window, and 128,000 maximum output tokens. The profile intentionally uses only
4,096 output tokens and reserves 16,384 tokens for provider-hidden
structured-schema overhead; its input-budget admission ceiling is 379,520.
This is conservative provider-contract admission, not a claim of local exact
tokenizer parity. [GPT-5.4 Mini model documentation](https://developers.openai.com/api/docs/models/gpt-5.4-mini)

The request sets every behavior-affecting field used by this profile: model,
ordered developer/user input, explicit language instruction, `text.format`,
`store=false`, `truncation=disabled`, `stream=false`,
`parallel_tool_calls=false`, `service_tier=default`,
`max_output_tokens=4096`, and `reasoning.effort=low`. OpenAI documents those
Responses request fields and the `text.format` JSON Schema configuration. [Responses create reference](https://developers.openai.com/api/reference/cli/resources/responses/methods/create)

## A2 and A3 binding

The adapter builder serializes the approved `AuthorizedProviderPayloadProjection`
into the sole user message and places output-language and scope constraints in
the developer/user messages. The exact ordered messages, endpoint/path, model,
generation semantics, strict-schema definition/name, and payload projection are
inside `DeepAnalysisRequestProjectionV1` (A2).

`DeepAnalysisExecutionProfileV1` (A3) binds provider kind/ID, adapter/version,
locked SDK version, Responses endpoint profile, versioned model/revision,
capability profile, conservative context profile, generation/no-retry profile,
non-secret credential execution profile identity, and strict-output profile.
The credential profile contains only the existing opaque identity; it is not
derived from raw API-key bytes.

The model echo is carried as untrusted response metadata. An unexpected response
model is intentionally returned only as `UntrustedDeepAnalysisResponseV1`; the
provider-neutral finalizer then rejects the early provenance binding.

## Response, errors, and cache semantics

The adapter extracts only the SDK's documented Responses `output_text` field.
It never scans for first JSON, strips fences, repairs malformed output, or uses
an alternative `output` item. The application finalizer performs strict JSON,
schema, domain, grounding, KG2, language, and provenance validation before its
sole trusted-success mint.

The untrusted envelope captures response model/status/output text, request ID,
and usage. Request ID and usage remain separate observational fields and are
excluded from semantic envelope/cache identity. Usage never grants
pre-dispatch authority. A versioned model is cache-eligible under the approved
contract, but no persistence/cache implementation has been added; that remains
TASK-016D scope.

Provider error mapping is deterministic and has no retry or fallback path:

| Signal | Provider-neutral outcome |
|---|---|
| no ephemeral credential | `AUTH_REQUIRED` / `PRE_DISPATCH` |
| HTTP 401/403 | `AUTH_INVALID` / `PROVIDER_ACCOUNT` |
| HTTP 429 with `insufficient_quota` | `QUOTA_EXCEEDED` / `PROVIDER_ACCOUNT` |
| other HTTP 429 | `RATE_LIMITED` / `PROVIDER_ACCOUNT` |
| HTTP 404 or model-not-found signal | `MODEL_UNAVAILABLE` / `PROVIDER_MODEL` |
| HTTP 5xx | `PROVIDER_UNAVAILABLE` / `PROVIDER_MODEL` |
| SDK connection/timeout | `NETWORK_FAILURE` or `TIMEOUT` / `TRANSPORT` |
| malformed/unfinished response envelope | `PROVIDER_ENVELOPE_INVALID` / `RESPONSE_ENVELOPE` |
| unclassified provider condition | `UNKNOWN` / `UNKNOWN` |

## Qualification evidence

- Fake transport request/profile/timeout/retry/usage/error tests: `14 passed`.
- Adapter to existing finalizer happy path: PASS; it mints only through the
  runtime-owned finalizer.
- Schema-valid fabricated evidence ID: finalizer returns `GROUNDING_INVALID`.
- Model echo mismatch: finalizer returns `PROVENANCE_INVALID`.
- Fenced `output_text` with an alternative valid output item: finalizer returns
  `STRUCTURED_OUTPUT_INVALID`; no repair or heuristic extraction occurs.
- Full-transcript sentinel and fake API-key sentinel are absent from the request
  body, response/provenance, exception, and adapter representation tests.
- Request ID/usage mutation leaves semantic provider-envelope identity unchanged.
- `uv run pytest tests/unit/test_openai_deep_analysis_adapter.py tests/unit/test_deep_analysis_contracts.py tests/unit/test_deep_analysis_runtime.py -q`: `72 passed`.
- `uv run mypy src`: PASS. `uv run pytest -q`: `1854 passed, 1 warning`.
- `uv run ruff check .`: PASS. `uv run mypy .`: historical baseline retained,
  `1019 errors in 44 files`.

No `OPENAI_API_KEY` was available in the approved temporary runtime mechanism.
Consequently LIVE-1 and LIVE-2 were not attempted, no credential was requested,
written, printed, or persisted, and the live result is `LIVE CREDENTIAL BLOCKED`.
The lack of a credential does not block the offline adapter qualification because
the mandatory provider mechanics are covered by current official API evidence
and fake-transport boundary tests.
