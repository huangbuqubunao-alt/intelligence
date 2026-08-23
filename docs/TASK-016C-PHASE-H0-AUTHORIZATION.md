# TASK-016C Phase H0 — Trusted Scoring Recovery Authorization

## Status

`READY FOR PHASE H0 INDEPENDENT REVIEW`

This is an authorization proposal, not implementation authority. It does not
authorize H1, production-code changes, runtime calls, or a cache design.

## 1. Frozen Phase G Contract

The accepted success path remains frozen:

```text
PhaseFTrustedScoringSuccess
  -> TrustedPersistenceEntry.persist_success()
  -> PREWRITE_VALIDATE
  -> verified filesystem protocol
  -> SQLite atomic registration
```

Phase H must not weaken, bypass, duplicate, or reorder it.

- `TrustedPersistenceEntry.persist_success()` remains the only persistence
  ingress and the sole owner of final-file promotion and scoring registration.
- There is no `persist_repair()`, repository repair API, alternate SQLite
  writer, manual Artifact creation, or scatter-field persistence.
- `PREWRITE_VALIDATE` stays pure and zero-write: no ProviderCall, Artifact,
  response artifact ID, score/stage write, tmp/final file, or cache state may
  exist before it succeeds.
- The existing PRIMARY `PhaseFTrustedScoringSuccess` case is unchanged.

### H1 reservation is local, not durable

H1 may create a runtime-local, process-memory, non-serializable admission
reservation. It is consumed before an external attempt and enforces the
one-shot budget within that runtime only. It must not write a `ProviderCall`,
Artifact, database row, filesystem object, cache object, or stage result.

Runtime-local admission is necessary but insufficient. Every PRIMARY, REPAIR,
and Judge dispatch additionally requires all three current-job facts:

- a verified active `SCORING` job lease;
- ownership of that job's current execution claim; and
- proof that no competing active claimant owns the same execution.

The job lease and execution claim are the durable cross-runtime coordination
boundary. They authorize dispatch ownership only; they are not ProviderCall
success evidence and cannot create a trusted persistence input.

A durable ProviderCall identity exists only when
`TrustedPersistenceEntry.persist_success()` completes its frozen persistence
protocol. H1 therefore cannot reintroduce the pre-PREWRITE durable reservation
forbidden by Phase G.

If the process crashes or loses a provider response, the local reservation is
lost but the scoring job is classified as `UNKNOWN_PROVIDER_STATE` on recovery
and becomes terminal/fail-closed. It is never re-dispatched merely because no
ProviderCall was persisted. This deliberately sacrifices availability to retain
at-most-once provider behavior.

### Recovery ordering for interrupted SCORING work

Expired or interrupted `SCORING` jobs must be atomically classified and
finalized fail-closed **before** generic reclaim, retry activation, or another
runtime can claim them. The recovery transaction compares the expired lease and
current claim, inspects the frozen job/error and ProviderCall facts, then writes
the existing terminal job/error representation in one transition.

There is no intermediate reclaimable or retryable state. A generic recovery
worker that loses this compare-and-finalize race re-reads the terminal or
already-complete graph and must not claim or dispatch scoring work.

## 2. Sealed Repair Persistence Bridge

```text
runtime-local PRIMARY admission
  -> received, known eligible PRIMARY failure
  -> runtime-local REPAIR admission
  -> exact RepairScoringAttempt (untrusted)
  -> schema -> frozen language validator -> deterministic quality gate
  -> REPAIR Judge PASS -> closure-owned TrustedScoringFinalizer
  -> PhaseHTrustedRepairSuccess (sealed, memory-only)
  -> TrustedPersistenceEntry.persist_success()
  -> unchanged PREWRITE_VALIDATE -> filesystem -> atomic SQLite registration
```

The provider supplies only an untrusted repair raw response and parser-derived
candidate. It cannot make a trusted result, attestation, Artifact, ProviderCall
completion, write plan, or persistence capability.

`PhaseHTrustedRepairSuccess` is not a
`PhaseFTrustedScoringSuccess`, and a repair must never be converted to
`PrimaryScoringAttempt`. This rejects fake-primary conversion. Bare
`ScoreResult`, individual `TrustedScoreResult`, mappings, JSON restores,
legacy artifacts, cache payloads, and repository records are not repair
persistence inputs.

### Runtime-owned repair capability verification

Type checks, sentinel flags, registries, and caller-provided validators are not
authorization. The sealed repair bridge is a runtime-owned lexical continuation:

1. `RuntimeOperations` creates the repair mint path and the persistence entry
   together from its validated config, context, quality authority, job scope,
   and finalizer closure.
2. The repair path re-derives every identity and invokes the closure-owned
   `TrustedScoringFinalizer`; it does not accept a caller result, validator,
   attestation, identity, raw payload, or plan.
3. The repaired result is consumed immediately by the same runtime closure via
   the existing `persist_success()` ingress. It is not a transferable public
   credential and exposes no public field/factory from which persistence input
   can be rebuilt.
4. `object.__new__` creates no accepted continuation: a forged shell cannot
   invoke the closure-owned finalizer or supply the closure's re-derived
   identity/evidence. Copy, deepcopy, pickle, JSON serialization, and restore
   are rejected before evidence exposure.

The repair continuation must be immutable, non-subclassable, non-copyable,
non-serializable, and process-memory-only. These properties are defense in
depth; acceptance comes from closure-owned re-derivation, not object type or a
stored flag.

The continuation binds, without caller-supplied fields:

- original scoring request and normalized-input identities;
- canonical REPAIR operation identity and `attempt_role=REPAIR`;
- primary failure identity/classification and primary exact raw hash;
- repair exact raw hash, same-parser candidate, and candidate hash;
- current scoring provider/model/digest, repair prompt/schema/version, output
  language, and runtime `TrustedScoringContext`;
- canonical scoring/quality inputs, full REPAIR PASS result, REPAIR Judge
  operation/attestation, and sealed structured-result bytes/hashes; and
- only the `TrustedScoreResult` returned by the closure-owned Finalizer.

The entry may have an H2-private repair verifier, but it remains an internal
branch of the existing `persist_success()` call. It creates the write plan only
after full revalidation and exposes no alternate ingress.

## 3. Frozen Identity and Budget Protocol

### PRIMARY and REPAIR identities

PRIMARY retains the existing
`build_scoring_request_identity()` request hash.

REPAIR has a distinct canonical operation input, serialized with the project's
canonical JSON rules:

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

Its normalized-input hash is the SHA-256 of that validated canonical operation
input. Its ProviderCall-style request identity is derived only through the
existing `build_provider_request_hash()` six-dimensional builder. The repair
result still binds the original scoring request hash; it must never substitute
the REPAIR transport identity for the scoring-result identity.

`primary_failure_class` is a closed runtime-derived enum:
`SCHEMA_OR_PARSE_INVALID`, `LANGUAGE_INVALID`,
`DETERMINISTIC_QUALITY_REJECT`, `JUDGE_REJECT`, or
`JUDGE_UNCERTAIN`. Unknown transport, timeout, authority/context mismatch,
and configuration failures are ineligible for repair.

### Judge identity

PRIMARY and REPAIR Judge calls retain the existing two-layer contract:

```text
H1 = SHA256(canonical_json(validated QualityJudgeOperationInput))
H2 = build_provider_request_hash(
       operation="local-content-quality-v1",
       normalized_input_hash=H1,
       provider=current_judge_provider,
       model=current_judge_model,
       prompt_version=current_quality_prompt_version,
       schema_version=current_quality_schema_version,
     )
```

`QualityJudgeOperationInput.attempt_role` is `PRIMARY` or `REPAIR`;
therefore their H1 and H2 values are distinct. H1 is never a ProviderCall key
and cannot replace H2.

### Limits, crash behavior, and duplicate prevention

| Role | Limit | Prevention |
|---|---:|---|
| PRIMARY scoring | <= 1 | Runtime-local admission consumes the role once |
| REPAIR scoring | <= 1 | Runtime-local admission requires an eligible PRIMARY failure |
| PRIMARY Judge | <= 1 | Runtime-local role budget |
| REPAIR Judge | <= 1 | Runtime-local role budget; total Judge <= 2 |

The local admission state is never restored after crash. Any expired or
interrupted scoring-stage job is terminal `UNKNOWN_PROVIDER_STATE`; restart
does not produce another PRIMARY, REPAIR, or Judge call.

Persisted ProviderCall states can arise only from the atomic trusted commit and
are never dispatch authority. On observation, every one fails closed:

| State | H action |
|---|---|
| missing after an interrupted run | Treat job as unknown; no dispatch |
| `PENDING` | Unknown/conflict; no dispatch or takeover |
| `SUCCEEDED` | Already committed or integrity conflict; no dispatch |
| `FAILED_FINAL` / `FAILED_RETRYABLE` | Consumed/conflict; no dispatch |
| mismatched or legacy record | Integrity failure; no dispatch |

A repeated call after an already complete trusted commit may be accepted only by
the existing entry's complete-graph idempotency check. It performs no provider
or Judge call and creates no duplicate registration.

## 4. Unknown Provider State

A sent request with a missing response, timeout, or crash during scoring/Judge
work is unknowable: the provider may have acted. H treats each as terminal
`UNKNOWN_PROVIDER_STATE`.

`UNKNOWN_PROVIDER_STATE` is a runtime recovery classification, not a new DB
enum, ProviderCall status, table, field, or schema migration. It is derived
only from the frozen existing contracts: an interrupted/expired `SCORING` job
lease and execution claim, its terminal-or-incomplete job/error record, and
any corresponding ProviderCall state. It is represented through the existing
non-retryable job/error transition with a stable safe diagnostic.

It never triggers retry, never permits duplicate dispatch, and never becomes
success. Only an already complete verified trusted persistence graph may be
reported as idempotent completion; that is not an UNKNOWN-to-success conversion.

- No retry, takeover, cache miss, raw reconstruction, or repair follows.
- A repair is permitted only after a received, in-memory, eligible PRIMARY
  failure while the same runtime-local budget remains live.
- On restart, the scoring job is finalized as unknown before normal retry
  dispatch can execute.
- Existing generic retry policies must not be used for Phase H scoring/Judge
  identities.

## 5. H3 Crash and Orphan-Final Recovery

Filesystem presence alone never establishes trust. H3 is not cache recovery and
never calls a provider or Judge.

Promoted orphan finals with no durable non-filesystem proof are quarantined.
They cannot create a ProviderCall, Artifact, score, stage completion, or a new
trusted success.

Recovery is permitted only when all evidence is already present:

1. DB-attested job/operation identity and a successful atomic recovery claim;
2. DB-attested scoring and Judge provider identities, compatible statuses, and
   response-artifact bindings;
3. canonical raw-envelope and structured-result reconstruction; current
   context/authority, PASS result, attestation, length, hash, metadata, and
   cross-binding verification; and
4. controlled regular-file/path verification for both final files.

A successful claim must atomically establish that the complete graph equals the
same verified evidence. A losing claimant does no write and no external call.
If the DB identity is absent, partial, legacy, conflicting, or mismatched, H3
quarantines even perfectly formed files.

| State | H3 disposition |
|---|---|
| Controlled current-operation tmp | Verify ownership/path/type; clean only that tmp |
| Verified finals but no DB-attested identity | Quarantine |
| DB identity plus verified files and canonical proof | Atomic idempotent recovery only |
| Exact complete committed graph | Idempotent success; no new calls or writes |
| Partial/mismatched files or DB, symlink, rotated authority, legacy payload, expired/unknown state | Quarantine and fail closed |
| REPAIR orphan lacking every DB-attested primary-failure binding | Quarantine; never auto-recover |

Quarantine leaves finals untouched, excludes them from normal work and any cache
interpretation, and emits safe diagnostics only. It never deletes, overwrites,
promotes, or converts files into Artifacts.

## 6. H1/H2/H3 Scope Boundaries

### H1 — local identity, admission, budget, and unknown-state stop

Allowed: runtime-local identity/admission code, existing job lease/claim and
unknown-state recovery wiring, and focused H1 tests. A narrow job-recovery
change is allowed only to atomically finalize expired/interrupted SCORING work
as unknown before generic reclaim, retry activation, or a new claim.

Forbidden: durable ProviderCall reservation before PREWRITE, changes to
`TrustedPersistenceEntry`, filesystem/Artifact writes, score/stage success,
provider repair dispatch, repository writer/API, schema/migration,
dependencies/lockfiles, and cache behavior.

Acceptance: no pre-PREWRITE durable persistence; PRIMARY <= 1, REPAIR <= 1,
Judge <= 2 per runtime; every timeout/crash/restart path blocks re-dispatch;
each dispatch proves an active owned SCORING lease and no competing claimant.

### H2 — sealed repair trusted flow

Allowed: repair transport/parser contract, runtime-owned repair seam, the
strictly private repair verifier inside the existing persistence entry, and
focused H2/Phase G regression tests.

Forbidden: `persist_repair`, alternate writer, repository repair API, manual
Artifact/ProviderCall completion, fake-primary conversion, bare `ScoreResult`,
schema/migration, dependencies/lockfiles, cache recovery, and external-network
tests.

Acceptance: only the runtime closure can consume a repair continuation; each
repair re-runs schema/language/quality/Finalizer validation; identity and
provenance are role-distinct; PRIMARY behavior remains unchanged.

### H3 — DB-attested orphan/crash classification

Allowed: recovery classification, final-file verification, atomic recovery
claim, and focused H3 tests.

Forbidden: filesystem-only recovery, provider/Judge calls, cache recovery/hits,
new persistence ingress, repository writer/API, schema/migration, or deletion
or overwrite of final files.

Acceptance: only DB-attested identity plus verified canonical files can recover;
all filesystem-only, partial, unknown, conflicting, legacy, and
non-reproducible repair states quarantine fail closed.

## 7. Independent Review Gate

Approve H1 only if the reviewer confirms:

- H1 has no durable ProviderCall reservation or any other PREWRITE persistence.
- Every dispatch requires an active owned SCORING lease and no competing active
  claimant; expired/interrupted SCORING work is finalized before reclaim/retry.
- `TrustedPersistenceEntry.persist_success()` remains the sole ingress; there
  is no repair API, repository writer, alternate SQLite writer, or scatter
  persistence.
- Capability acceptance relies on runtime closure-owned re-derivation and
  Finalizer acceptance, not type/sentinel/registry/caller validation.
- PRIMARY <= 1, REPAIR <= 1, and Judge <= 2 hold for normal, timeout, crash,
  and restart paths.
- `UNKNOWN_PROVIDER_STATE` is derived without a schema migration and is never
  retryable, dispatchable, or successful.
- Filesystem-only orphan finals are always quarantined.

Request changes if any implementation retries unknown provider state, promotes a
repair to PRIMARY, treats a missing ProviderCall as permission to retry, trusts
filesystem alone, or accepts caller-created repair material.
