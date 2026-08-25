# TASK-016C Phase H2-B — Runtime REPAIR Control-Flow Authorization

## Status, scope, and precedence

**Status:** `READY FOR H2-B AUTHORIZATION INDEPENDENT REVIEW`.

This is a design/authorization document only.  It freezes the runtime control
flow for one received, eligible PRIMARY failure through one REPAIR provider
attempt and one REPAIR Judge attempt.  It authorizes no implementation in this
task and does not authorize H2-C, persistence, a schema change, a migration,
dependency work, a network call, or any public repair API.

This document consumes the accepted H2 authorization and H2-A evidence
foundations.  In the event of a conflict, the frozen H2 authorization controls
the evidence schema, serializer, identities, and H1 semantics; this document
controls only the narrower H2-B runtime sequencing and stop boundary.  It does
not amend `docs/TASK-016C-PHASE-H2-AUTHORIZATION.md`.

## 1. Frozen H2-B boundary

H2-B activates exactly this memory-only path:

```text
eligible PRIMARY failure, actually observed by the runtime
  -> runtime-owned verification of PRIMARY failure evidence
  -> one-shot REPAIR admission
  -> one REPAIR provider contact
  -> exact REPAIR raw capture
  -> candidate/schema validation
  -> TASK-016B language validation
  -> one REPAIR Judge admission and contact
  -> H2-A Judge raw replay and PASS verification
  -> PhaseH2BValidatedRepairResult (memory only)
```

It stops there.  In particular, H2-B does **not** mint
`PhaseHTrustedRepairSuccess`, call `TrustedPersistenceEntry.persist_success()`,
call `persist_repair()`, register a ProviderCall or an Artifact, produce a
write plan, promote a file, or make a SQLite success/stage update.  H2-C alone
may define the subsequent sealed repair-success aggregate and use the existing
Phase G persistence ingress.

## 2. Sole runtime entry condition

REPAIR is a private branch in the runtime's actual PRIMARY execution; it is
not an operation callable with a claimed failure class or evidence object.  At
the instant the branch decides whether to admit REPAIR, all of the following
must hold:

1. the same `RuntimeOperations` instance owns an active, unexpired `SCORING`
   lease for the job, proved through the accepted H1 admission state;
2. that state shows exactly one PRIMARY scoring role has already been consumed;
3. this runtime has received and classified that PRIMARY outcome in the same
   live execution (not reconstructed from caller input, a cache, a DB row, or a
   restart record);
4. runtime-owned inputs rebuild `PrimaryTrustedContext` with
   `build_primary_trusted_context(...)`, and
   `verify_primary_failure_evidence(pfe, trusted_context, validated_settings)`
   succeeds before eligibility is considered;
5. the independently replayed class is in the closed eligible set in section
   3, and is not `UNKNOWN_PROVIDER_STATE`; and
6. the shared H1 state shows the REPAIR role unused and no existing ProviderCall
   exists for the newly derived REPAIR request hash.

The runtime must derive the candidate PFE only while classifying the PRIMARY
path it dispatched.  It may pass that private, in-memory state to a private
helper, but the helper's input is runtime-owned context plus the internally
created PFE—not `failure_class=...`, an arbitrary `PrimaryFailureEvidence`, an
admission object, or a caller-created repair input.  Failure of any predicate
is a fail-closed terminal H2-B result with no REPAIR contact.

## 3. Closed eligibility set

The exact, and only, H2-B eligible `PrimaryFailureClass` literals are:

- `SCHEMA_OR_PARSE_INVALID`
- `LANGUAGE_INVALID`
- `JUDGE_REJECT`
- `JUDGE_UNCERTAIN`

`UNKNOWN_PROVIDER_STATE` is never eligible.  Nor are
`DETERMINISTIC_QUALITY_REJECT`, a pre-capture parser/protocol error, a timeout,
an authority/configuration mismatch, an arbitrary string, or a future enum
value.  This matches the frozen H2 source of truth exactly.  A known candidate
that the deterministic quality gate rejects is terminal and cannot be
relabeled as `JUDGE_REJECT`.

## 4. H1 admission, identity, and dispatch order

H2-B reuses the existing H1 `ScoringAdmissionRegistry` execution key, lock,
lease proof, role budget, `ProviderCall`-existence check, and terminal release
semantics.  It adds neither a second registry nor a receipt, token,
continuation, capability, or caller-minted repair identity.

The necessary REPAIR/REPAIR_JUDGE consumption operation is a private,
runtime-only H1 admission method.  It must be callable only by
`RuntimeOperations`' internal PRIMARY-failure branch; the current public
`ScoringDispatchAdmission.admit()` continues to reject caller attempts to
consume either repair role.

The exact REPAIR sequence is:

```text
verified runtime PRIMARY failure
  -> build_repair_normalized_input(
       job_id,
       runtime-owned PrimaryTrustedContext,
       internally created verified PFE,
       validated LocalScoringSettings,
     )
  -> repair_normalized_input_hash(RNI)
  -> build_repair_request_hash(RNI)
  -> local provider-factory/config construction (no contact)
  -> private H1 REPAIR admission under the shared execution-state lock
  -> one provider dispatch/contact
```

Provider construction is deliberately before REPAIR admission: a factory or
configuration failure is locally known and consumes no slot.  The admission is
the last authorization check before the first request is sent.  It re-proves
the active lease while holding the shared H1 state lock, rejects a consumed
`REPAIR` role or existing request hash, and records `REPAIR` as consumed before
releasing the lock and contacting the provider.  Once consumed it is never
unconsumed, including if no useful response follows.

`RNI.schema_version` remains exactly
`task016c-repair-normalized-input-v1`; `role` is exactly `REPAIR`; its
normalized-input hash remains H2 JCS SHA-256; and its provider request hash is
the frozen role-distinct `build_provider_request_hash()` result for
`local-scoring-repair-v1`.  Runtime derives every model, digest, temperature,
limit, role, normalized hash, and request hash from the trusted context,
validated settings, and verified PFE.  No caller-provided value in any of those
positions is authoritative.  A PRIMARY scoring identity, PRIMARY Judge H2, or
REPAIR Judge H2 cannot substitute for the REPAIR scoring identity.

If admission rejects, H2-B performs zero provider contacts and returns a
terminal fail-closed non-success.  If either runtime loses or expires its lease
before factory completion, admission, or contact, it performs no contact; after
admission but before contact, it still must re-prove the lease immediately
before dispatch and fail closed if that proof fails.  An expired/interrupted
SCORING job is handled by H1's terminal `UNKNOWN_PROVIDER_STATE` recovery path,
not by a H2-B retry.

## 5. Provider-contact and UNKNOWN boundary

**Provider contact** starts when the implementation invokes the provider method
that can send the REPAIR request (for Ollama, the request-bearing generate
operation).  Constructing a factory, deriving identities, validating local
data, admission rejection, or formatting a request is not contact.

Before contact, a factory/configuration failure, identity/evidence mismatch,
local parse/validation failure, or admission/lease rejection is a known local
failure.  It creates no `UNKNOWN_PROVIDER_STATE` merely because no request may
have been sent, and creates no retry or persistence authority.  It consumes no
REPAIR slot if it occurs before admission; a post-admission lease proof failure
leaves the one-shot slot consumed but still makes no contact.

After contact, timeout, connection/read interruption, ambiguous HTTP/provider
state, process interruption, missing reliable response state, or any failure
that makes it impossible to determine whether the provider received/acted on
the request is `UNKNOWN_PROVIDER_STATE`.  It is terminal and fail-closed:
there is no second REPAIR, Judge, takeover, cache interpretation, or
persistence.  Only H1's already-authorized terminal job/error update may occur
where applicable.

## 6. REPAIR raw capture and candidate result categories

REPAIR uses the same *candidate transport* boundary as PRIMARY because the
frozen parser consumes the full Ollama `/api/generate` HTTP body.  This is not
an accidental reuse of Judge raw semantics.

```text
complete HTTP body, at most 1,000,000 bytes
  -> strict UTF-8 decode, preserving the exact body text
  -> strict outer Ollama object and string `response` extraction
  -> strict UTF-8 re-encode of the full body
  -> SHA-256 and exact byte length of those full-body bytes
  -> canonical scoring-candidate parser on that same full body
```

The authoritative REPAIR raw is the full decoded HTTP response body—not
`payload["response"]`, a parsed object, a pretty-printed/re-serialized body,
or a trimmed value.  It is accepted at exactly 1,000,000 bytes and rejected
above that bound.  Strict UTF-8 re-encoding must reproduce the raw bytes;
surrogates fail.  The exact SHA-256 and byte length are calculated from
`repair_raw_utf8.encode("utf-8", errors="strict")`.  Whitespace, escape
spelling, and empty model content are preserved exactly; empty content is a
valid capture and then deterministically fails candidate parsing.

Duplicate object keys are not last-key-wins authority.  The H2-B transport
decoder must detect and reject duplicates while extracting the outer Ollama
envelope and while validating its inner scoring-candidate JSON.  A duplicate
in the outer envelope prevents a trustworthy `response` extraction and is a
post-contact `UNKNOWN_PROVIDER_STATE`.  A duplicate in the extracted inner
candidate has a trustworthy captured body but invalid candidate syntax: it is a
known REPAIR `SCHEMA_OR_PARSE_INVALID` terminal failure.  The future parser
change must be a single shared strict parser/replay seam, not a separate REPAIR
parser or a new identity algorithm.

Missing/non-string outer `response`, non-object outer JSON, invalid strict
UTF-8, oversize/truncated body, or otherwise incomplete outer protocol are
post-contact UNKNOWN outcomes.  Once the outer protocol is complete, malformed
inner JSON, non-object inner JSON, extra fields, duplicate inner keys, and
`ScoringCandidate` schema failure are known REPAIR parse/schema failures.  Each
has no recursive repair and no persistence.  Thus H2-B terminal categories are
`PRE_CONTACT_FAILURE`, `UNKNOWN_PROVIDER_STATE`,
`REPAIR_SCHEMA_OR_PARSE_INVALID`, `REPAIR_LANGUAGE_INVALID`,
`REPAIR_JUDGE_REJECT`, `REPAIR_JUDGE_UNCERTAIN`,
`REPAIR_JUDGE_UNKNOWN_PROVIDER_STATE`, and memory-only success.  These labels
are H2-B control-flow outcomes, not new DB enums or durable schema.

## 7. REPAIR language validation

After a parser-derived `ScoringCandidate`, H2-B invokes exactly the frozen
TASK-016B language validator, using the RNI/output-language binding.  It does
not add a second language algorithm, heuristic, or fallback.

An `INVALID` language result is `REPAIR_LANGUAGE_INVALID`: terminal,
non-success, no second REPAIR, no Judge dispatch, and no persistence.  During
H2-B this result exists only in memory plus any already-authorized H1 terminal
job/error transition; it creates neither a repair success record nor a new
artifact.  `UNCERTAIN` is fail-closed under the same terminal local-failure
rule; only a valid candidate may advance to the quality path.

## 8. REPAIR Judge sequence and budget

For a valid REPAIR candidate, H2-B derives—not accepts—the quality inputs and
Judge identity from runtime-owned repaired candidate, RNI, trusted runtime
settings, and the frozen quality authority:

```text
runtime-owned repaired candidate + RNI + validated settings
  -> expected REPAIR ContentQualityInput and QualityJudgeOperationInput
     (attempt_role = REPAIR)
  -> build_judge_h1_h2() / expected H1 and H2
  -> local Judge-factory/config construction (no contact)
  -> private H1 REPAIR_JUDGE admission
  -> one Judge provider contact
  -> H2-A extracted Judge raw capture and pure replay
```

The implementation must use the H2-A trusted composition pattern, extending it
only with a runtime-owned REPAIR derivation if a small composition primitive is
missing.  It must not accept a caller-created `JudgeTrustedContext`, Judge
operation, candidate, request hash, or Judge evidence as authority.  The
resulting role is exactly `REPAIR`; it cannot reuse PRIMARY H1/H2.

H1's total Judge budget remains unchanged: PRIMARY may consume
`PRIMARY_JUDGE` once and REPAIR may consume `REPAIR_JUDGE` once, for at most two
Judge contacts.  The shared H1 lock prevents duplicate REPAIR Judge consumption
and H1 requires a consumed REPAIR role before this role can be consumed.  A
restart, a second runtime, an existing ProviderCall state, an expired lease, or
a second attempt rejects before a Judge contact.  No hidden third Judge call is
authorized.

Judge raw is exactly H2-A's boundary: the extracted Ollama `response` string,
not the full HTTP body; strict UTF-8 bytes; at most 20,000 bytes inclusive;
exact SHA-256 and byte length; no trimming, normalization, or reserialization.
Outer protocol/raw capture failures after contact are
`UNKNOWN_PROVIDER_STATE`, not `UNCERTAIN`.  The pure replay uses the existing
Judge parser/evidence registry/result promotion; raw semantic invalidity is
`UNCERTAIN` only when valid captured raw exists.

Judge outcomes are frozen as follows:

| REPAIR Judge outcome | H2-B action |
|---|---|
| `PASS` | May mint the memory-only result in section 10 after all H2-A replay and binding checks pass. |
| `REJECT` | Terminal `REPAIR_JUDGE_REJECT`; no second repair, no persistence. |
| `UNCERTAIN` | Terminal `REPAIR_JUDGE_UNCERTAIN`; no retry or further action. |
| `UNKNOWN_PROVIDER_STATE` | Terminal fail-closed; no retry, repair, Judge, or persistence. |

## 9. Runtime seam and non-public surface

The future branch belongs in `RuntimeOperations` immediately after the
runtime's actual PRIMARY outcome classification and before the current
PRIMARY-success-only finalizer/persistence continuation.  Concretely, it
replaces the private `_KnownPrimaryFailure` escape at the producer-owned
PRIMARY control-flow point with a private classifier that either returns the
normal PRIMARY path, produces a verified eligible PFE and calls the private
H2-B branch, or terminates fail-closed.  `run_primary_trusted_scoring()` remains
PRIMARY-only and may not become a caller-controlled `repair(...)` overload.

An internal helper may accept one opaque runtime-owned execution-state object
containing the lease-bound admission view, job id, rebuilt trusted PRIMARY
context, internally generated PFE, and validated settings.  It must not accept
arbitrary PFE/RNI/model/limits/role/hash/admission arguments from a public API.
There will be no public `repair`, `retry`, `dispatch_repair`, repair factory,
receipt, token, continuation, registry handle, repair authority, or
caller-supplied admission state.

## 10. In-memory success and H2-C handoff

H2-B's only success value is an exact, immutable,
non-serializable/private-mint intermediate named
`PhaseH2BValidatedRepairResult`.  It is data plus sealed in-memory provenance,
not a persistence capability.  It must contain, or seal bindings to:

- the `TrustedScoreResult` produced only by the existing finalizer from the
  repaired candidate;
- exact `RepairNormalizedInput`, its H2 JCS normalized-input hash, and the
  role-distinct REPAIR scoring request hash;
- the independently verified `PrimaryFailureEvidence` and its hash;
- the exact REPAIR full-body raw string, strict UTF-8 byte length/SHA-256, and
  same-parser derived candidate/hash;
- the REPAIR `JudgeEvidence`, whose role is `REPAIR`, expected H1/H2, raw
  binding, pure-replayed result, and status are all `PASS`; and
- enough sealed runtime provenance to rederive all of the preceding bindings
  against the current trusted context/settings.

It must reject copy/deepcopy/pickle/JSON restoration and cannot be accepted by
`TrustedPersistenceEntry`, directly or by structural resemblance.  It confers
no file, Artifact, ProviderCall, SQLite, job-success, stage-success, cache, or
write-plan authority.

H2-C receives only this object.  Its narrow task is:

```text
PhaseH2BValidatedRepairResult
  -> construct and independently revalidate PhaseHTrustedRepairSuccess
  -> existing TrustedPersistenceEntry.persist_success()
  -> existing Phase G PREWRITE/write-plan/filesystem/SQLite mechanics
```

H2-C must not re-decide eligibility, alter model/config trust, dispatch a
provider or Judge, replay a repair budget decision, or invent an identity rule.

## 11. Concurrency and restart contract

### Concurrent runtimes

Attack case: runtime A and B observe the same eligible received PRIMARY failure
for a shared active `SCORING` job/lease.  The H1 lease proof and shared
execution-state lock permit exactly one runtime to consume `REPAIR` for the
derived request hash.  The winner alone may contact the provider.  The loser
finds a non-owned/expired lease, an already-consumed role, or an existing
request-hash state and fails closed before contact.  A future RED test must run
both branches concurrently and assert exactly one REPAIR provider contact, at
most one REPAIR Judge contact, one REPAIR role consumption, zero persistence,
and zero contact by the losing branch.

### Restart and crash matrix

Admission state, PFE, RNI, raw capture, Judge evidence, and
`PhaseH2BValidatedRepairResult` are memory-only and are never restored.  The
following table freezes H2-B behavior; `H3` owns any later recovery work.

| Event | Consumed H1 budget | Provider state / H2-B result | Retry and owner |
|---|---|---|---|
| A. Crash before REPAIR provider contact | None if before admission; `REPAIR` if after admission but before contact | No provider contact is known; the live H2-B result is lost. A consumed admission is not restored. | No H2-B retry. Later restart follows H1 terminal unknown/fail-closed handling; H3 owns any separately authorized recovery. |
| B. Crash after REPAIR contact before response classification | `REPAIR` | Unknown provider state. | No retry, Judge, or persistence; H1 terminal unknown path only. |
| C. Crash after valid REPAIR response before Judge | `REPAIR`; no `REPAIR_JUDGE` if not admitted | Response may be valid but all proof is volatile; restart cannot safely reuse it. | No retry or reuse; terminal unknown/fail-closed on restart; H3 only. |
| D. Crash after REPAIR Judge contact | `REPAIR` and `REPAIR_JUDGE` | Unknown Judge provider state. | No retry, further Judge, or persistence; H1 terminal unknown path only. |
| E. Crash after Judge PASS before H2-C/persistence | `REPAIR` and `REPAIR_JUDGE` | Validated result was only memory; it is lost and cannot become success from a restart. | No H2-B retry or persistence; H1 terminal unknown/fail-closed handling, H3 only if later authorized. |

An existing complete verified Phase G/H2-C graph, if H2-C later creates one, is
handled solely by existing idempotent-completion verification and makes no
provider or Judge contact.  H2-B creates no durable schema or recovery marker.

## 12. Side-effect accounting

For every pre-dispatch rejection—invalid/forged PFE, caller-created RNI,
identity/config override, factory failure, admission failure, lease failure,
or local validation failure—assert:

- zero additional scoring-provider contacts;
- zero additional Judge contacts;
- zero filesystem writes;
- zero Artifact writes; and
- zero SQLite success writes.

For stateful rejections after a baseline (for example a consumed role, a lost
lease after admission, a duplicate dispatch, or an UNKNOWN response), assert
relative to that baseline: no additional unauthorized provider contact, no
duplicate role consumption, no duplicate Judge contact, and no persistence.
`UNKNOWN_PROVIDER_STATE` may perform only the existing H1 terminal job/error
update where already authorized; it never writes a success graph.

## 13. Future RED behavioral matrix

The future H2-B implementation must add focused RED tests for all of the
following, preserving the accounting in section 12:

1. caller invokes REPAIR without an actual PRIMARY failure;
2. forged otherwise eligible PFE;
3. `UNKNOWN_PROVIDER_STATE` relabeled as eligible;
4. duplicate REPAIR admission;
5. two concurrent runtimes attempting the same REPAIR;
6. caller-supplied attacker `RepairNormalizedInput`;
7. caller model/digest/temperature/limit override;
8. PRIMARY identity substituted as REPAIR identity;
9. REPAIR identity substituted as PRIMARY identity;
10. provider factory/configuration failure before contact;
11. timeout/interruption after REPAIR contact;
12. valid captured raw with malformed/duplicate-key REPAIR candidate;
13. REPAIR candidate failing TASK-016B language validation;
14. duplicate REPAIR Judge admission;
15. PRIMARY Judge evidence substituted into REPAIR Judge;
16. REPAIR Judge context/candidate/request substitution;
17. REPAIR Judge `REJECT`;
18. REPAIR Judge `UNCERTAIN`;
19. REPAIR Judge `UNKNOWN_PROVIDER_STATE`;
20. a second REPAIR attempt after every possible repair failure;
21. direct passage of `PhaseH2BValidatedRepairResult` to
    `TrustedPersistenceEntry`; and
22. every attempted REPAIR persistence/write/ProviderCall/Artifact registration
    before H2-C.

## 14. Future implementation allowance and prohibitions

A separate H2-B implementation authorization may allow only the smallest
necessary edits to:

- `src/youtube_intel/runtime.py` — private PRIMARY-failure branch and private
  REPAIR/REPAIR Judge dispatch orchestration;
- `src/youtube_intel/scoring_admission.py` — only a non-public,
  runtime-guarded use of the existing H1 state for REPAIR/REPAIR_JUDGE;
- `src/youtube_intel/h2_evidence.py` — only a missing runtime-owned REPAIR
  Judge composition primitive, without changing H2-A trust rules or JCS;
- `src/youtube_intel/providers/ollama.py` — only the existing provider seam's
  one-shot REPAIR transport/raw-capture/shared strict-parser integration;
- `src/youtube_intel/scoring.py` — only the private in-memory scoring seam
  necessary to mint `PhaseH2BValidatedRepairResult` (not a persistence
  aggregate);
- focused H2-B and H1/H2-A regression tests; and
- H2-B handoff documentation.

The following are not authorized: Phase G persistence machinery; state schema
or migrations; repository write APIs; Artifact/ProviderCall registration;
filesystem write-plan changes; `h2_jcs.py`; existing identity algorithms;
TASK-016B language algorithm; public runtime repair APIs; `PhaseHTrustedRepairSuccess`;
`persist_success(REPAIR)`; `persist_repair()`; cache/recovery/H3 work;
dependencies, lockfiles, configuration, real provider/model/network/Vault use.

## 15. Completion boundary

| Capability | H2-B status |
|---|---|
| REPAIR runtime control flow | Yes |
| Single REPAIR provider dispatch | Yes |
| REPAIR Judge | Yes |
| Validated in-memory repair result | Yes |
| REPAIR persistence | No |
| `PhaseHTrustedRepairSuccess` persistence activation | No |
| H2-C required | Yes |

Until a future implementation and independent review satisfy this document,
H2-B remains design-only.
