# TASK-016C Phase H2 — REPAIR Trusted-Flow Authorization Proposal

## Status and decision requested

`READY FOR PHASE H2 AUTHORIZATION INDEPENDENT REVIEW`.

This proposal assumes Phase G is accepted and H1-A/H1-B are closed. It
authorizes neither code, tests, review, merge, network calls, cache recovery,
nor a public repair surface. Its purpose is to define the narrow future H2
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
   `LANGUAGE_INVALID`, `DETERMINISTIC_QUALITY_REJECT`, `JUDGE_REJECT`, or
   `JUDGE_UNCERTAIN`.
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

### Sealed PRIMARY failure evidence

`PhaseHTrustedRepairSuccess` must seal an exact, canonical
`PrimaryFailureEvidence` structure with
`failure_evidence_schema = "primary-scoring-failure-evidence-v1"`. Its
canonical JSON SHA-256 is `primary_failure_evidence_hash`, which is both
sealed in the repair success and included in the canonical REPAIR request
identity above. A caller-supplied `primary_failure_class` has no authority by
itself.

Every `PrimaryFailureEvidence` contains, at minimum:

- the exact bounded strict-UTF-8 PRIMARY raw response string and its exact
  UTF-8 bytes semantics;
- `primary_raw_response_hash = SHA256(primary_raw_response.encode("utf-8"))`;
- canonical original `ScoringInput` bytes/hash plus the PRIMARY normalized and
  request identities rebuilt with `build_scoring_request_identity()`;
- current PRIMARY scoring provenance: operation, provider, model, model
  digest, prompt version, schema version, output language, temperature,
  maximum output tokens, and maximum description characters;
- the canonical parsed/validated PRIMARY `ScoringCandidate` and candidate hash
  when parsing succeeded; otherwise an explicit absent-candidate marker;
- one closed eligible failure class and its class-specific canonical evidence;
  and
- the current quality-authority provenance whenever the failure passed the
  PRIMARY quality/Judge boundary.

`PREWRITE_VALIDATE` reconstructs the original scoring input from sealed bytes,
rebuilds its PRIMARY identity against the current runtime context, recomputes
the raw hash, and checks every sealed provenance value before it evaluates the
failure class. A missing, non-canonical, malformed, rotated, or
non-reproducible evidence field makes the failure ineligible; it cannot reach
REPAIR or a write plan.

The eligible classes and their re-proof requirements are frozen as follows.

| Eligible class | Sealed class-specific evidence | Required independent PREWRITE proof |
|---|---|---|
| `SCHEMA_OR_PARSE_INVALID` | `parser_contract = "scoring-candidate-parser-v1"`; canonical failure mode `JSON_DECODE`, `ENVELOPE_INVALID`, or `CANDIDATE_SCHEMA_INVALID`; canonical parser diagnostic code; no candidate. | Run the one canonical PRIMARY parser/schema validator against the exact sealed PRIMARY raw response. It must fail with the same authorized failure mode and diagnostic code. A successful parse, a different failure mode, or reliance on the stored enum rejects. |
| `LANGUAGE_INVALID` | Exact canonical PRIMARY candidate/hash; canonical language-validator input/result; definitive validator failure code. | Reparse the PRIMARY raw response, require the sealed candidate/hash, then rerun the frozen TASK-016B language validator against the rebuilt candidate/input. It must yield the same definitive invalid result/code. A pass, uncertainty, candidate mismatch, or enum-only proof rejects. |
| `DETERMINISTIC_QUALITY_REJECT` | Exact canonical PRIMARY candidate/hash; canonical quality input/hash; deterministic-gate result and reject reason; no Judge evidence. | Reparse and validate the candidate, rebuild the quality input, and rerun the frozen deterministic gate. Its canonical reject result/reason must exactly equal the sealed evidence. A non-reject or a Judge-derived substitute rejects. |
| `JUDGE_REJECT` | Exact canonical PRIMARY candidate/hash and quality input/hash; PRIMARY `QualityJudgeOperationInput(attempt_role=PRIMARY)`; Judge H1/H2; exact bounded PRIMARY Judge raw response; canonical parsed `ContentQualityResult(REJECT)`; current quality authority provenance. | Rebuild the PRIMARY operation and H1/H2, require current authority/config equality, reparse/validate the sealed Judge response through the frozen Judge-result contract, and require the resulting canonical `REJECT` evidence to equal the seal. Mismatched response, H1/H2, operation, authority, or non-reject rejects. |
| `JUDGE_UNCERTAIN` | The same PRIMARY Judge operation/H1/H2/raw-response/authority evidence as `JUDGE_REJECT`, with canonical parsed `ContentQualityResult(UNCERTAIN)` and its exact uncertainty reason/code. | Rebuild the PRIMARY operation and H1/H2 and reparse/validate the sealed Judge response under the frozen contract. It must independently yield the exact sealed `UNCERTAIN` result/reason/code. Any non-uncertain, mismatch, or unavailable proof rejects. |

`UNKNOWN_PROVIDER_STATE`, transport failure, timeout, process loss, authority
rotation, lease loss, and any class without the complete reproducible evidence
above are not eligible failure classes. They remain H1 fail-closed states and
never acquire a REPAIR identity.

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

The composite envelope has these top-level canonical fields, with no omitted
or caller-supplied side channel:

```text
envelope_schema = "trusted-scoring-repair-envelope-v1"
primary_failure_evidence
repair_attempt = {
  raw_response, raw_response_hash, candidate, candidate_hash,
  normalized_input_hash, request_hash,
  operation = "local-scoring-repair-v1",
  provider, model, model_digest, prompt_version, schema_version,
  output_language, temperature, max_output_tokens, max_description_chars
}
repair_quality = {
  input, input_hash, result = PASS, operation(attempt_role=REPAIR),
  judge_h1, judge_h2, judge_raw_response, authority_provenance,
  attestation
}
trusted_result_binding = { structured_result_bytes, structured_result_hash,
                           structured_result_length }
```

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
**zero additional scoring-provider calls, zero Judge calls, zero filesystem
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
  transport using the existing canonical parser and existing local safety
  rules; no provider-side trust or persistence.
- `src/youtube_intel/scoring.py`: the private sealed
  `PhaseHTrustedRepairSuccess` aggregate/minting guard, REPAIR
  raw/candidate identity reconstruction, and the strictly private
  `persist_success()` verifier/plan branch, reusing the existing writer and
  atomic registration only.
- `src/youtube_intel/quality.py`: only minimal reuse necessary to build and
  verify the existing REPAIR-role quality operation, attestation, and
  Finalizer inputs; no policy or validator changes.
- Focused H2 tests plus targeted Phase G/H1 regression tests, and the H2
  handoff evidence.

The following remain forbidden: schema or migration changes; a new or
externally observable persistence boundary; Phase G rewrite; any capability
object beyond the required sealed `PhaseHTrustedRepairSuccess`; public repair APIs;
receipt/token/registry/continuation exposure; repository repair APIs; new
writer or SQLite path; manual Artifacts/ProviderCalls; cache/recovery work;
TASK-016B Language Validator changes; dependencies, lockfiles, configuration,
Cloud, real network/model/Vault/credential use; and any repair eligibility from
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
