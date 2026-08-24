# TASK-016C Phase H2 — REPAIR Trusted-Flow Authorization Proposal

## Status and decision requested

`PROPOSAL ONLY / IMPLEMENTATION NOT AUTHORIZED`.

This proposal assumes Phase G is accepted and H1-A/H1-B are closed. It
authorizes neither code, tests, review, merge, network calls, cache recovery,
nor a public repair surface. Its purpose is to define the narrow future H2
implementation boundary by which one eligible, received PRIMARY failure may be
repaired without weakening the accepted trusted-persistence chain.

## 1. Frozen contracts

The only persistence route remains:

```text
PhaseFTrustedScoringSuccess
  -> TrustedPersistenceEntry.persist_success()
  -> PREWRITE_VALIDATE
  -> filesystem protocol
  -> SQLite atomic registration
```

H2 must preserve all of the following.

- `TrustedPersistenceEntry.persist_success()` remains the only persistence
  ingress, only filesystem promoter, and only owner of SQLite registration.
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
  ingress remain unchanged.

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
  -> internal existing persist_success() bridge
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

H2 must not mint a public `PhaseHTrustedRepairSuccess` (or any other repair
capability object). Instead, `RuntimeOperations` retains the repair evidence in
a non-exported lexical continuation for the duration of the same call stack.
That continuation is neither a DTO nor a transferable credential: it has no
public factory, field access, serialization, copy/deepcopy/pickle support, or
caller entry point.

The runtime immediately invokes the existing
`TrustedPersistenceEntry.persist_success()` path through an H2-private branch
inside that entry. The public entry remains `persist_success()`; there is no
`persist_repair()` and no repository-facing repair method. The branch receives
its REPAIR evidence only from the runtime closure, re-derives all identities,
and performs the same zero-write validation before it can mint the existing
opaque `ValidatedScoringWritePlan`.

The H2-private verifier must prove, in memory, all of the following before
delegating to the existing writer/registrar:

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
   as one existing write plan. The raw envelope contains the role-distinct
   provenance and both primary/repair bindings; it is the plan's single
   canonical record, not new scattered database fields.

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

## 6. Required attack matrix

| Attempt | Required defense and outcome |
|---|---|
| Forged repair result | Reject before planning unless the runtime closure re-derives raw-to-candidate binding, full REPAIR PASS/attestation, context, and Finalizer result. A bare `ScoreResult`/`TrustedScoreResult` cannot enter. |
| Fake repair identity | Recompute canonical REPAIR input and `build_provider_request_hash()`; require role-distinct operation, current provider/model/digest, eligible PRIMARY failure binding, and collision checks. Any supplied identity is ignored/rejected. |
| Replayed PRIMARY failure | A failure has effect only while the original private stack is live. The consumed PRIMARY/REPAIR role state denies replay; restart becomes `UNKNOWN_PROVIDER_STATE`, never repair. |
| Duplicate repair call | Consume REPAIR before contact under the existing execution-state lock; re-check active exclusive lease and ProviderCall absence. A second scoring or Judge REPAIR role is denied before contact. |
| `UNKNOWN_PROVIDER_STATE` abuse | Unknown, timeout, crash, lost response, expired lease, or missing durable call state finalizes fail-closed. It has no eligible failure class, repair path, retry, takeover, or cache interpretation. |
| `object.__new__`, copy, deepcopy, pickle | No new repair capability exists to forge. Forged shells and copied/restored values cannot enter the lexical runtime branch, re-derive evidence, consume a private admission, or call the H2-private verifier. All public/persisted shapes fail exact-type and provenance checks. |
| Direct persistence bypass | Only `TrustedPersistenceEntry.persist_success()` reaches PREWRITE, file promotion, and SQLite registration. It rejects caller data, plans, raw bytes, Artifact/ProviderCall records, mappings, JSON, cache, and legacy material; no other writer/API is added. |

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
- `src/youtube_intel/scoring.py`: REPAIR raw/candidate identity reconstruction
  and the strictly private `persist_success()` verifier/plan branch, reusing
  the existing writer and atomic registration only.
- `src/youtube_intel/quality.py`: only minimal reuse necessary to build and
  verify the existing REPAIR-role quality operation, attestation, and
  Finalizer inputs; no policy or validator changes.
- Focused H2 tests plus targeted Phase G/H1 regression tests, and the H2
  handoff evidence.

The following remain forbidden: schema or migration changes; any persistence
boundary change; Phase G rewrite; new capability objects; public repair APIs;
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
  trusted result can reach persistence;
- `persist_success()` remains the sole entry and its PREWRITE/filesystem/SQLite
  behavior is unchanged apart from its private evidence verifier;
- all attack-matrix cases fail closed before external contact or persistence as
  applicable; and
- all crash, timeout, lease-loss, and restart paths preserve the H1
  `UNKNOWN_PROVIDER_STATE` no-repair rule.

Until then, H2 remains design-only.
