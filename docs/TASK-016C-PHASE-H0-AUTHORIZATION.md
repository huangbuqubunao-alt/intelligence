# TASK-016C Phase H0 — Trusted Scoring Recovery Authorization

## Status

`READY FOR PHASE H0 INDEPENDENT REVIEW`

This is a design authorization proposal only. It does not authorize Phase H
implementation, production changes, or runtime calls.

## 1. Frozen Phase G Contract

The accepted Phase G success path is frozen:

```text
PhaseFTrustedScoringSuccess
  -> TrustedPersistenceEntry.persist_success()
  -> PREWRITE_VALIDATE
  -> verified filesystem protocol
  -> SQLite atomic registration
```

Phase H must not weaken, bypass, duplicate, or reorder this boundary.

- `TrustedPersistenceEntry.persist_success()` remains the only trusted
  persistence ingress and the only owner of final-file promotion and scoring
  registration.
- There is no `persist_repair()`, repository repair-registration API,
  alternate SQLite writer, manual Artifact creation, or scatter-field
  score/stage write.
- `PREWRITE_VALIDATE` remains pure and zero-write. Before it passes, no
  Artifact, successful ProviderCall, response artifact ID, score, stage, tmp
  file, final file, or cache state may be created.
- An H reservation is a one-shot dispatch/budget ledger only. It is not a
  trusted result and cannot evidence provider success.

The existing exact `PhaseFTrustedScoringSuccess` PRIMARY behavior remains
unchanged. H2 may add only a private, exact-type repair verification branch
inside the existing entry; it may not add a second entry point.

## 2. Sealed Repair Persistence Bridge

```text
runtime-owned PRIMARY reservation
  -> received, known eligible PRIMARY failure
  -> runtime-owned REPAIR reservation
  -> exact RepairScoringAttempt (untrusted)
  -> schema -> frozen language validator -> deterministic quality gate
  -> REPAIR Judge PASS -> verified attestation -> TrustedScoringFinalizer
  -> PhaseHTrustedRepairSuccess (sealed, memory-only)
  -> TrustedPersistenceEntry.persist_success()
  -> unchanged PREWRITE_VALIDATE -> filesystem -> atomic SQLite registration
```

Only the runtime-private H2 repair seam may mint
`PhaseHTrustedRepairSuccess`. The provider supplies an untrusted repair raw
response and parser-derived candidate only; it cannot create a trusted result,
attestation, Artifact, ProviderCall completion, write plan, or persistence
capability.

`PhaseHTrustedRepairSuccess` is not a `PhaseFTrustedScoringSuccess`, and a
repair must never be converted to `PrimaryScoringAttempt`. This rejects a
fake-primary conversion. Bare `ScoreResult`, a single `TrustedScoreResult`,
mappings, JSON restores, legacy artifacts, cache payloads, and repository
records are likewise not repair persistence inputs.

### Capability and provenance

The repair success is an exact, private-sentinel-minted, immutable,
non-subclassable, non-copyable, non-deepcopyable, non-pickleable,
non-serializable, process-memory-only object. Its constructor is private to the
runtime-owned seam. It exposes no `from_*` factory and accepts no caller-supplied
authority, verifier, raw payload, identity, attestation, plan, Artifact,
ProviderCall, job, or filesystem field.

The entry must check exact capability identity before reading fields. It must
reject objects fabricated through `object.__new__`, proxy/subclass objects,
copied slots, mutated internals, `model_construct`, `model_copy`, mapping/JSON
restoration, or a self-consistent caller DTO.

The sealed bridge contains and cross-binds:

- original scoring request identity and normalized-input hash;
- distinct REPAIR provider-call identity and `attempt_role=REPAIR`;
- PRIMARY provider-call identity, primary raw-response hash, and the exact
  eligible-failure classification that permitted repair;
- exact repair raw response, repair raw hash, parser-derived candidate, and
  candidate hash;
- current provider/model/digest, prompt/schema, output language, and runtime
  `TrustedScoringContext` bindings;
- canonical scoring input, quality input, full REPAIR PASS result, REPAIR Judge
  operation, attestation, and sealed structured-result bytes/hashes; and
- the `TrustedScoreResult` returned only by `TrustedScoringFinalizer`.

`TrustedPersistenceEntry.persist_success()` remains the sole public method. Its
H2 private verifier accepts exactly either the existing PRIMARY aggregate or the
sealed repair aggregate. The repair branch creates its write plan internally
only after all bindings are revalidated. No caller can provide replacement
fields or a replacement plan.

## 3. Identity, Reservation, and Budget Protocol

| Role | Identity | Limit | Durable source |
|---|---|---:|---|
| PRIMARY scoring | Existing `build_scoring_request_identity()` request hash | 1 | One `ProviderCall` identity |
| REPAIR scoring | `build_provider_request_hash()` over canonical REPAIR operation input: original request identity, primary raw hash, REPAIR prompt/schema, provider/model/digest, output language | 1 | One distinct `ProviderCall` identity |
| PRIMARY Judge | Existing H1/H2 derivation with `attempt_role=PRIMARY` | 1 | One distinct `ProviderCall` identity |
| REPAIR Judge | Existing H1/H2 derivation with `attempt_role=REPAIR` | 1 | One distinct `ProviderCall` identity |

Judge identities retain the frozen two-layer contract:

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

`attempt_role` makes PRIMARY and REPAIR Judge identities distinct. H1 is not a
ProviderCall key and must never substitute for H2.

The existing unique `provider_calls.request_hash` is the durable one-shot
ledger. H1 uses runtime-private orchestration around existing generic
ProviderCall primitives; it adds no public repository scoring/repair API,
table, field, migration, or cache record, and never uses generic retry/takeover
behavior for these identities.

Before dispatch, the runtime reads the exact identity. Only a missing row may
be reserved. Every other state blocks automatic dispatch:

| Existing state | H action |
|---|---|
| `PENDING` (live or expired) | Unknown; stop and fail closed |
| `SUCCEEDED` | Consumed; do not dispatch |
| `FAILED_FINAL` | Consumed; do not dispatch |
| `FAILED_RETRYABLE` | Consumed for H; do not take over or dispatch |
| mismatched/legacy identity | Integrity failure; stop |

This gives PRIMARY <= 1, REPAIR <= 1, PRIMARY Judge <= 1, REPAIR Judge <= 1,
and Judge total <= 2, including after restart.

## 4. Unknown Provider State

Once a reservation exists, the process cannot prove whether an external request
was delivered. An unknown state is therefore never a retry or cache miss.

| Event | State retained | Required behavior |
|---|---|---|
| Request sent; response missing | `PENDING` / unknown | Stop; no resend |
| Timeout | `PENDING` / unknown | Stop; no resend |
| Crash during scoring or Judge call | `PENDING` / unknown | Stop; no resend |
| Restart finds any `PENDING` | Unknown | Classify only; no takeover or provider/Judge call |

A known invalid PRIMARY response may start one REPAIR only while its exact raw
response remains in the same process memory. After restart, no artifact,
caller payload, cache record, or reconstructed raw input may launch repair.
This availability tradeoff preserves one-shot accounting and provenance.

## 5. H3 Crash and Orphan-Final Recovery

H3 recovers previously written final files only. It is not cache recovery and
never calls a scoring provider or Judge.

Filesystem presence alone is insufficient. Before registration, recovery
requires all of:

1. matching DB/job identity and an atomic, runtime-owned recovery claim;
2. matching scoring and Judge ProviderCall identities and role-appropriate
   statuses;
3. canonical raw-envelope and structured-result reconstruction, hashes,
   lengths, metadata, current context, quality result, and attestation checks;
4. controlled regular-file/path verification for both promoted finals; and
5. exact complete-graph equality, or a transactionally provable absent/eligible
   registration state.

Only then may the runtime reconstruct the sealed success in memory and invoke
the same `TrustedPersistenceEntry.persist_success()` path. Claim and
registration are atomic; a losing claimant makes no writes or external calls.

| State | H3 disposition |
|---|---|
| Controlled current-operation tmp | Verify ownership/path/type; clean only that tmp |
| Complete verified PRIMARY orphan finals with DB/provider evidence | Recover through the sole entry |
| Exact complete committed graph | Idempotent success; no new calls or writes |
| Missing final, hash/path/type/version mismatch, symlink, authority rotation, conflicting graph, or legacy payload | Reject and quarantine |
| REPAIR orphan without independently re-provable primary-origin evidence | Quarantine; never auto-recover |
| Expired `PENDING` without a complete verified eligible final pair | Quarantine and fail closed |

Quarantine leaves existing finals untouched, excludes them from normal work and
any cache interpretation, and emits only safe diagnostic evidence. It does not
delete, overwrite, promote, or convert finals into Artifacts.

## 6. H1/H2/H3 Scope Boundaries

### H1 — identity, reservation, and budget

Allowed: `src/youtube_intel/scoring.py`, `src/youtube_intel/runtime.py`, and
new focused H1 tests.

Forbidden: `TrustedPersistenceEntry` semantics, filesystem protocol, Artifact
creation, score/stage completion, provider repair dispatch, schema/migration,
dependencies/lockfiles, cache behavior, and public repository APIs.

Acceptance: exact identities; duplicate/concurrent reservation prevention;
every existing state blocks dispatch; restart and unknown-state tests prove no
second external call.

### H2 — sealed repair trusted flow

Allowed: `src/youtube_intel/providers/ollama.py`, `src/youtube_intel/scoring.py`,
`src/youtube_intel/runtime.py`, focused quality support only if necessary, and
focused H2/Phase G regression tests.

Forbidden: `persist_repair`, alternate writer, repository repair API, manual
Artifact/ProviderCall completion, fake-primary conversion, bare `ScoreResult`,
schema/migration, dependencies/lockfiles, cache recovery, or external-network
tests.

Acceptance: only the runtime seam mints repair success; each repair re-runs
schema/language/quality/Finalizer validation; REPAIR provenance and Judge
identity are distinct; existing PRIMARY entry behavior is unchanged.

### H3 — orphan/crash recovery

Allowed: `src/youtube_intel/runtime.py`, `src/youtube_intel/scoring.py`, and a
narrow private `state.py` recovery-claim helper only if required for atomic
claim; focused H3 tests.

Forbidden: public repository APIs, provider/Judge calls, cache recovery/hits,
schema/migration, deleting or overwriting finals, new persistence ingresses, and
changes to the frozen PRIMARY PREWRITE contract.

Acceptance: recovery requires DB identity, provider identity, canonical hashes,
final-file verification, and an atomic claim; valid primary orphan recovery is
idempotent; partial, unknown, conflicting, legacy, and non-reproducible repair
states quarantine fail closed.

## 7. Independent Review Gate

Approve H1 only if the reviewer confirms:

- Phase G retains one persistence ingress and no new writer or repository
  scoring API is introduced.
- The H1 ledger cannot dispatch an identity more than once.
- `PENDING`, unknown, successful, failed, and conflicting identities all block
  automatic dispatch.
- H1 creates no trusted success, Artifact, final file, cache hit, or stage
  completion.

Request changes if the proposal relies on a caller-supplied verifier/token/flag,
manual success Artifact creation, fake PRIMARY conversion, bare `ScoreResult`,
or an unauthorized change to `TrustedPersistenceEntry` semantics.
