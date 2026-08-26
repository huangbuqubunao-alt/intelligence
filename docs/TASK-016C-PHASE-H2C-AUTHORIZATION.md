# TASK-016C Phase H2-C — Trusted Repair Success Minting and Phase G Re-entry

## Status, authority, and scope

Status: **READY FOR H2-C AUTHORIZATION INDEPENDENT REVIEW**.  This is a design
and implementation authorization only.  It authorizes no implementation in
this commit, no provider or Judge contact, no Phase G redesign, no schema or
migration, no cache/recovery work, and no merge/push/tag/rebase/reset.

It is subordinate to the accepted H2/H2-B contracts, in particular the H2-B
Round 5 lexical aggregate lifetime and the final accepted implementation
(`c6626ab`).  It replaces exactly the live H2-B-only full-PASS branch:

```text
aggregate -> fail_job(CAPABILITY_UNAVAILABLE, H2B_PASS_AWAITING_H2C)
```

with the continuation below.  It does not alter any historical terminal row.

Reuse decision: **DIRECT** — reuse the approved project primitives,
`RepairTrustedScoringFinalizer`, H2 evidence builders, Phase G persistence
entry, existing SQLite schema, and standard-library hashing/UTF-8 handling.
No dependency, component, or external source is introduced.

## 1. Authority boundary and exact entry point

H2-C exists only as the immediate lexical continuation after:

```python
aggregate = PhaseH2BValidatedRepairResult(...)
```

inside the same actual `RuntimeOperations.scoring_stage` execution frame which
just completed the admitted H2-B REPAIR and REPAIR_JUDGE path.  The only live
shape is:

```text
aggregate + same frame-owned inputs
  -> H2-C local replay/mint
  -> PhaseHTrustedRepairSuccess
  -> TrustedPersistenceEntry.persist_success(success)
```

H2-C executes instead of the transitional `fail_job`, before any terminal
transition.  It is not a method, function, closure returned to a caller,
callback, hook, registry lookup, cache replay, repository operation, or retry
route.  The following (including underscore variants) are forbidden:
`h2c_finalize`, `finalize_repair`, `verify_h2b_result`,
`mint_repair_success`, `persist_validated_repair`, `persist_repair`,
`persist_h2c`, `repair_writer`, and `repair_repository_success`.

Possession of a complete, self-consistent, copied, pickled, reconstructed, or
low-level-forged `PhaseH2BValidatedRepairResult` grants no H2-C execution.
Control-flow placement is the only execution provenance.  Aggregate evidence
is data, never authority; no `repair_consumed`, `judge_consumed`, `admitted`,
token, receipt, capability, nonce, sentinel, registry key, or continuation
object may be added to change that fact.

## 2. Runtime-owned trust roots

H2-C may use only these roots from the current runtime frame:

1. current `job_id`, runtime owner, and active scoring-lease proof;
2. the original exact validated `ScoringInput` used for PRIMARY;
3. a freshly rebuilt `PrimaryTrustedContext` derived from that input and the
   same current validated settings;
4. the same validated `LocalScoringSettings` object used by H2-B;
5. current runtime-owned scoring and quality provenance authorities; and
6. the local H2-B aggregate as untrusted replay material.

No aggregate field is a root.  H2-C accepts no caller replacement for context,
settings, job/owner, PRIMARY semantic identity, Judge context, repair config,
or provenance authority.  It fresh-checks the active lease/owner before
minting; `persist_success()` retains its existing independent owned-running-job
check immediately before SQLite registration.  A changed settings object or
any aggregate settings/provenance mismatch is `SETTINGS_MISMATCH`.

Every security-significant nested value is reconstructed through its strict
schema/canonical representation and compared to the aggregate value.  Exact
type, frozen dataclass/Pydantic identity, private constructor, object identity,
or prior H2-B verification is never sufficient.

## 3. Normative H2-C replay sequence

All steps are local and deterministic; any mismatch stops at the first
applicable closed reason in section 8.  No step may contact a provider or
Judge.

1. Verify current job/owner/active scoring lease in the live frame.
2. Rebuild `PrimaryTrustedContext` from original `ScoringInput` and current
   validated settings; compare all aggregate PRIMARY provenance.
3. Strictly reconstruct PRIMARY evidence and verify `PrimaryFailureEvidence`.
4. Require its class to be in the closed eligible set and match the aggregate
   class.
5. Rebuild `RepairNormalizedInput` using exactly
   `build_repair_normalized_input(job_id, primary_trusted_context,
   failure_evidence, validated_settings)`.
6. Compute its exact H2 JCS bytes and require RNI value and bytes equality.
7. Compute the RNI SHA-256 and require equality.
8. Recompute the REPAIR request hash and require equality.
9. Rebuild `render_task016c_repair_prompt_v2` and the exact REPAIR payload.
10. Require model, prompt, `stream=false`, format, `think=false`,
    temperature, `num_predict`, UTF-8 bytes, payload SHA-256, and payload
    byte length equality.
11. Replay authoritative REPAIR outer raw: strict UTF-8, frozen maximum,
    SHA-256/length, duplicate-key rejection, protocol-object rules, and exact
    response-string extraction.
12. Re-extract model content; re-run `parse_scoring_candidate`; require exact
    repaired candidate equality and recompute its hash.
13. Re-run only TASK-016B language validation and require `VALID` and exact
    evidence equality.
14. Reconstruct the accepted REPAIR `ContentQualityInput`; re-run
    `DeterministicContentQualityGate` and require PASS (no
    `EMPTY_CONTENT`, `CONTROL_CHARACTER_INVALID`, or `EXACT_REPETITION`).
15. Rebuild the REPAIR Judge trusted context and operation input from the
    replayed candidate, REPAIR request hash, and current settings; require
    `attempt_role=REPAIR`.
16. Recompute Judge H1 under the frozen canonical/JCS rule and Judge H2 with
    `build_provider_request_hash(operation="local-content-quality-v1", ...)`.
17. Replay Judge captured raw strictly: representation defined by the frozen
    H2 contract, strict UTF-8, at most 20,000 bytes inclusive, exact hash and
    length; pure-verify it and require semantic PASS.
18. Freshly validate the REPAIR `QualityPassAttestation` against replayed
    candidate, REPAIR request hash, Judge H1/H2, role, policy, and schema.
19. Invoke `RepairTrustedScoringFinalizer` with freshly reconstructed inputs.
    Its independent schema/provenance checks, gate replay, Judge replay,
    attestation verification, dual binding, and sealed serializer are required
    redundancy, not optional work already covered by H2-C.
20. Require exact field equality between the finalizer's `TrustedScoreResult`
    and `aggregate.finalizer_trusted_result`.
21. Recompute sealed structured UTF-8 bytes and require byte-for-byte,
    SHA-256, byte-length, schema version, and prompt-version equality.
22. Recheck every schema/version/settings value and the complete PRIMARY to
    REPAIR provenance matrix in section 5.
23. Construct the single trusted repair success only after steps 1–22 pass.

The H2-B 21-step contract is preserved, not replaced: old steps 1–4 map to
new 1–4; 5–8 map to 5–10; 9 maps to 11; 10–11 map to 12; old 12 is now split
across 19–21 (finalizer after the prerequisite language/gate/Judge replay);
old 13 maps to 13; 14–16 map to 15–16; 17–19 map to 17; 20 maps to 18 and
22; and 21 maps to 1–2 and 22.  The expanded sequence makes the previously
required deterministic gate, finalizer, and sealed-value checks explicit; it
does not delete or weaken an old check.

## 4. PRIMARY eligibility and raw/candidate replay

The only eligible PRIMARY classes are exactly:

- `SCHEMA_OR_PARSE_INVALID`: exact trustworthy PRIMARY outer raw plus the
  approved parser diagnostic must replay to the same failure;
- `LANGUAGE_INVALID`: PRIMARY raw/candidate must replay and TASK-016B must
  return exact `INVALID` evidence;
- `JUDGE_REJECT`: trustworthy PRIMARY Judge capture must pure-replay to
  `REJECT`; and
- `JUDGE_UNCERTAIN`: trustworthy PRIMARY Judge capture must pure-replay to
  `UNCERTAIN`.

`UNKNOWN_PROVIDER_STATE` and every other class are ineligible.  Aggregate
selection of an enum has no force.  PRIMARY replay includes original
`ScoringInput`, expected context identity, PRIMARY request hash, applicable
PRIMARY outer raw/candidate, `PrimaryFailureEvidence`, classification, and
applicable PRIMARY Judge evidence/raw.  Expected values come from the runtime
roots, never aggregate duplicates.

REPAIR raw is the exact captured outer `/api/generate` response body.  It is
not stored extracted content, pretty JSON, reserialization, or a candidate
substitute.  Its extracted response string is recomputed from strict
duplicate-key/protocol parsing.  Empty/whitespace REPAIR content fails the
candidate schema before the gate; post-schema gate failure is never rescued by
Judge PASS or an attestation.

## 5. Cross-binding and no-network rule

H2-C performs zero `/api/tags`, zero `/api/generate`, zero provider-factory
network contact, and zero Judge network contact on both success and failure.
Any required network dependency is a design blocker.

Let `P` be PRIMARY semantic request hash and `R` be REPAIR request hash.
`P != R`.  `R` binds the replayed RNI/JCS/hash, prompt/payload, raw,
candidate, deterministic quality input, Judge operation/H1/H2/raw,
attestation, and finalizer REPAIR provenance.  The result retains `P` as its
semantic score request hash; it never substitutes P for R.  This preserves the
dual binding without erasing repaired origin.

Therefore an R1/R2 attack with the same repaired candidate and same semantic
score rejects unless every value is R2-consistent with the deterministic
runtime-derived RNI/request.  Because the runtime derives the expected RNI
and R, substituting selected R2 fields into an R1 aggregate fails the relevant
identity, raw, Judge, attestation, finalizer, envelope, or byte check.

`object.__new__`, `object.__setattr__`, `model_construct`, fake subclasses,
extra attributes, copy/deepcopy, pickle, and hand-built serialized objects are
treated solely as untrusted inputs.  Their construction secrecy is irrelevant;
fresh replay and the Phase G prewrite verifier must reject every inconsistency.

## 6. `PhaseHTrustedRepairSuccess` and Phase G ingress

The type is `PhaseHTrustedRepairSuccess` in `src/youtube_intel/scoring.py`,
alongside `PhaseFTrustedScoringSuccess` and before
`TrustedPersistenceEntry`.  It is a narrow pre-persistence trust-boundary
type, contains no persistence behavior, is exact/non-subclassable/immutable,
and rejects normal construction, copying, deep-copying, and serialization.
Private/sentinel mechanics are defence in depth only.

It carries exactly: runtime job/owner/pipeline scope; original `ScoringInput`
semantic identity and PRIMARY request/normalized hashes; the canonical
`trusted-scoring-repair-envelope-v1` bytes, SHA-256, and length; exact
`TrustedScoreResult`; sealed structured bytes, SHA-256, length, prompt/schema
versions; and one private exact `RepairCompositeEnvelope` evidence bundle.
The bundle is the already-frozen six-field parent envelope: schema literal,
complete PRIMARY failure evidence, repair-provider/RNI evidence,
repair-candidate/raw evidence, repair-quality/Judge/attestation evidence, and
finalizer binding.  It is one compact sealed graph, not a caller scatter-plan.

Only the lexical H2-C code above may mint it after full replay.  There is no
public mint/factory.  A technically forged exact instance remains unable to
skip Phase G: `persist_success` exact-type checks first, then independently
reconstructs and verifies the complete envelope before any plan or write.

`TrustedPersistenceEntry.persist_success(success)` is extended by option A,
the closed exact union:

```text
type(success) is PhaseFTrustedScoringSuccess -> existing PRIMARY verifier
type(success) is PhaseHTrustedRepairSuccess  -> private REPAIR verifier
otherwise                                   -> reject before field read
```

No protocol/base class, duck typing, structural field interface, compatibility
adapter, caller write plan, alternate writer, or alternate ingress is allowed.
`persist_success` remains the only persistence method.

## 7. Shared Phase G plan and schema decision

The REPAIR verifier maps the success to the existing private
`_ValidatedScoringWritePlan`; after plan minting the writer, PREWRITE ordering,
filesystem protocol, no-clobber/idempotency rule, and SQLite transaction are
identical to PRIMARY.

The artifact namespace remains `scoring/<P>/raw(.json)` and
`scoring/<P>/structured(.json)`.  Raw artifact bytes are the exact replayed
`trusted-scoring-repair-envelope-v1` composite envelope; structured artifact
bytes are exactly the H2-C/finalizer sealed bytes—persistence must not
reserialize them.  Artifact kind, root, retention, write/promotion/fsync, and
SQLite completion state stay unchanged.  A duplicate is idempotent only when
the complete existing graph equals this plan; it must never overwrite or
diverge.

The persisted scoring `ProviderCall` uses REPAIR identity `R`:
`operation="local-scoring-repair-v1"`, RNI hash, REPAIR provider/model,
repair prompt/schema, and the shared raw artifact key.  The persisted Judge
ProviderCall uses replayed REPAIR Judge H2 and the same raw artifact.  No
ProviderCall row is created for the failed PRIMARY attempt.  PRIMARY semantic
identity remains in the result and composite envelope while R remains in both
ProviderCalls and the envelope, so existing schema preserves both identities.
No migration, table, artifact kind, or extra column is required; the existing
generic ProviderCall/artifact fields represent this provenance exactly.

PREWRITE remains zero-write and revalidates the repair graph before creating
the common plan.  It must preserve existing rechecks of lease/status/stage,
two completed ProviderCalls, two artifacts, score update, and successful
SCORING transition.  H2-C introduces no H2-specific path or SQLite writer.

## 8. Failure, retry, and crash semantics

An H2-C replay mismatch before minting uses exactly one:

```text
PipelineRepository.fail_job(job_id, owner=runtime_owner,
  error_code=ErrorCode.INVALID_RESPONSE,
  error_message="H2C_REPLAY_INVALID:<reason>", retry_at=None)
-> FAILED_FINAL -> StageDisposition.TERMINAL
```

There is no generic `_fail`, provider/Judge call, retry, persistence, or second
terminal transition.  The closed `<reason>` set is:

`LEASE_INVALID`, `PRIMARY_EVIDENCE_MISMATCH`, `PFE_INVALID`,
`FAILURE_CLASS_INELIGIBLE`, `RNI_MISMATCH`, `REPAIR_REQUEST_MISMATCH`,
`REPAIR_PAYLOAD_MISMATCH`, `REPAIR_RAW_INVALID`, `CANDIDATE_MISMATCH`,
`LANGUAGE_INVALID`, `DETERMINISTIC_GATE_INVALID`, `JUDGE_EVIDENCE_INVALID`,
`ATTESTATION_INVALID`, `FINALIZER_INVALID`, `TRUSTED_RESULT_MISMATCH`,
`STRUCTURED_RESULT_MISMATCH`, `SETTINGS_MISMATCH`, and
`PROVENANCE_MISMATCH`.

`RuntimeOperations.retry()` is narrowly extended to exclude a `FAILED_FINAL`
job when its code is `INVALID_RESPONSE` and its message is exactly one of the
above `H2C_REPLAY_INVALID:` literals.  This is a non-retryable trust-boundary
terminal; a matching string with another code has no effect, and existing
ordinary `INVALID_RESPONSE` manual retry behavior remains unchanged.  The
existing code-only exclusion for historical `CAPABILITY_UNAVAILABLE` remains
unchanged.

Crash before mint, and crash after mint but before `persist_success`, retain
no aggregate and must use the existing H1 interrupted-scoring/lease recovery
mapping to terminal `UNKNOWN_PROVIDER_STATE`; no restart reconstructs H2-C or
redispatches REPAIR/Judge.  Once `persist_success` starts, existing Phase G
PREWRITE/filesystem/SQLite crash semantics govern: promoted-but-unindexed
files are fail-closed orphan finals; an SQLite-complete graph follows existing
success behavior.  H2-C adds no recovery writer or retry.

An H2-C-enabled live full PASS never emits
`CAPABILITY_UNAVAILABLE/H2B_PASS_AWAITING_H2C`; it proceeds to persistence and
the existing `SUCCEEDED` state.  Historical records with that code/detail stay
terminal and manual-retry-excluded: no scan, revival, aggregate restoration,
or cache replay is authorized.

## 9. Required future RED tests

Tests must prove no public H2-C finalizer/verifier/mint API, no aggregate
ingress, no token/receipt/continuation/registry, and no caller invocation even
with a valid aggregate plus runtime object.  They must test constructed,
`object.__new__`, `object.__setattr__`, `model_construct`, copy/deepcopy,
pickle, subclass, and extra-attribute attacks.

The successful lexical test must demonstrate actual recomputation.  Mutate and
require rejection for PFE/failure class, RNI/JCS/hash, request/prompt/payload,
repair raw/extracted content/candidate/hash, language, quality input/gate,
Judge operation/H1/H2/raw/hash/length/evidence, attestation, finalizer result,
structured bytes/hash/length, and settings.  A transport spy must prove zero
`/api/tags` and zero `/api/generate` on both replay success and replay failure.
R1/R2 same-candidate substitution must reject.

Minting tests must show the valid lexical path produces exact
`PhaseHTrustedRepairSuccess`, while direct/forged values cannot bypass the
exact union plus revalidating PREWRITE.  Phase G tests must retain unmodified
PRIMARY `PhaseFTrustedScoringSuccess` persistence, accept valid REPAIR only
through `persist_success`, reject H2-B aggregate/wrong type/subclass/forged
repair success, prohibit alternate writers, preserve byte-for-byte structured
artifact equality, and preserve no-clobber/complete-graph idempotency.

## 10. Narrow future implementation scope

Authorized production scope only: `src/youtube_intel/runtime.py` (the lexical
replay, transition replacement, exact H2-C terminal and retry exclusion),
`src/youtube_intel/h2_evidence.py` (strict reconstruction/replay helpers only),
`src/youtube_intel/quality.py` (reuse/focused pure replay support only), and
`src/youtube_intel/scoring.py` (the exact repair success, exact union,
private repair verifier, and common-plan mapping).  Focused H2-C and Phase G
regression tests plus handoff evidence are allowed in a later implementation
authorization.

In `scoring.py`, allowed changes are limited to defining/importing the exact
repair success and evidence bundle, extending `persist_success`'s exact
accepted set, deriving the same private plan, and retaining every PRIMARY,
PREWRITE, write/promotion/fsync, and SQLite behavior.  Forbidden are a public
persistence method, caller scatter fields, H2-specific file/SQLite path,
bypass, or PRIMARY serializer change.

`state.py`, migrations, `domain.py`, provider transports, TASK-016B, and cache
remain frozen.  The provider/artifact audit above proves the existing schema
is sufficient, so no persistence-schema blocker exists.  Phase I cache and
recovery semantics are explicitly not activated.

## 11. Security-discretion audit

No executor discretion remains over H2-C ingress, replay ordering, fresh
reconstruction, network prohibition, PFE/RNI/raw/Judge/finalizer replay,
aggregate authority, trusted-success fields, exact Phase G union, ProviderCall
provenance, schema requirement, error detail, manual retry, crash behavior, or
historical CAPABILITY records.  Any proposed deviation is `DECISION NEEDED`.
