# TASK-016C Phase H2 — REPAIR Trusted-Flow Authorization Proposal

## Status and decision requested

`REQUEST-CHANGES AMENDMENT / IMPLEMENTATION NOT AUTHORIZED`.

This proposal assumes Phase G is accepted and H1-A/H1-B are closed. It
authorizes neither code, tests, review, merge, network calls, cache recovery,
nor a public repair surface. Its purpose is to define the narrow future H2
implementation boundary by which one eligible, received PRIMARY failure may be
repaired without weakening the accepted trusted-persistence chain.

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

The aggregate seals one repair envelope; it is not assembled from caller
arguments at persistence time. The envelope contains only runtime-derived,
immutable values needed for repeat validation:

| Binding | Required sealed value |
|---|---|
| PRIMARY identity | Original `primary_scoring_request_hash` and `primary_normalized_input_hash`, each rebuilt with `build_scoring_request_identity()` from the canonical original `ScoringInput`. |
| PRIMARY failure | Closed runtime-derived `primary_failure_class` and the exact `primary_raw_response_hash`. |
| REPAIR raw/candidate | Exact bounded strict-UTF-8 repair raw response, `repair_raw_response_hash`, canonical parser-derived candidate, and canonical candidate hash. |
| REPAIR provider identity | Current runtime scoring provider, model, model digest, output language, temperature, output limit, description limit, repair prompt version, and repair schema version. |
| REPAIR attempt identity | Canonical REPAIR normalized-input hash and the `build_provider_request_hash()` request hash for `local-scoring-repair-v1`; it is distinct from PRIMARY and both Judge identities. |
| Quality/Judge evidence | Canonical quality input, complete REPAIR `PASS` result, `QualityJudgeOperationInput(attempt_role=REPAIR)`, Judge H1/H2, and current-authority `QualityPassAttestation`. |
| Finalized structured value | Exact `TrustedScoreResult` from the Finalizer plus sealed canonical structured-result bytes/hash. |

The envelope's raw persistence bytes must canonically include the PRIMARY
identity/failure/raw-hash bindings, REPAIR raw hash and provider/attempt
identity, REPAIR Judge evidence, and attestation. The bytes are one sealed
input to the existing write plan, rather than new scatter fields or a database
schema change. REPAIR transport identity never replaces the original PRIMARY
scoring identity of the score/result or logical scoring artifact namespace.

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

Both success types must execute the same `PREWRITE_VALIDATE` phase, the same
temporary-write/fsync/hash/no-clobber-promote/directory-fsync/final-reopen
protocol, and the same single SQLite registration transaction. Neither branch
may reserve or complete a ProviderCall, create an Artifact, set a response
artifact ID, write a score/stage/job, or touch the filesystem before its
prewrite verifier produces the common opaque `ValidatedScoringWritePlan`.

The H2 REPAIR verifier must prove, in memory, all of the following before it
may mint that existing plan:

1. PRIMARY identity, exact PRIMARY raw hash, and eligible runtime-derived
   failure class bind the REPAIR identity.
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

Only this successfully validated plan enters the already-frozen file protocol
and the existing single SQLite registration transaction. It creates the same
two Artifact records, two completed ProviderCalls, scoring summary, stage, and
job transition as the G path; it uses the REPAIR scoring and REPAIR Judge
ProviderCall identities while retaining the PRIMARY scoring identity for the
score/result and logical artifact namespace. No third call, third Artifact,
new writer, alternate SQLite path, or pre-PREWRITE state is permitted.

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

For this category, capture state before the attack and assert: **zero
scoring-provider calls, zero Judge calls, zero Artifact writes, zero SQLite
success writes, and no state transition**. “Zero SQLite success writes” covers
ProviderCall completion, response-artifact ID, score, pipeline stage, and job
success updates; “no state transition” additionally excludes an attempted
terminal/retry transition. There may be no tmp/final/mkdir or cache write.

| Test case | Injection / action | Required behavioral result |
|---|---|---|
| Forged repair success | Supply a hand-built `PhaseHTrustedRepairSuccess`, a bare result, mapping, JSON restore, or a sealed object with one altered provenance/hash field. | Exact-type or re-derived provenance validation rejects before plan minting and satisfies every Category A assertion. |
| `object.__new__` | Allocate an uninitialized `PhaseHTrustedRepairSuccess` shell, including one populated only through low-level attribute operations. | No runtime-only mint provenance exists; exact-type/seal/provenance checks reject and satisfy every Category A assertion. |
| `object.__setattr__` mutation | Attempt to mutate each sealed envelope binding after minting: PRIMARY identity/failure/raw hash, REPAIR raw/provider/identity, Judge evidence, attestation, or final result bytes. | Immutability rejects mutation; if a test bypasses normal mutation, re-derived prewrite validation rejects the changed value and satisfies every Category A assertion. |
| Copy, deepcopy, pickle restoration | Apply `copy.copy`, `copy.deepcopy`, and pickle round-trip to a legitimate repair success. | Each operation is rejected; no restored object can invoke persistence. A forged restored shape reaching the entry satisfies every Category A assertion. |
| Fake provenance | Alter a sealed provider/model/digest, REPAIR identity, Judge H1/H2, attestation, primary failure class, or raw/candidate/result binding. | Canonical re-derivation rejects the mismatch before plan minting and satisfies every Category A assertion. |
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

A future H2 implementation may be considered only if its independent review
can demonstrate that:

- exactly one eligible received PRIMARY failure yields at most one REPAIR
  provider call and one REPAIR Judge call;
- PRIMARY, REPAIR, PRIMARY Judge, and REPAIR Judge identities are distinct,
  stable, canonical, and correctly bound to provider/model/digest;
- REPAIR follows the specified validation order and only a finalizer-produced
  trusted result sealed inside `PhaseHTrustedRepairSuccess` can reach
  persistence;
- `persist_success()` remains the sole entry and its PREWRITE/filesystem/SQLite
  behavior is unchanged apart from its private evidence verifier;
- all attack-matrix cases fail closed before external contact or persistence as
  applicable; and
- all crash, timeout, lease-loss, and restart paths preserve the H1
  `UNKNOWN_PROVIDER_STATE` no-repair rule.

Until then, H2 remains design-only.
