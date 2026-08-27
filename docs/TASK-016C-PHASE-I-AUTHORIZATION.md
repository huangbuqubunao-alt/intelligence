# TASK-016C Phase I — Cache Hardening, Live Same-Job Recovery, and Reuse Boundary

## Status and purpose

Status: **DESIGN DRAFT — READY FOR INDEPENDENT REVIEW; IMPLEMENTATION IS NOT
AUTHORIZED.** This document does not authorize a source, test, migration,
dependency, lockfile, provider, network, merge, push, tag, rebase, or squash
change. It is subordinate to the closed H1, H2-A, H2-B, H2-C, and Phase G
contracts recorded in `handoffs/TASK-016C.md`.

Phase I is the smallest useful hardening phase: it may add a **live,
same-job, fully revalidated reuse path for REPAIR/Judge evidence and a
pre-persistence H2-C graph**. It may skip an otherwise duplicate REPAIR or
Judge network dispatch only after that proof. It does not create a general
cache, a cross-job cache, a PRIMARY cache contract, a restart/resurrection
mechanism, or a new lineage generation.

Reuse decision: **DIRECT**. The implementation must reuse the existing sealed
H2-C semantic objects and derivations, `build_provider_request_hash`,
`build_judge_h1_h2`, H2 Canonical JSON, `RepairPersistenceGraphIdentityV2`,
the H1 admission/lease checks, Phase G persistence checks, SQLite v2, and the
hardened artifact helpers. No third-party component is permitted.

The governing rule is unchanged:

```text
sealed semantic inputs
  -> canonical deterministic derivation
  -> derived request/hash identities
  -> validation of duplicated evidence claims
  -> validation of persisted ProviderCall identities
  -> verified P/R/J/E/S/G
  -> trusted persistence/read
```

A cache hit, Artifact row, file, `request_hash`, ProviderCall row, Judge
response, G value, or serialized trusted-success-shaped value is evidence only;
none is authority by itself.

## 1. Existing-state inventory

The following is an audit of the frozen implementation, not a claim that each
mechanism is authorized for Phase I reuse.

| Class | Current mechanism and location | Key/scope/lifetime | Trust, owner, and failure behavior |
|---|---|---|---|
| A: persistence idempotency | `TrustedPersistenceEntry._check_committed_graph()` and `_committed_lineage_graph_matches()` in `scoring.py` | Exact planned raw/structured artifacts, ProviderCalls, Video, and Job; process-independent; same producing job | Compares the complete graph before returning an existing commit; mismatch fails closed. Mutation/persistence is lease-bound. It is not a semantic execution cache. |
| A: repair orphan adoption | H2-C/Phase G PREWRITE and orphan reconciliation in `scoring.py` | Exact deterministic P/G final paths and exact plan | Only the exact no-clobber, hash-verified, indexed plan is adopted; partial/mismatched files fail closed. |
| A: ProviderCall ledger | `SQLiteStateRepository.reserve_provider_call()`, `complete_provider_call()`, and `fail_provider_call()` in `state.py` | Globally unique `request_hash`; durable, cross-process | It verifies request fields on collision and handles `PENDING`, retryable, succeeded, and final rows. It is a dispatch ledger/result pointer, not authority. The key itself has no Job column. |
| B: legacy PRIMARY semantic cache | `RepositoryBackedScoringService._score()` and `_load_verified_cached_result()` in `scoring.py` | PRIMARY request hash plus `scoring/<hash>/raw|structured`; durable; effectively cross-process and potentially cross-job | Reads bytes, hashes, result provenance, artifact `video_id`, and ProviderCall fields. It does not establish the Phase I same-job contract and is explicitly out of Phase I scope. |
| C: PRIMARY received-raw recovery | `_persist_recovery_primary_response()` and `_load_verified_recovery_raw_response()` in `scoring.py` | `scoring/<request_hash>/recovery/raw`; durable recovery Artifact, existing job/video binding | A retryable ProviderCall marker can cause raw response re-parse rather than another provider call. It validates metadata/hash/expiry, but is not an H2-C continuation authorization. |
| C/D: provider reservation takeover | `reserve_provider_call()` in `state.py` | `request_hash`, ProviderCall lease/availability | Expired or retryable reservation can be taken over; a verified deterministic Artifact can mark a row succeeded. This is state-store recovery/deduplication, not semantic authority. |
| C/D: job reclaim/retry | `SQLiteStateRepository.reclaim_expired_jobs()` and `RuntimeOperations.retry()` | Job lease/status/error code; durable, cross-process | Non-SCORING expired work follows generic reclaim. Expired SCORING becomes `UNKNOWN_PROVIDER_STATE` / `FAILED_FINAL`; runtime retry excludes capability and trust-integrity terminals. |
| Read verification | `AuthoritativeScoringReader` in `scoring.py`; runtime/reporting consumers call it | Video authoritative pointer -> exact Job -> exact structured Artifact | Reads verify the selected graph, including v1 first classification and H2-C R/J/G rederivation. It is not a mutable cache manager. |
| Provider-local caches | `providers/subtitles.py`, `transcripts.py`, and provider adapters | Provider-specific request/response handling only | No Phase I scoring reuse authority is derived from those adapter-local results. They remain outside this authorization. |

`pipeline.py` supplies ErrorCode-based retry scheduling and lease-owned
`fail_job`; `jobs.py` supplies scheduling/re-entry but no separate scoring
semantic cache. `reporting.py` has no authority cache: it must consume a
verified scoring read. `h2_evidence.py` contains the sealed evidence and
canonical derivations, not a cache.

Terminology is normative:

- **Persistence idempotency** repeats the same already-planned durable commit.
- **Semantic reuse** avoids a provider dispatch after fresh proof from roots.
- **Crash recovery** resolves an interrupted durable transition without
  inferring an unknown external outcome.
- **Retry** creates/schedules permitted work by ErrorCode; it is not reuse.

## 2. Threat model and non-goals

In scope: arbitrary same-process callers outside the inherited trusted-success
assumption; stale runtime owners; expired leases; corrupt/malicious SQLite rows
or filesystem artifacts; symlink/FIFO/device/socket/directory replacement;
stale ProviderCalls; request-hash collisions or equal hashes with differing
identity claims; stale model/digest/prompt/schema/policy/settings; graph or
artifact from another Job/Video; partial graph; DB/file orphan split; write
between filesystem and SQLite; pre-v2, legacy, and unknown future generations;
and cache poisoning/replay.

Out of scope: changing the inherited same-process trusted-success minting
assumption; resolving an external dispatch whose outcome is unknown; cross-job
deduplication; PRIMARY cache redesign; model/provider-local cache policy;
schema v3; scoring rerun; terminal Job resurrection; changing H1 admission,
H2-B repair control flow, H2-C replay, Phase G semantics, the ten ErrorCodes,
or the reader's authority role.

## 3. Exact policy decisions

| Decision | Phase I answer |
|---|---|
| Cross-job reuse | **NO.** Equal P/R/J/G/hash never permits sharing between Jobs. Any proposal requires a separate trust contract and authorization. |
| Expired SCORING recovery | **NO.** H1 reclaim remains `UNKNOWN_PROVIDER_STATE` -> `FAILED_FINAL`; cached evidence cannot resolve dispatch ambiguity. |
| Terminal Job resurrection | **NO.** A successful/failed terminal job is never resumed or rewritten by cache state. |
| Provider cache network skip | **YES, REPAIR only**, after section 7's complete same-job proof. PRIMARY is not authorized. |
| Judge cache network skip | **YES, REPAIR_JUDGE only**, after section 8's complete same-job proof. |
| Complete H2-C graph skip | **YES**, only before Phase G durable completion, for the exact live same Job and after section 9's full revalidation. |
| Valid owner/lease | Required for every reuse that can lead to provider-dispatch suppression, admission consumption, persistence, terminalization, or Job mutation. Read-only diagnostic verification does not require it and must not mutate. |
| Migration 003 | **NO.** Existing schema v2 is sufficient; a durable cache index/state would be a separate authorization blocker. |
| New ErrorCode | **NO.** Existing `TRUST_INTEGRITY_INVALID`, `UNKNOWN_PROVIDER_STATE`, and normal ErrorCode retry policy remain sufficient. |
| Reader change | **NO semantic change.** It remains the sole read verifier; Phase I may only reuse its verification logic/hardened reader primitives without adding a cache bypass. |
| Phase G/lineage | **NO semantic or schema change.** Phase G still receives only a runtime-minted trusted success after proof; v1/legacy rules are unchanged. |

## 4. Cacheable units and boundaries

| Candidate unit | Phase I disposition | Canonical identity and proof | Network / scope |
|---|---|---|---|
| PRIMARY raw response, candidate, deterministic quality, Judge, trusted ScoreResult | **NOT CACHEABLE in Phase I** | Existing PRIMARY behavior is inventory only; no new PRIMARY reuse contract | No new skip; same/cross-job authorization absent |
| REPAIR provider raw response | **AUTHORIZED FOR REUSE** | Rederive sealed RNI -> normalized hash -> R; verify exact R ProviderCall and raw envelope artifact | Skip REPAIR network only; same Job, valid lease, cross-process permitted |
| REPAIR candidate | **REVALIDATE-ONLY** | Reparse verified raw and recompute candidate hash/language/gate | Never independently reused |
| REPAIR Judge response | **AUTHORIZED FOR REUSE** | Rederive sealed `QualityJudgeOperationInput` -> H1/H2 J; verify exact JudgeEvidence, Judge ProviderCall, and same raw envelope | Skip Judge network only; same Job, valid lease, cross-process permitted |
| `RepairCompositeEnvelope` raw bytes | **REVALIDATE-ONLY** | Strict H2-JCS parse/reserialize, byte hash/length, all P/R/J/E claims and roots | No authority or standalone skip |
| finalizer structured bytes | **REVALIDATE-ONLY** | Exact sealed bytes/hash/length plus independently rerun finalizer | No standalone skip |
| complete repair graph G | **AUTHORIZED FOR REUSE** | All section 9 proof, then recompute G exactly | Skip both repair execution contacts; same Job only |
| `VerifiedScoringRead` | **NOT CACHEABLE as authority** | It is a runtime read conclusion; reread through `AuthoritativeScoringReader` | Downstream never consumes a cached substitute |
| ProviderCall record | **REVALIDATE-ONLY evidence** | Exact sealed-derived request identity, `SUCCEEDED`, response Artifact ID | Never unilateral authority; PENDING/unknown never successful |
| normalized semantic inputs/settings provenance | **REVALIDATE-ONLY roots** | Rebuild from runtime-owned current input/settings; compare sealed commitments | Mutable configuration causes miss/fail-closed as stated below |

The Phase I cache key is not a new database key. It is the exact existing
identity tuple, used only after runtime recomputation:

```text
REPAIR: (job_id, video_id, pipeline_version, lineage=v1,
         sealed RNI -> normalized_input_hash, operation, provider, model,
         model_digest, prompt_version, schema_version, payload hash/length,
         settings_provenance_sha256) -> R
JUDGE:  (job_id, video_id, pipeline_version, lineage=v1,
         sealed QualityJudgeOperationInput -> H1, operation, provider, model,
         model_digest, policy/prompt/schema versions, settings provenance) -> J=H2
GRAPH:  (job_id, video_id, P, R, J, settings_provenance_sha256, E, S,
         producer versions, graph/envelope schemas) -> G
```

SHA-256 collision resistance is assumed. `job_id`/`video_id`/generation and
settings bindings are mandatory scope guards even where R/J/G already
semantically bind some of them. Filename, timestamps, latest rows, model name,
or prompt text alone are never cache keys.

## 5. Live, expired, and terminal policy

Only a live runtime may attempt Phase I reuse. Before every mutable reuse path
it must reread the Job and require exactly: same `job_id`, same `video_id`,
`VIDEO_STAGE`, `SCORING`, `RUNNING`, same runtime owner, active unexpired
lease, expected pipeline version, and `scoring_lineage_version` exactly v1.
The runtime must rebuild current input/settings before any ProviderCall or file
is accepted.

If the owner/lease is stale at any point, Phase I performs no mutation,
dispatch, adoption, or `fail_job`. It returns the existing stale-lease route.
If integrity failure is found while the owner/lease is still reproven current,
the existing H2-C integrity terminalization path and its existing closed
diagnostic vocabulary apply; if it cannot reprove the lease, it must not
terminalize. An expired job remains H1's `UNKNOWN_PROVIDER_STATE` terminal;
no Phase I lookup runs before reclaim's generation/state classification.

## 6. Settings and version invalidation

The runtime must rebuild and compare the full H2-C settings provenance before
reuse: provider/base URL, model and model digest, temperature, max tokens,
transcript/description limits, output language, threshold, operations, prompt
and schema versions, frozen format/body hash and length where applicable,
quality policy/prompt/schema, Judge provider/model/digest, and language
validator contract. A mismatch is an authorization miss: it must not accept
the old evidence. For a live owned job it follows the existing normal dispatch
or existing fail-closed path dictated by the H1/H2-B state; it never rekeys or
mutates old evidence to fit new settings.

`scoring_lineage_version`, evidence schema, envelope schema, graph schema,
producer versions, prompt versions, and policy versions are exact equality
checks. Pre-v2/NULL and unknown future generations are not Phase I cache hits.
Unknown versions fail closed; known but unequal identity-bearing versions are
misses only where normal live execution can safely create a new exact evidence
path. A v1 Job is classified before any legacy lookup, so it can never
downgrade to legacy.

## 7. REPAIR provider-reuse contract

A REPAIR raw hit may skip `/api/generate` only after all of these conditions:

1. Section 5's live Job/lease proof succeeds.
2. The runtime reconstructs the original validated `ScoringInput`,
   `PrimaryTrustedContext`, eligible `PrimaryFailureEvidence`, current validated
   settings, and sealed `RepairNormalizedInput`; it recomputes canonical RNI
   bytes/hash, exact payload bytes/hash/length, and R.
3. It rejects any evidence duplicate that disagrees with the sealed RNI:
   operation, provider, model, model digest, prompt/schema, language,
   temperature, and limits.
4. The R ProviderCall is present and exactly `SUCCEEDED`, has the sealed-derived
   operation/provider/model/prompt/schema/R, and points to the expected raw
   Artifact ID. `PENDING`, retryable, final failed, missing, or mismatched rows
   are never hits.
5. The raw Artifact is exact P/G path/key, same Job/Video, correct kind,
   producer/version/retention metadata, regular/no-follow/nonblocking-open
   verified, bounded, exact hash/length verified, strict UTF-8/H2-JCS parsed,
   and canonical-reserialized.
6. The raw replay produces the exact candidate, candidate hash, language PASS,
   deterministic gate PASS, and the exact expected REPAIR evidence.

The cache may cross a process boundary only because all proof is durable and
freshly recomputed. It may not cross a Job boundary. A proof failure is not a
fallback to trusting the file or row; it follows the partial-cache matrix.

## 8. REPAIR Judge-reuse contract

A REPAIR Judge hit may skip its network dispatch only after section 7's
preconditions through candidate/gate verification plus all of these:

1. Rebuild the sealed `QualityJudgeOperationInput` from runtime roots and the
   freshly revalidated candidate; derive H1 and J/H2 with `build_judge_h1_h2`.
2. Treat stored H1/H2 and JudgeEvidence metadata as claims: compare every
   operation/provider/model/digest/policy/prompt/schema/candidate/input/hash
   field to the sealed-derived truth.
3. Require the J ProviderCall to be exactly `SUCCEEDED`, exactly match the
   sealed-derived Judge request, and point at the same verified raw envelope
   Artifact ID. A successful R row cannot stand in for J.
4. Strictly replay the captured Judge response and require the frozen PASS
   semantics and exact QualityPassAttestation before finalization.

No stored Judge H1/H2, JudgeEvidence model, or successful ProviderCall is a
request-identity truth source. Failure never downgrades to `JUDGE_UNCERTAIN`.

## 9. Complete H2-C graph reuse contract

The only graph reuse authorized is a complete, **pre-persistence**, v1 graph
left by an in-process interruption while the same runtime still owns the
current lease. It can skip REPAIR/Judge execution only after the runtime:

1. proves section 5's same Job/Video/owner/lease/pipeline/generation tuple;
2. reconstructs the same sealed semantic roots and current settings;
3. independently rederives P, R, J, E, S, and G; reruns the gate, Judge PASS
   verification, attestation, and finalizer;
4. verifies exact graph keys/paths, regular descriptor reads, no symlink/FIFO
   or special file, byte bounds, hashes/lengths, Artifact metadata, and both
   ProviderCall identities/response IDs; and
5. verifies that no terminal Job/pointer/lineage state conflicts with the
   pending plan, then mints a fresh runtime trusted-success conclusion and
   enters unchanged Phase G persistence.

G is a compact identity after proof, never a substitute for proof. A completed
terminal graph is read only through `AuthoritativeScoringReader`; it is not a
resume candidate. No trusted-success object is serialized, cached, copied, or
reconstructed: it is minted only after the full replay in the live runtime.

## 10. Partial-cache matrix

| Observed state | Required result |
|---|---|
| Complete same-job graph passes every proof | Reuse only as sections 7–9 allow; no network. |
| Valid R raw but J absent | Reuse R only after section 7; dispatch/replay Judge through H1/H2-B under the live lease. |
| Valid R/J evidence but structured/finalizer bytes absent | Re-run deterministic finalizer; never infer trusted success. |
| ProviderCall exists but raw missing; raw exists but ProviderCall missing; DB pointer/file missing; Artifact record/file mismatch | Integrity failure: no adoption or dispatch suppression. Reprove lease, then use existing fail-closed H2-C integrity handling; stale owner makes no mutation. |
| Partial G directory, partial temp/final files, wrong G, file from another Job/Video, orphan file with no exact DB authority | Never adopt as cache; preserve no-clobber and fail closed. |
| PENDING/in-flight/unknown ProviderCall | Never infer success, never redispatch from Phase I, and do not resolve expired SCORING ambiguity. |
| FAILED_RETRYABLE/FAILED_FINAL ProviderCall | Not a cache hit. Existing ErrorCode/H1 behavior controls; Phase I does not reinterpret it. |
| Terminal Job or expired lease | No reuse, no resurrection, no terminal mutation. |

## 11. Filesystem, ProviderCall, reader, and downstream contracts

Every Phase I artifact read must use the hardened Phase G/H2-C path: directory
descriptor anchoring; `O_NOFOLLOW`; `O_NONBLOCK` for attacker-controlled
reopen; immediate `fstat`; regular-file-only acceptance; bounded read; exact
hash verification; no-clobber; special-file rejection; and nested-directory
durability. `Path.read_bytes()`, filename-only lookup, or a new convenience
reader is forbidden for cache/recovery.

ProviderCall status meaning is frozen: `SUCCEEDED` is auditable evidence only;
`FAILED_*` is an outcome ledger; `PENDING`/unknown is an unresolved dispatch
state, never a success. A row may not be manually completed or fabricated to
make a hit.

`AuthoritativeScoringReader` remains the sole selector/verifier for completed
results and returns `VerifiedScoringRead`. Analysis, notes, weekly, reporting,
and any downstream reader must continue to consume that result, never a
"latest cached artifact" or Phase I flag. Pointerless legacy compatibility
remains inside the reader only; Phase I cannot run before v1/legacy
classification or make a v1 result use a legacy path.

## 12. Retry, errors, schema, and runtime sequence

No ErrorCode/detail is added. Cache-integrity failure uses the existing H2-C
integrity terminalization semantics only after lease re-proof; unresolved
dispatch remains H1 `UNKNOWN_PROVIDER_STATE`; ordinary cache absence is not an
error and follows normal H1/H2-B dispatch. Retry remains ErrorCode-based, not
detail-string based. `CAPABILITY_UNAVAILABLE` and
`TRUST_INTEGRITY_INVALID` remain excluded from resurrection/retry.

Schema stays v2 (`user_version=2`); no migration 003, new table, column,
index, cache TTL, or durable cache state is authorized. If implementation
needs any of these, it must stop with **DECISION NEEDED: schema authorization**.

The exact live execution sequence is:

```text
claim SCORING job -> prove current owner/lease/v1 -> rebuild runtime roots
-> search exact same-job evidence only -> hardened file/DB verification
-> rederive P/R/J/E/S/G and validate duplicate claims/ProviderCalls
-> complete graph hit: mint fresh runtime conclusion -> unchanged Phase G
-> component hit: skip only its proven network contact; execute remaining H2-B/H2-C
-> miss without contradiction: normal H1/H2-B dispatch
-> contradiction: lease reproof -> existing integrity terminalization, or stale no-op
```

## 13. Future implementation scope and stop conditions

Potential production scope is limited to `runtime.py`, `scoring.py`,
`h2_evidence.py`, and existing hardened filesystem helpers only if needed;
corresponding focused H1/H2-B/H2-C/Phase G/recovery tests may be added. It must
not alter `state.py` schema/migrations, `jobs.py` reclaim semantics,
`pipeline.py` retry semantics, provider implementations, PRIMARY persistence,
reader/downstream API contracts, dependencies, or configuration formats unless
separately authorized.

Stop and request a new decision if: a cross-job benefit is requested; a
ProviderCall cannot be job-bound by verified evidence; an expired outcome must
be resolved; a terminal Job must change; a new durable cache index/state,
migration, ErrorCode/detail literal, lineage version, or reader bypass is
needed; a required artifact cannot be opened through the hardened path; or a
test demonstrates a frozen H1/H2-B/H2-C/Phase G invariant conflict.

## 14. Future TDD and security matrix

The implementation must write RED tests before production changes and retain
all existing tests. The matrix must cover at least the following:

| Area | Required cases |
|---|---|
| Exact identity | 1 exact hit; 2 wrong provider; 3 wrong model; 4 wrong model digest; 5 prompt version; 6 schema version; 7 policy version; 8 settings hash; 9 normalized input; 14 pipeline version; 16 lineage generation. |
| Forgery | 10 forged evidence metadata + matching ProviderCall; 11 forged Judge metadata + matching ProviderCall; 12 forged H1/H2; 13 wrong Job; 15 wrong Video; forged G; forged request roots; valid hash from another Video. |
| Versions/artifacts | 17 pre-v2; 18 unknown future generation; 19 missing raw; 20 missing structured; 21 missing ProviderCall; 22 partial Judge graph; 23 filesystem orphan; 26 special file; pre-v2-as-v1 and v1-as-legacy attacks. |
| Filesystem | 24 symlink; 25 FIFO; directory/socket/device where available; final and temp special-file replacement; no follow/nonblocking/regular-file/hash tests. |
| Lease/state | 27 same-job valid complete graph; 28 stale lease; 29 expired SCORING; 30 terminal Job; 31 retry-pending non-SCORING unchanged; no stale `fail_job`. |
| Behavior/regression | 32 v1 cannot downgrade; 33 downstream uses `VerifiedScoringRead`; 34 no network on verified reuse; 35 authorized miss dispatches normally; 36 H1; 37 H2-B; 38 H2-C; 39 Phase G regressions. |
| Gates | 40 full `uv run pytest`; 41 `uv run mypy src`; 42 `uv run ruff check .`; 43 repository security scan; 44 `git diff --check`. |

The test suite must additionally prove that a cache hit never reconstructs a
trusted-success object from serialized data, a `SUCCEEDED` ProviderCall never
substitutes for its response Artifact, and no test weakens an existing
assertion to accommodate Phase I.

## 15. Implementation status

**PHASE I DESIGN DRAFTED.** It is ready only for independent design review.
**PHASE I IMPLEMENTATION REMAINS UNAUTHORIZED.**
