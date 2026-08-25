# TASK-016C Phase H2 — REPAIR Trusted-Flow Authorization Proposal

## Status and decision requested

`READY FOR PHASE H2 AUTHORIZATION INDEPENDENT REVIEW`.

This proposal assumes Phase G is accepted and H1-A/H1-B are closed. It
authorizes neither code, tests, merge, network calls, cache recovery, nor a
public repair surface. Its purpose is to define the narrow future H2
implementation boundary by which one eligible, received PRIMARY failure may be
repaired without weakening the accepted trusted-persistence chain.

This Round 3 amendment is documentation-only. It does not authorize or modify
`src/`, `tests/`, schema/migrations, dependencies, or `uv.lock`.

## 1. Frozen contracts

The only persistence entry remains `TrustedPersistenceEntry.persist_success()`.
It accepts exactly one of the two sealed, memory-only success aggregates:

```text
PhaseFTrustedScoringSuccess
  -- PRIMARY --> TrustedPersistenceEntry.persist_success()
PhaseHTrustedRepairSuccess
  -- REPAIR  --> TrustedPersistenceEntry.persist_success()
  -> PREWRITE_VALIDATE
  -> filesystem protocol
  -> SQLite atomic registration
```

H2 must preserve all of the following.

- `TrustedPersistenceEntry.persist_success()` remains the only persistence
  ingress, only filesystem promoter, and only owner of SQLite registration.
- Its H2 contract is an exact-type discriminated union:
  `type(success) is PhaseFTrustedScoringSuccess` or
  `type(success) is PhaseHTrustedRepairSuccess`. Every other value, including
  a subclass, mapping, JSON restore, bare `ScoreResult`, bare
  `TrustedScoreResult`, raw bytes, Artifact, ProviderCall, cache payload, or
  legacy value is rejected before any field is read.
- There is no `persist_repair()`, alternate writer, repository repair API,
  repair table, pre-write ProviderCall reservation, manual Artifact creation,
  scatter-field persistence, or alternate SQLite transaction.
- `PREWRITE_VALIDATE` stays pure and zero-write. No file, Artifact,
  ProviderCall, cache record, response artifact ID, score, stage, or SQLite
  state may be written before it passes.
- H1 stays closed: no receipt capability, repair token, repair registry, repair
  continuation exposed to callers, caller repair admission, or repair from
  `UNKNOWN_PROVIDER_STATE`.
- The PRIMARY-only Phase G path and its exact `PhaseFTrustedScoringSuccess`
  validation semantics remain unchanged. Its shared writer, filesystem
  protocol, SQLite registration, and complete-graph idempotency semantics are
  also the REPAIR semantics; H2 adds no second persistence boundary.

## 2. Runtime-only REPAIR orchestration

REPAIR is an internal branch of the active `RuntimeOperations` SCORING
execution. It has no public API and does not accept a caller-provided failure,
identity, result, attestation, raw response, or persistence plan.

```text
PRIMARY provider attempt
  -> received local failure classified by the runtime as eligible
  -> runtime internal REPAIR branch consumes its one-shot admission
  -> exactly one REPAIR provider attempt
  -> candidate -> schema -> language -> quality judge -> attestation -> finalizer
  -> sealed PhaseHTrustedRepairSuccess
  -> existing persist_success() bridge
  -> unchanged PREWRITE_VALIDATE -> filesystem -> SQLite atomic registration
```

The runtime may enter this branch only when all conditions hold in the same
live call stack:

1. The PRIMARY call was actually dispatched by the current runtime under its
   active, exclusively owned SCORING lease.
2. Its response was received and a runtime-local classifier produced one of
   the closed eligible failures: `SCHEMA_OR_PARSE_INVALID`,
   `LANGUAGE_INVALID`, `JUDGE_REJECT`, or `JUDGE_UNCERTAIN`.
3. The existing H1 runtime-local admission state shows that PRIMARY was
   consumed, REPAIR has not been consumed, and no current ProviderCall exists
   for either derived REPAIR identity.
4. The runtime still owns the same unexpired SCORING lease immediately before
   each provider and Judge dispatch.

Provider creation failure before contact may fail normally but does not create
repair eligibility. A transport exception, timeout, process loss, lease loss,
authority/context mismatch, malformed H1 state, or any uncertain provider
outcome is `UNKNOWN_PROVIDER_STATE` or a fail-closed error. Neither can enter
REPAIR.

The one-shot decision is performed by a private method on the existing
runtime/admission composition, under the existing execution-state lock. It
uses the existing `REPAIR` and `REPAIR_JUDGE` role slots; it introduces no
separate repair registry and returns no receipt or capability. The private
method is callable only from the runtime's PRIMARY-failure branch and performs
no persistence.

## 3. REPAIR identity, budget, and restart rule

### Canonical identities

The successful score remains a score for the original PRIMARY request.
`build_scoring_request_identity()` therefore remains the canonical scoring
identity, and the finalized `ScoreResult.request_hash`, score summary, and
logical scoring artifact namespace remain bound to the PRIMARY request hash.

REPAIR has a separate transport/ProviderCall identity. Its normalized-input
hash is the SHA-256 of canonical JSON over exactly:

```text
operation = "local-scoring-repair-v1"
primary_scoring_request_hash
primary_normalized_input_hash
primary_raw_response_hash
primary_failure_evidence_hash
primary_failure_class
repair_prompt_version
repair_schema_version
scoring_provider
scoring_model
scoring_model_digest
temperature
max_output_tokens
max_description_chars
output_language
```

Its request hash must be produced only through the existing
`build_provider_request_hash()` with:

```text
operation = "local-scoring-repair-v1"
normalized_input_hash = repair_normalized_input_hash
provider = current scoring provider
model = current scoring model
prompt_version = repair_prompt_version
schema_version = repair_schema_version
```

The REPAIR Judge retains the existing two-layer identity. Its
`QualityJudgeOperationInput.attempt_role` is `REPAIR`, so its H1 and H2 are
role-distinct from PRIMARY Judge H1/H2. The runtime derives every value from
the current trusted context, current quality authority, original scoring input,
and the in-memory received PRIMARY failure; it never reads identity material
from a caller object or persisted record.

Before dispatch and again before persistence, H2 must reject if any REPAIR
request hash equals the PRIMARY scoring request hash, PRIMARY Judge H2, or
REPAIR Judge H2. This is a defense-in-depth collision guard; the distinct
operation and canonical input are the primary collision prevention.

### Canonical H2 evidence serialization

Every H2 evidence object uses the project canonical JSON rule already used by
trusted scoring and Judge identities: strict UTF-8 encoding; lexicographically
sorted object keys; compact separators `,` and `:`; `ensure_ascii=false`; JSON
integers/booleans/null only in their exact JSON representation; and no
NaN/Infinity. Duplicate semantic fields are forbidden because each typed schema
has one field name for each meaning and rejects unknown fields. Pretty-printing,
whitespace normalization, implementation-specific float formatting, alternate
key order, and duplicate JSON keys are forbidden.
The H2 wire decoder must reject a duplicate object key before typed validation;
it must not apply a last-key-wins conversion.

For every versioned H2 object, validation is exactly:

```text
exact typed schema with unknown fields rejected
  -> canonical JSON bytes (strict UTF-8)
  -> SHA-256 lowercase hexadecimal
```

Revalidation parses the sealed bytes into the exact typed schema, rejects
unknown fields and invalid enum values, canonically reserializes it, and
requires byte-for-byte equality with the sealed bytes before using its hash.
No `null`/missing-field equivalence, free-form diagnostic text, or lossy
object-to-dictionary conversion is permitted.

### `PrimaryFailureEvidence` exact wire schema

`PrimaryFailureEvidence` is the complete typed wire contract below. Its object
has exactly these fields and no others; every field is required. Its schema
literal is `"task016c-primary-failure-evidence-v1"` and its canonical SHA-256
is `primary_failure_evidence_hash` in the REPAIR identity and composite
envelope.

| Field | Exact JSON type and rule |
|---|---|
| `schema_version` | string, exactly `"task016c-primary-failure-evidence-v1"` |
| `primary_attempt_identity` | non-empty string, exactly `"local-scoring"` |
| `primary_request_hash` | lowercase 64-character SHA-256 hexadecimal string |
| `primary_normalized_input_hash` | lowercase 64-character SHA-256 hexadecimal string |
| `primary_provider` | non-empty string, exactly the current scoring provider |
| `primary_model` | non-empty string, exactly the current scoring model |
| `primary_model_digest` | string matching `sha256:` plus 64 lowercase hexadecimal characters |
| `primary_prompt_version` | non-empty string, exactly the current scoring prompt version |
| `primary_schema_version` | non-empty string, exactly the current scoring schema version |
| `primary_output_language` | string enum `"zh-CN"` or `"en"` |
| `primary_temperature` | finite JSON number, exactly the current scoring temperature |
| `primary_max_output_tokens` | positive JSON integer, exactly the current limit |
| `primary_max_description_chars` | positive JSON integer, exactly the current limit |
| `primary_scoring_input` | object conforming exactly to existing validated `ScoringInput`; it is canonical JSON nested as an object, with its own model validation and unknown-field rejection |
| `primary_scoring_input_sha256` | lowercase 64-character SHA-256 of canonical `primary_scoring_input` bytes |
| `primary_raw_utf8` | string containing the exact bounded PRIMARY provider HTTP body after successful strict UTF-8 decode; no trim, normalization, or reserialization |
| `primary_raw_utf8_length` | JSON integer `0..1000000`, exactly `len(primary_raw_utf8.encode("utf-8"))` |
| `primary_raw_sha256` | lowercase 64-character SHA-256 of the exact PRIMARY UTF-8 bytes |
| `failure_class` | closed eligible enum defined below |
| `primary_candidate` | either exact `CandidateEvidence` or exact `NotApplicableEvidence`, never `null` or omitted |
| `parser_evidence` | either exact `ParserFailureEvidence` or exact `NotApplicableEvidence`, never `null` or omitted |
| `language_evidence` | either exact `LanguageValidationEvidence` or exact `NotApplicableEvidence`, never `null` or omitted |
| `judge_evidence` | either exact `JudgeEvidence` with role `PRIMARY` or exact `NotApplicableEvidence`, never `null` or omitted |

`NotApplicableEvidence` is exactly `{"kind":"NOT_APPLICABLE"}`: one string
field, no others. `CandidateEvidence` is exactly:

```text
{
  "schema_version": "task016c-candidate-evidence-v1",
  "kind": "CANDIDATE",
  "candidate": <exact validated ScoringCandidate object>,
  "candidate_sha256": <lowercase 64-char SHA-256 of canonical candidate bytes>
}
```

Its `candidate` object must revalidate as the existing exact
`ScoringCandidate` schema and its hash must equal canonical reserialization.

The only permitted `failure_class` literals are
`SCHEMA_OR_PARSE_INVALID`, `LANGUAGE_INVALID`, `JUDGE_REJECT`, and
`JUDGE_UNCERTAIN`. `DETERMINISTIC_QUALITY_REJECT`,
`UNKNOWN_PROVIDER_STATE`, arbitrary strings, and future values are not H2
REPAIR-eligible. An unknown class or an incorrect applicable/non-applicable
combination fails closed:

| `failure_class` | `primary_candidate` | `parser_evidence` | `language_evidence` | `judge_evidence` |
|---|---|---|---|---|
| `SCHEMA_OR_PARSE_INVALID` | `NOT_APPLICABLE` | `PARSER_FAILURE` | `NOT_APPLICABLE` | `NOT_APPLICABLE` |
| `LANGUAGE_INVALID` | `CANDIDATE` | `NOT_APPLICABLE` | `LANGUAGE_VALIDATION` | `NOT_APPLICABLE` |
| `JUDGE_REJECT` | `CANDIDATE` | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `JUDGE_EVIDENCE(role=PRIMARY,result=REJECT)` |
| `JUDGE_UNCERTAIN` | `CANDIDATE` | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `JUDGE_EVIDENCE(role=PRIMARY,result=UNCERTAIN)` |

### Parser and language evidence

`ParserFailureEvidence` has exactly four fields:
`schema_version` (exactly `"task016c-parser-failure-evidence-v1"`), `kind`
(exactly `"PARSER_FAILURE"`), `raw_sha256` (lowercase 64-character hash), and
`diagnostic_code` (the closed enum below). It contains no exception message,
traceback, field value, or arbitrary text.

The diagnostic mapper is a minimal pure wrapper over the current shared
`parse_scoring_candidate()` behavior. It must use these exact codes and no
others:

| Current parser path | `diagnostic_code` |
|---|---|
| exact raw string cannot strict-UTF-8 encode | `RAW_UTF8_INVALID` |
| exact raw UTF-8 bytes exceed 1,000,000 | `RAW_BYTES_LIMIT_EXCEEDED` |
| outer provider body `json.loads` fails | `OUTER_JSON_INVALID` |
| outer parsed value is not a JSON object | `OUTER_TOP_LEVEL_TYPE_INVALID` |
| outer object has no `response` key | `MODEL_RESPONSE_MISSING` |
| outer `response` is not a string | `MODEL_RESPONSE_TYPE_INVALID` |
| model `response` exceeds 20,000 characters | `MODEL_RESPONSE_LENGTH_EXCEEDED` |
| model response `json.loads` fails | `MODEL_JSON_INVALID` |
| model JSON is not an object | `MODEL_TOP_LEVEL_TYPE_INVALID` |
| model object contains a key outside the current scoring field set | `MODEL_FIELD_SET_INVALID` |
| exact `ScoringCandidate` schema validation fails | `CANDIDATE_SCHEMA_INVALID` |

For `SCHEMA_OR_PARSE_INVALID`, PREWRITE runs that same parser and mapper on
`primary_raw_utf8`, requires failure, and requires the exact sealed diagnostic
object, including `parser_evidence.raw_sha256 == primary_raw_sha256`. Parser
success or any different code rejects. Stored exception text cannot be
authority because it is neither sealed nor accepted.

`RAW_UTF8_INVALID` and `RAW_BYTES_LIMIT_EXCEEDED` are part of the complete
current-parser taxonomy, but cannot form an H2 repair-eligible sealed failure:
the former has no strict-UTF-8 string that can enter canonical evidence and the
latter exceeds the required bounded `primary_raw_utf8` field. They therefore
fail closed as unknown/ineligible before `PrimaryFailureEvidence` minting. The
remaining listed codes are eligible only when every applicable evidence field
and replay check above can be sealed and reproduced exactly.

`LanguageValidationEvidence` has exactly six fields:
`schema_version` (exactly `"task016c-language-validation-evidence-v1"`),
`kind` (exactly `"LANGUAGE_VALIDATION"`), `candidate_sha256` (lowercase
64-character hash), `output_language` (enum `"zh-CN"|"en"`),
`validator_contract` (exactly `"task016b-scoring-language-validator-v1"`),
and `result` (enum `"VALID"|"INVALID"|"UNCERTAIN"`). The frozen TASK-016B
validator emits no finer deterministic reason code; this exact `result` is its
only diagnostic authority. For `LANGUAGE_INVALID`, `result` must be `INVALID`.

PREWRITE reparses the primary raw, requires the sealed candidate/hash, calls
the existing `detect_scoring_language_violation(reason, output_language)`,
and builds the same typed evidence. It must byte-for-byte equal the seal. A
`VALID` or `UNCERTAIN` result, a candidate/hash mismatch, or a replacement
language algorithm rejects.

### Judge raw, outcome split, and `JudgeEvidence`

For H2, Judge raw evidence is **only** the exact extracted Ollama model-content
string from the successful generate response object's `response` field. It is
not the full HTTP body. Capture happens only after loopback transport completed,
the bounded HTTP body strictly UTF-8 decoded, the outer Ollama body parsed as a
JSON object, and that object contained a string `response` field no longer than
20,000 characters. The captured model-content string preserves every character,
including surrounding whitespace; it is never trimmed, normalized, or JSON
reserialized. Empty content is the empty string with UTF-8 byte length zero and
the SHA-256 of empty bytes; it deterministically becomes a semantic
`UNCERTAIN` only if the pure verifier below does so.

`UNKNOWN_PROVIDER_STATE` is not a Judge semantic result. Timeout after provider
contact, connection/read/process interruption, HTTP/provider protocol failure,
missing body/content, failed strict UTF-8/outer-JSON extraction, or any state
where exact model-content raw evidence cannot be sealed is H1
`UNKNOWN_PROVIDER_STATE` after dispatch (or a pre-contact fail-closed denial
before dispatch). None may be labeled `JUDGE_UNCERTAIN` or used for REPAIR.

`JudgeEvidence` is one exact schema for both roles. It has exactly these fields
and no others; every field is required:

| Field | Exact JSON type and rule |
|---|---|
| `evidence_schema_version` | string, exactly `"task016c-judge-evidence-v1"` |
| `role` | string enum `"PRIMARY"` or `"REPAIR"` |
| `judge_h1` | lowercase 64-character SHA-256 hex |
| `judge_h2` | lowercase 64-character SHA-256 hex |
| `provider` | non-empty string, exactly `"ollama"` |
| `model` | non-empty string, exactly the current Judge model |
| `model_digest` | string matching `sha256:` plus 64 lowercase hexadecimal characters |
| `policy_version` | non-empty string, exactly the current Judge policy version |
| `prompt_version` | non-empty string, exactly the current Judge prompt version |
| `operation_schema_version` | non-empty string, exactly the current Judge operation/result schema version; this name deliberately differs from `evidence_schema_version` |
| `operation` | string, exactly `"local-content-quality-v1"` |
| `operation_input` | object conforming exactly to existing `QualityJudgeOperationInput`, including the same `attempt_role` as `role` |
| `judge_input` | object conforming exactly to existing `ContentQualityInput` |
| `judge_input_sha256` | lowercase 64-character canonical hash of `judge_input` |
| `raw_capture_kind` | string, exactly `"EXTRACTED_OLLAMA_RESPONSE_TEXT_V1"` |
| `raw_utf8` | exact extracted model-content string; empty string is allowed and never omitted |
| `raw_utf8_length` | JSON integer `0..20000`, exactly `len(raw_utf8.encode("utf-8"))` |
| `raw_sha256` | lowercase 64-character SHA-256 of exact `raw_utf8` bytes |
| `derived_result` | object conforming exactly to existing `ContentQualityResult` with `decision_source=LOCAL_JUDGE` |

The pure internal verifier to be introduced by a future H2 implementation has
this conceptual contract:

```text
verify_judge_model_content(
  raw_utf8: str,
  operation_input: exact QualityJudgeOperationInput,
  content_input: exact ContentQualityInput
) -> exact ContentQualityResult(status in PASS|REJECT|UNCERTAIN)
```

It is deterministic and performs no provider call, filesystem write, SQLite
write, cache action, or mutable-runtime-authority lookup. It uses the existing
`_parse_judge_response()` JSON/schema/evidence-registry rules and existing
`_build_result_from_response()` promotion rules, factored without changing
their semantics. A captured model-content string that cannot parse/validate
under those rules produces the existing local-Judge `UNCERTAIN` result with
`JUDGE_INVALID_RESPONSE`; raw content was obtained, so this is semantic and may
be represented. Transport/no-content outcomes are outside the verifier and are
always `UNKNOWN_PROVIDER_STATE`/ineligible.

During PREWRITE, `JudgeEvidence` is parsed as its exact schema, canonicalized
back to identical bytes, and verified as follows: rebuild Judge H1 from the
exact `operation_input`; rebuild H2 through `build_provider_request_hash()`;
require provider/model/digest/prompt/operation-schema/operation/input bindings
to equal current frozen provenance; recompute the canonical `judge_input`
hash; require `operation_input.quality_input_hash == judge_input_sha256` and
the existing frozen quality cross-bindings (matching scoring request hash,
candidate hash, output language, candidate reason/topics, and evidence
registry); recompute raw length/hash; call the pure verifier; and require its
exact canonical `ContentQualityResult` to equal `derived_result`.
`JUDGE_REJECT` requires `role=PRIMARY`,
`operation_input.scoring_request_hash == primary_request_hash`,
`operation_input.candidate_hash == primary_candidate.candidate_sha256`, and
result status `REJECT`; `JUDGE_UNCERTAIN` requires the same PRIMARY bindings
and result status `UNCERTAIN`. A stored enum alone is never authority.

The same `JudgeEvidence` schema and replay steps apply to REPAIR, but the role
is exactly `REPAIR`, `operation_input.attempt_role=REPAIR`, and the derived
result must be `PASS` before attestation/finalization. PRIMARY Judge evidence
cannot substitute for REPAIR Judge evidence, nor vice versa, even when raw
content/model/result match: role changes the operation input, H1, H2, and
canonical evidence bytes.

### Provider/model binding and one-shot budget

REPAIR must use the current runtime-owned scoring provider, model, model digest,
output language, temperature, maximum output tokens, and maximum description
length. It may use only the approved repair prompt/schema versions. Any
configuration or authority rotation after PRIMARY prevents REPAIR persistence;
it does not permit recomputation under substituted settings.

For one active job execution, the maximum external work is:

| Role | Maximum |
|---|---:|
| PRIMARY scoring | 1 |
| REPAIR scoring | 1 |
| PRIMARY Judge | 1 |
| REPAIR Judge | 1 |

The existing in-memory role state is consumed before contact and is not
reversible after a provider attempt. Replaying a PRIMARY failure cannot consume
another REPAIR slot. A second repair call, including a second Judge call, is
denied before provider creation/contact.

### Restart behavior

Admission state, received failure classification, and REPAIR working evidence
are process-memory-only. They are never serialized or restored. After crash,
timeout, lost response, lease expiry, or restart, the job is finalized through
the H1 closed `UNKNOWN_PROVIDER_STATE` path before generic reclaim/retry.
There is no PRIMARY retry, REPAIR retry, replayed failure admission, cache-miss
interpretation, or persisted-state takeover. An exact already-complete G graph
may be returned by existing idempotency verification only; it never dispatches
PRIMARY, REPAIR, or a Judge.

## 4. REPAIR validation and trust transition

The mandatory order is exact:

```text
REPAIR candidate (untrusted)
  -> schema validation
  -> frozen TASK-016B language validation
  -> deterministic quality gate, then REPAIR quality judge
  -> QualityPassAttestation
  -> TrustedScoringFinalizer
```

The REPAIR provider returns only a bounded, strict-UTF-8 raw response and the
candidate reconstructed by the same canonical parser used by PRIMARY and
Phase G. Both the raw response and candidate remain untrusted. Schema
validation reconstructs an exact `ScoringCandidate`; it does not make it
trusted. Language validation remains unchanged. The deterministic gate may
reject before Judge dispatch; a non-rejected candidate proceeds to one REPAIR
Judge call with `attempt_role=REPAIR`.

Only a full `PASS` produces an attestation, built and re-verified with the
current runtime-owned quality authority. `REJECT`, `UNCERTAIN`, malformed Judge
output, or any binding mismatch produces no attestation and no persistence.
The existing `TrustedScoringFinalizer` then revalidates the candidate, scoring
input, REPAIR quality input/result, REPAIR Judge operation, attestation,
authority, and trusted scoring context. Its output is the sole trusted business
value: an exact `TrustedScoreResult`.

Nothing before Finalizer is trusted: raw response, parser output, candidate,
failure classification as an external value, Judge response, and reconstructed
quality DTOs are all untrusted evidence. The attestation is verified evidence,
not an authority to write. After Finalizer, only the finalizer-produced
`TrustedScoreResult` is trusted business data; the raw response and repair
evidence remain evidence that must be revalidated by persistence.

## 5. Persistence bridge: one entry, one plan, one transaction

### 5.1 Sealed second success type

Yes. `TrustedPersistenceEntry.persist_success()` accepts the second sealed
success type `PhaseHTrustedRepairSuccess`; it does not gain a second method or
alternate repository interface. This is the sole H2 exception to the general
ban on new capability objects. No receipt, repair token, registry entry,
admission handle, caller continuation, or further capability type is allowed.

`PhaseHTrustedRepairSuccess` is a private, memory-only aggregate with these
mandatory properties:

- The constructor is private to the runtime-owned minting closure. It has no
  caller constructor, `from_*` factory, mapping/JSON factory, or restore path.
- It is exact type, non-subclassable, immutable after minting, non-copyable,
  non-deepcopyable, and non-serializable/non-pickleable. Its fields are not a
  public repair API.
- It is minted only by the current `RuntimeOperations` composition after the
  same runtime has received an eligible PRIMARY failure, consumed its private
  REPAIR admission, completed the complete REPAIR validation pipeline, and
  received the exact `TrustedScoreResult` from `TrustedScoringFinalizer`.
- Minting independently re-derives every binding below. A type marker,
  sentinel, or stored flag is defense in depth only; `persist_success()` must
  re-derive and verify the provenance before any plan exists.
- Its lifetime ends at immediate handoff to the runtime-owned persistence
  entry. It is not retained for retry, crash recovery, cache lookup, or caller
  use.

### 5.2 Sealed repair envelope and provenance binding

The aggregate seals one composite repair envelope; it is not assembled from
caller arguments at persistence time. The envelope is canonical JSON with the
exact literal `envelope_schema = "trusted-scoring-repair-envelope-v1"`. Its
canonical bytes, SHA-256, and length are the final `SCORING_RAW` artifact
content, hash, and length for a successful REPAIR. It is neither the invalid
PRIMARY raw response alone nor the REPAIR raw response alone.

The aggregate and composite envelope contain only runtime-derived, immutable
values needed for repeat validation:

| Binding | Required sealed value |
|---|---|
| PRIMARY identity | Canonical original `ScoringInput` bytes/hash, original `primary_scoring_request_hash`, and `primary_normalized_input_hash`, each rebuilt with `build_scoring_request_identity()`. |
| PRIMARY failure | Complete canonical `PrimaryFailureEvidence`, including the exact PRIMARY raw response, raw hash, class, `primary_failure_evidence_hash`, candidate/hash when present, class-specific evidence, and PRIMARY scoring/quality provenance. |
| REPAIR raw/candidate | Exact bounded strict-UTF-8 repair raw response, `repair_raw_response_hash`, canonical parser-derived candidate, and canonical candidate hash. |
| REPAIR provider identity | Current runtime scoring provider, model, model digest, output language, temperature, output limit, description limit, repair prompt version, and repair schema version. |
| REPAIR attempt identity | Canonical REPAIR normalized-input hash and the `build_provider_request_hash()` request hash for `local-scoring-repair-v1`; it is distinct from PRIMARY and both Judge identities. |
| Quality/Judge evidence | Canonical quality input, complete REPAIR `PASS` result, `QualityJudgeOperationInput(attempt_role=REPAIR)`, Judge H1/H2, and current-authority `QualityPassAttestation`. |
| Finalized structured value | Exact `TrustedScoreResult` from the Finalizer plus sealed canonical structured-result bytes/hash/length. |

The exact typed `RepairCompositeEnvelope` has exactly these six required
top-level fields and no others:

| Field | Exact JSON type and rule |
|---|---|
| `envelope_schema` | string, exactly `"trusted-scoring-repair-envelope-v1"` |
| `primary_failure_evidence` | exact `PrimaryFailureEvidence` described in Section 3 |
| `repair_provider_evidence` | exact `RepairProviderEvidence` below |
| `repair_candidate_evidence` | exact `RepairCandidateValidationEvidence` below |
| `repair_quality_evidence` | exact `RepairQualityEvidence` below |
| `finalizer_binding` | exact `FinalizerBinding` below |

`RepairProviderEvidence` has exactly 13 required fields:
`schema_version`=`"task016c-repair-provider-evidence-v1"`,
`operation`=`"local-scoring-repair-v1"`, `normalized_input_hash` and
`request_hash` (each lowercase 64-character hash), `provider` and `model`
(non-empty strings), `model_digest` (`sha256:` plus 64 lowercase hex),
`prompt_version` and `operation_schema_version` (non-empty strings),
`output_language` (`"zh-CN"|"en"`), `temperature` (finite JSON number),
`max_output_tokens` and `max_description_chars` (positive JSON integers), and
`raw_utf8`/`raw_utf8_length`/`raw_sha256` would be ambiguous duplicates and are
therefore prohibited here: they exist only in `repair_candidate_evidence`.

`RepairCandidateValidationEvidence` has exactly eight required fields:
`schema_version`=`"task016c-repair-candidate-evidence-v1"`,
`parser_contract`=`"scoring-candidate-parser-v1"`,
`raw_utf8` (exact bounded strict-UTF-8 REPAIR provider HTTP body),
`raw_utf8_length` (integer `0..1000000` equal to its UTF-8 byte length),
`raw_sha256` (lowercase 64-character hash), `candidate` (exact existing
`ScoringCandidate` object), `candidate_sha256` (canonical candidate hash), and
`validation_status`=`"VALID"`. No repair failure or `NOT_APPLICABLE` form is
allowed in a successful repair envelope.

`RepairQualityEvidence` has exactly seven required fields:
`schema_version`=`"task016c-repair-quality-evidence-v1"`, `quality_input`
(exact existing `ContentQualityInput` object), `quality_input_sha256`
(canonical hash), `judge_evidence` (exact `JudgeEvidence` with
`role="REPAIR"` and `derived_result.status="PASS"`), `quality_result` (the
same exact `ContentQualityResult(PASS)` as `judge_evidence.derived_result`),
`quality_result_sha256` (canonical hash), and `attestation` (exact existing
`QualityPassAttestation` object). All cross-bindings must be exact; no field is
nullable, optional, or replaceable with `NotApplicableEvidence`. In
particular, PREWRITE applies the frozen quality cross-binding verifier with
`judge_evidence.operation_input.scoring_request_hash ==
repair_provider_evidence.request_hash`, candidate hashes equal to
`repair_candidate_evidence.candidate_sha256`, and quality-input hash equal to
the canonical `quality_input`; it then verifies the matching PASS result hash
and attestation. No PRIMARY scoring request/candidate/Judge identity may occupy
any of those REPAIR bindings.

`FinalizerBinding` has exactly six required fields:
`schema_version`=`"task016c-finalizer-binding-v1"`, `trusted_score_result`
(the existing finalizer-produced business object serialized only inside this
sealed binding, never accepted or exposed as a bare `ScoreResult`),
`trusted_score_result_sha256` (canonical hash), `structured_utf8` (sealed
structured-result canonical JSON string), `structured_utf8_length` (integer
equal to its strict UTF-8 byte length), and `structured_utf8_sha256`
(lowercase 64-character hash). `structured_utf8` must be the sealed serializer
output for the exact finalizer result; it is never caller-provided.

Every nested object above follows Section 3 canonical serialization and exact
typed reserialize-equality. Their names, schema literals, required fields,
absence semantics, and unknown-field behavior are therefore frozen rather than
left to an implementer.

The exact PRIMARY raw response and all classification-specific evidence live
inside `primary_failure_evidence`; this is what lets PREWRITE independently
prove that the repair was eligible. REPAIR transport identity never replaces
the original PRIMARY scoring identity of the score/result or logical scoring
artifact namespace. The envelope is one sealed plan input, rather than new
scatter fields or a database schema change.

### 5.3 Shared persistence invariants

`persist_success()` first checks the exact success type before reading any
property. It then selects the corresponding in-memory verifier:

```text
exact PhaseFTrustedScoringSuccess
  -> PRIMARY prewrite verifier
  -> ValidatedScoringWritePlan

exact PhaseHTrustedRepairSuccess
  -> REPAIR prewrite verifier
  -> ValidatedScoringWritePlan

either plan
  -> unchanged verified filesystem protocol
  -> unchanged single SQLite atomic registration
```

After H2, the only allowed exact inputs are
`PhaseFTrustedScoringSuccess` and `PhaseHTrustedRepairSuccess`; there is no
third success type, compatibility adapter, or caller-selected verifier.

Both success types must execute the same `PREWRITE_VALIDATE` phase, the same
temporary-write/fsync/hash/no-clobber-promote/directory-fsync/final-reopen
protocol, and the same single SQLite registration transaction. Neither branch
may reserve or complete a ProviderCall, create an Artifact, set a response
artifact ID, write a score/stage/job, or touch the filesystem before its
prewrite verifier produces the common opaque `ValidatedScoringWritePlan`.

The H2 REPAIR verifier must prove, in memory, all of the following before it
may mint that existing plan:

1. The complete `PrimaryFailureEvidence` re-proves the eligible failure under
   the exact class-specific procedure in Section 3; its raw, canonical input,
   identity, candidate, quality/Judge evidence, provenance, and
   `primary_failure_evidence_hash` bind the REPAIR identity.
2. REPAIR raw response re-parses through the same canonical parser; its raw
   and candidate hashes bind the finalizer-produced trusted result.
3. Original scoring identity and current provider/model/digest/context bind
   the result; REPAIR transport identity is never substituted for the scoring
   result identity.
4. REPAIR quality input, full `PASS`, REPAIR Judge H1/H2, and attestation
   re-verify against the current authority and `attempt_role=REPAIR`.
5. Canonical raw-envelope and sealed structured-result bytes, hashes, lengths,
   Artifact metadata, and the two ProviderCall requests/completions are rebuilt
   as one existing write plan.

### 5.4 REPAIR-to-write-plan mapping

The REPAIR verifier constructs the same private `_ValidatedScoringWritePlan`
shape used by Phase G. The following mapping is frozen.

| Plan field | REPAIR-derived value |
|---|---|
| `video_id`, `job_id`, pipeline scope, score summary | The original runtime-owned scoring job/video/context; the summary is the finalizer-produced score evaluated against the current runtime threshold. |
| Result namespace | Original PRIMARY scoring request hash. The final result remains the one score for that original job/video; no second logical score-result namespace exists. |
| `SCORING_RAW` key/path | Exactly the Phase G PRIMARY namespace: key `scoring/<primary_scoring_request_hash>/raw`, relative path `scoring/<primary_scoring_request_hash>/raw.json`. Its bytes/hash/length are the composite envelope defined in Section 5.2. |
| `SCORING_STRUCTURED` key/path | Exactly the Phase G PRIMARY namespace: key `scoring/<primary_scoring_request_hash>/structured`, relative path `scoring/<primary_scoring_request_hash>/structured.json`. Its bytes/hash/length are the sealed Finalizer structured result. |
| Raw Artifact metadata | `SCORING_RAW`, original video/job, `DATA`, the exact raw key/path above, composite-envelope hash, REPAIR provider/model, `producer_version="scoring-raw-content-quality-repair-v1"`, raw-response 30-day retention, and the existing 30-day expiry calculation. |
| Structured Artifact metadata | `SCORING_STRUCTURED`, original video/job, `DATA`, the exact structured key/path above, sealed structured hash, REPAIR provider/model, `producer_version="scoring-structured-content-quality-repair-v1"`, long-lived retention, and no expiry. |
| Artifact IDs | `scoring-raw-` + SHA-256 of `raw_key + raw_envelope_hash`; `scoring-structured-` + SHA-256 of `structured_key + structured_hash`. |
| Scoring ProviderCall request/completion | Request fields are only the sealed REPAIR identity: `operation="local-scoring-repair-v1"`, REPAIR normalized-input hash, REPAIR provider/model, repair prompt/schema versions, and deterministic artifact key=`raw_key`. Its request hash is recomputed with `build_provider_request_hash()`. Completion is `SUCCEEDED` in the existing transaction and binds `response_artifact_id` to the raw Artifact ID. No PRIMARY scoring ProviderCall is created for the failed PRIMARY attempt. |
| Judge ProviderCall request/completion | Request fields are the sealed REPAIR Judge identity: operation=`local-content-quality-v1`, normalized input=REPAIR Judge H1, request hash=REPAIR Judge H2, and provider/model/prompt/schema from the current quality authority; deterministic artifact key=`raw_key`. Completion is `SUCCEEDED` in the existing transaction and binds the same raw Artifact ID. It differs from PRIMARY Judge only because the sealed operation has `attempt_role=REPAIR`, producing distinct H1/H2. |

The existing PRIMARY branch is semantically unchanged: it continues to derive
its scoring ProviderCall from `operation="local-scoring"` and the existing
PRIMARY request identity. This amendment narrowly authorizes the H2-private
REPAIR verifier to derive its scoring ProviderCall from the sealed
`local-scoring-repair-v1` identity instead. No caller supplies either branch's
ProviderCall fields.

After either branch mints `_ValidatedScoringWritePlan`, the filesystem and
SQLite code is identical and type-agnostic. There is no role-specific
filesystem writer, no role-specific SQLite transaction, `persist_repair()`,
repository repair API, or change to PREWRITE ordering/no-clobber promotion/
single registration transaction.

### 5.5 Complete-graph idempotency equality

For REPAIR, `persist_success()` may return an existing committed graph only
when the entire graph equals the newly derived REPAIR plan. Equality includes:

- exact composite raw-envelope bytes, hash, length, and
  `trusted-scoring-repair-envelope-v1` schema literal;
- sealed structured bytes, hash, and length;
- both Artifact IDs, keys, kinds, paths, content hashes, storage root, video,
  job, provider/model, producer version, retention, and expiry metadata;
- scoring ProviderCall request hash, operation, normalized hash, provider,
  model, prompt/schema, `SUCCEEDED` status, and raw response-artifact binding;
- REPAIR Judge ProviderCall H1/H2, operation, provider/model/prompt/schema,
  `SUCCEEDED` status, and raw response-artifact binding;
- final video score/`should_summarize`, pipeline state, and job identity/type,
  target stage, pipeline version, and terminal status; and
- all PRIMARY failure evidence represented by the composite envelope, including
  its hash, class-specific canonical evidence, and exact PRIMARY raw bytes.

A PRIMARY-committed graph can never equal a REPAIR plan merely because the
score fields match: its raw-envelope schema/content, scoring ProviderCall
operation/identity, and producer metadata differ. Two REPAIR plans with
different PRIMARY failure evidence can never compare equal because the sealed
failure-evidence hash changes the REPAIR request identity and composite raw
envelope. Any partial, legacy, pending, failed, missing, mismatched, or
cross-role graph fails closed without a new provider/Judge call or write.

This is not fake-primary conversion: the repair raw evidence, failure binding,
attempt role, quality operation, attestation, and two ProviderCall identities
remain explicitly `REPAIR` throughout validation and persistence. It shares
the persistence mechanism, not PRIMARY provenance.

## 6. Required attack matrix and behavioral tests

The test suite must distinguish rejection before dispatch from rejection after a
legitimate stateful action. “Zero writes” is an absolute assertion only for an
attack rejected before any legitimate state transition; it must not be applied
retroactively to a test whose security behavior is an approved terminal
transition.

### Category A — pre-dispatch rejection attacks

For this category, the rejection occurs before write-plan minting. Capture the
baseline before the attack and assert the absolute post-baseline effects:
**zero additional scoring-provider calls, zero additional Judge calls, zero filesystem
writes, zero Artifact writes, zero SQLite success writes, and no video/job
success transition**. Filesystem writes include tmp/final/mkdir/promote/
directory-fsync activity. SQLite success writes include ProviderCall completion,
response-artifact ID, score, pipeline-stage, and job-success updates. No cache
write, terminal/retry transition, or `ValidatedScoringWritePlan` may exist.

| Test case | Injection / action | Required behavioral result |
|---|---|---|
| Forge `SCHEMA_OR_PARSE_INVALID` | Seal that class while the exact PRIMARY raw response parses and schema-validates successfully. | PRIMARY reparse disproves the class; reject before write-plan minting and satisfy every Category A assertion. |
| Forge `LANGUAGE_INVALID` | Seal language-invalid evidence while the canonical PRIMARY candidate passes the frozen language validator. | PRIMARY reparse plus language revalidation disproves the class; reject before write-plan minting and satisfy every Category A assertion. |
| Forge `JUDGE_REJECT` | Supply mismatched PRIMARY Judge H1/H2, Judge raw response/result, operation, or current authority for a claimed reject. | Rebuilt PRIMARY Judge identity/evidence fails equality; reject before write-plan minting and satisfy every Category A assertion. |
| Forge `JUDGE_UNCERTAIN` | Supply PRIMARY Judge evidence that does not independently re-derive the exact `UNCERTAIN` result/reason/code. | Rebuilt Judge evidence disproves uncertainty; reject before write-plan minting and satisfy every Category A assertion. |
| Mix PRIMARY raw A with failure evidence B | Combine one exact PRIMARY raw response with candidate/quality/Judge/class-specific evidence derived from another. | Raw reparse, hash, candidate, and evidence cross-bindings reject before write-plan minting and satisfy every Category A assertion. |
| Mix PRIMARY identity A with REPAIR success B | Combine a repair success/envelope with a different original scoring input or PRIMARY request identity. | Rebuilt identity and failure-evidence hash mismatch reject before write-plan minting and satisfy every Category A assertion. |
| Substitute PRIMARY ProviderCall identity into REPAIR plan | Force `local-scoring`/PRIMARY request fields where the sealed REPAIR scoring ProviderCall fields are required. | Exact REPAIR request identity recomputation rejects before write-plan minting and satisfies every Category A assertion. |
| Substitute REPAIR identity into PRIMARY branch | Feed REPAIR operation/request fields to exact `PhaseFTrustedScoringSuccess` validation. | The unchanged PRIMARY branch rejects cross-role material before write-plan minting and satisfies every Category A assertion. |
| Forge composite envelope schema/version or hashes | Alter `trusted-scoring-repair-envelope-v1`, raw bytes/hash/length, structured bytes/hash/length, or failure-evidence hash. | Canonical envelope/plan validation rejects before write-plan minting and satisfies every Category A assertion. |
| Direct persistence with forged repair success | Call `persist_success()` with a hand-built, low-level, or otherwise forged `PhaseHTrustedRepairSuccess`. | Exact type, runtime mint, seal, PRIMARY failure proof, and REPAIR chain validation reject before write-plan minting and satisfy every Category A assertion. |
| Unknown `PrimaryFailureEvidence` field | Insert an unrecognized field at any depth of `PrimaryFailureEvidence`. | Exact typed parsing rejects unknown fields before write-plan minting and satisfies every Category A assertion. |
| Missing `PrimaryFailureEvidence` field | Remove any required top-level or required applicable tagged-evidence field. | Exact typed parsing rejects missing fields before write-plan minting and satisfies every Category A assertion. |
| Non-canonical equivalent evidence | Supply syntactically valid JSON that parses to the same typed object but differs in key order, separators, whitespace, Unicode representation, or duplicate-key encoding. | Canonical reserialize bytes differ from the seal; reject before write-plan minting and satisfy every Category A assertion. |
| Forged parser diagnostic | Seal a parser diagnostic code inconsistent with the exact PRIMARY raw response. | The pure current-parser mapper produces a different code (or succeeds); reject before write-plan minting and satisfy every Category A assertion. |
| Free-form parser exception authority | Replace typed parser evidence with free-form exception text or add such text as a purported authority field. | Schema rejects the field/form; no exception text is parsed as authority, and every Category A assertion holds. |
| LANGUAGE evidence where validator passes | Seal `LANGUAGE_INVALID` while `detect_scoring_language_violation` returns `VALID`. | Typed language replay disproves the evidence; reject before write-plan minting and satisfy every Category A assertion. |
| Candidate/evidence hash mismatch | Change a PRIMARY or REPAIR candidate, candidate hash, raw binding, or language evidence candidate hash independently. | Canonical candidate/hash cross-binding fails before write-plan minting and satisfies every Category A assertion. |
| `JUDGE_REJECT` raw replays to PASS | Seal `JUDGE_REJECT` but supply captured Judge model content that pure replay maps to `PASS`. | Pure Judge verifier/result equality fails before write-plan minting and satisfies every Category A assertion. |
| `JUDGE_REJECT` raw replays to UNCERTAIN | Seal `JUDGE_REJECT` but supply captured Judge model content that pure replay maps to `UNCERTAIN`. | Pure Judge verifier/result equality fails before write-plan minting and satisfies every Category A assertion. |
| `JUDGE_UNCERTAIN` raw replays to REJECT or PASS | Seal `JUDGE_UNCERTAIN` but supply model content that pure replay maps to `REJECT` or `PASS`. | Pure Judge verifier/result equality fails before write-plan minting and satisfies every Category A assertion. |
| Forged Judge H1 | Alter H1 while retaining the operation input and other Judge evidence. | H1 recomputation fails before write-plan minting and satisfies every Category A assertion. |
| Forged Judge H2 | Alter H2 while retaining the operation input/H1 and other Judge evidence. | H2 recomputation through `build_provider_request_hash()` fails before write-plan minting and satisfies every Category A assertion. |
| Judge raw bytes/hash/length mismatch | Alter captured Judge content, UTF-8 byte length, or SHA-256 independently. | Strict UTF-8 length/hash verification fails before write-plan minting and satisfies every Category A assertion. |
| PRIMARY Judge evidence in REPAIR role | Substitute `JudgeEvidence(role=PRIMARY)` for the required REPAIR Judge evidence. | Role/operation/H1/H2/input binding fails before write-plan minting and satisfies every Category A assertion. |
| REPAIR Judge evidence in PRIMARY role | Substitute `JudgeEvidence(role=REPAIR)` for PRIMARY failure evidence. | Role/operation/H1/H2/input binding fails before write-plan minting and satisfies every Category A assertion. |
| Transport/no-response as `JUDGE_UNCERTAIN` | Supply timeout, interruption, protocol/no-content state, or absent captured model content with a claimed `JUDGE_UNCERTAIN`. | No full `JudgeEvidence` exists; classify H1 unknown/ineligible and satisfy every Category A assertion. |
| Composite unknown nested field | Insert an unrecognized field in any `RepairCompositeEnvelope` nested evidence object. | Exact nested schema parsing rejects before write-plan minting and satisfies every Category A assertion. |
| Composite canonical reserialize mismatch | Supply a parseable composite envelope whose canonical reserialization differs byte-for-byte from sealed bytes. | Exact reserialize-equality rejects before write-plan minting and satisfies every Category A assertion. |
| `object.__new__` | Allocate an uninitialized `PhaseHTrustedRepairSuccess` shell, including one populated only through low-level attribute operations. | No runtime-only mint provenance exists; exact-type/seal/provenance checks reject and satisfy every Category A assertion. |
| `object.__setattr__` mutation | Attempt to mutate each sealed envelope binding after minting: PRIMARY identity/failure/raw hash, REPAIR raw/provider/identity, Judge evidence, attestation, or final result bytes. | Immutability rejects mutation; if a test bypasses normal mutation, re-derived prewrite validation rejects the changed value and satisfies every Category A assertion. |
| Copy, deepcopy, pickle restoration | Apply `copy.copy`, `copy.deepcopy`, and pickle round-trip to a legitimate repair success. | Each operation is rejected; no restored object can invoke persistence. A forged restored shape reaching the entry satisfies every Category A assertion. |
| Fake provenance | Alter a sealed provider/model/digest, REPAIR identity, Judge H1/H2, attestation, primary failure class/evidence, or raw/candidate/result binding. | Canonical re-derivation rejects the mismatch before write-plan minting and satisfies every Category A assertion. |
| PRIMARY-to-REPAIR substitution | Present PRIMARY aggregate/evidence where a REPAIR aggregate is required, relabel a REPAIR success as PRIMARY, or swap their raw/identity/quality evidence. | Role, envelope, and identity cross-binding reject; REPAIR transport identity can never be treated as PRIMARY provenance. Every Category A assertion holds. |
| Persistence bypass | Call a repository method/direct writer, pass a plan/raw bytes/Artifact/ProviderCall/legacy cache data to a persistence boundary, or call any proposed repair-specific method. | No such public path exists. Only `persist_success()` accepts an exact sealed success; all bypass forms reject and satisfy every Category A assertion. |

### Category B — stateful rejection attacks

These tests begin after a legitimate dispatch, admission consumption, or
recovery fact may already exist. Capture a baseline immediately before the
rejected additional action (the rejection point), then assert: **no additional
scoring-provider calls, no additional Judge calls, no duplicate success
persistence, and no duplicate REPAIR/REPAIR_JUDGE consumption**. No new
Artifact, completed ProviderCall, response-artifact ID, score, stage, or job
success may be produced beyond that baseline.

The only allowed writes after the rejection point are explicitly defined
terminal fail-closed transitions. In particular,
`UNKNOWN_PROVIDER_STATE` may perform its already-approved terminal job/error
update; it cannot write a success graph, re-enable admission, or authorize a
new provider/Judge call. No generic retry, reclaim, takeover, or repair
transition is permitted.

| Test case | Rejection-point setup / action | Required behavioral result |
|---|---|---|
| Duplicate REPAIR dispatch | A legitimate REPAIR role has already been consumed; replay the received PRIMARY failure, call the private branch again, or race two branches. | The second dispatch is denied before contact. Relative to the baseline: no additional provider/Judge call, no duplicate REPAIR consumption, and no duplicate success persistence. |
| Duplicate REPAIR Judge dispatch | A legitimate REPAIR Judge role has already been consumed; request a second REPAIR Judge call. | The second Judge dispatch is denied before contact. Relative to the baseline: no additional Judge/provider call, no duplicate REPAIR_JUDGE consumption, and no duplicate success persistence. |
| `UNKNOWN_PROVIDER_STATE` handling | Simulate timeout, lost response, process crash, lease loss/expiry, or missing durable ProviderCall after a dispatched attempt. | The job may receive only the approved terminal unknown job/error update. It never classifies as an eligible PRIMARY failure, enters REPAIR, writes a success graph, or makes an additional provider/Judge call. |
| Restart after consumed identity | Restart after PRIMARY, REPAIR, or either Judge identity was consumed but before a successful trusted commit. | The recovered state is terminal unknown/fail-closed, not restored admission. Relative to the baseline: no additional dispatch, no duplicate role consumption, no duplicate success persistence, and only the explicitly allowed terminal update if still required. |

An exact already-complete G graph remains an idempotent-completion case, not a
rejection case: it makes no external call and creates no duplicate success
write.

## 7. Future implementation scope

If this proposal is accepted, a separate H2 task card may authorize only the
smallest implementation required for the design:

- `src/youtube_intel/runtime.py`: private PRIMARY-failure-to-REPAIR
  orchestration, runtime-owned closure, and no-public-surface enforcement.
- `src/youtube_intel/scoring_admission.py`: private use of the existing role
  state for runtime-owned REPAIR/REPAIR_JUDGE consumption; no receipt, token,
  registry, or caller admission API.
- `src/youtube_intel/providers/ollama.py`: one bounded candidate-only REPAIR
  transport using the existing canonical parser/local safety rules, plus the
  narrow Judge-seam change required to capture exact successful extracted model
  content before interpretation and factor the existing Judge JSON/schema/
  evidence-registry parsing and result promotion into the pure replay verifier.
  It may retain that evidence only in the internal runtime flow; it may not add
  a public raw-response API, new provider, network protocol, second Judge
  implementation, cache, or persistence behavior.
- `src/youtube_intel/scoring.py`: the private sealed
  `PhaseHTrustedRepairSuccess` aggregate/minting guard, REPAIR
  raw/candidate identity reconstruction, the versioned evidence wire-schema
  validation/canonical serialization helpers, and the strictly private
  `persist_success()` verifier/plan branch, reusing the existing writer and
  atomic registration only.
- `src/youtube_intel/quality.py`: only minimal typed evidence construction/
  replay support needed to build and verify existing PRIMARY/REPAIR Judge
  operation identities, content-quality inputs/results, attestation, and
  Finalizer inputs; no policy or TASK-016B validator change.
- Focused H2 tests plus targeted Phase G/H1 regression tests, and the H2
  handoff evidence.

The following remain forbidden: schema or migration changes; a new or
externally observable persistence boundary; Phase G rewrite; any capability
object beyond the required sealed `PhaseHTrustedRepairSuccess`; public repair APIs;
receipt/token/registry/continuation exposure; repository repair APIs; new
writer or SQLite path; manual Artifacts/ProviderCalls; cache/recovery work;
`src/youtube_intel/domain.py` contract changes; TASK-016B Language Validator
changes; dependencies, lockfiles, configuration, Cloud, real
network/model/Vault/credential use; and any repair eligibility from
`UNKNOWN_PROVIDER_STATE`.

## 8. Acceptance conditions for a later H2 authorization

An H2 implementation may be authorized only after an independent review can
demonstrate that:

- exactly one eligible received PRIMARY failure yields at most one REPAIR
  provider call and one REPAIR Judge call;
- every eligible PRIMARY failure class is independently reproducible from its
  sealed exact raw/candidate/quality/Judge/provenance evidence, rather than a
  stored enum, and every non-reproducible case fails closed;
- PRIMARY, REPAIR, PRIMARY Judge, and REPAIR Judge identities are distinct,
  stable, canonical, and correctly bound to provider/model/digest;
- REPAIR follows the specified validation order and only a finalizer-produced
  trusted result sealed inside `PhaseHTrustedRepairSuccess` can reach
  persistence;
- `persist_success()` remains the sole entry and its PREWRITE/filesystem/SQLite
  behavior is unchanged apart from the exact-type private verifier and common
  plan mapping defined here;
- REPAIR uses the exact original PRIMARY result/artifact namespace, the sealed
  REPAIR scoring/REPAIR Judge ProviderCall identities, and complete-graph
  equality defined here; and
- all Category A/B attack-matrix evidence meets its specified zero-I/O or
  rejection-point-relative accounting; and
- all crash, timeout, lease-loss, and restart paths preserve the H1
  `UNKNOWN_PROVIDER_STATE` no-repair rule.

Until an independent review accepts this authorization, H2 remains design-only
and no H2 implementation is authorized.
