# TASK-016C Phase I — Live In-Frame Evidence Hardening Authorization

## Status, supersession, and decision

Status: **APPROVED · AUDITED · NO-OP DETERMINATION · CLOSED.**

This document supersedes the complete durable-reuse proposal in commit `7018c83`. Its durable ProviderCall, Artifact, raw-response, Judge, and pre-persistence complete-graph reuse clauses are **SUPERSEDED** and no longer normative. This is docs only: no production, tests, migration, dependency, provider, merge, push, tag, rebase, or squash is authorized.

Selected final option: **I-B — hardening-only.** Current production is a one-pass lexical H2-B -> H2-C -> Phase G flow. It has no meaningful repeated deterministic consumer or duplicate network dispatch to optimize. Phase I must not manufacture an in-memory cache merely to justify itself. A future implementation may be documentation/test-only, or narrowly consolidate a proven invariant without semantic reuse behavior.

The frozen trust chain remains:

```text
sealed semantic inputs -> deterministic derivation -> derived identities
-> duplicated-claim validation -> ProviderCall validation where Phase G requires it
-> verified P/R/J/E/S/G -> trusted persistence/read
```

No persisted value is authority. No in-memory value becomes authority merely because it is immutable or self-consistent; it is usable only in the exact runtime-owned lexical flow that legitimately produced and validated it.

## 1. Terminology and exact scope

- **In-frame verified evidence** is a runtime-owned immutable value produced and fully verified during the current `RuntimeOperations.scoring_stage` invocation.
- **In-frame reuse** is later use of that value in the same lexical scoring execution, same `RuntimeOperations` instance, same Job/owner, and valid lease. It is not a durable cache hit.
- **Durable cache** is reuse selected from SQLite, Artifact rows/files, G paths/directories, filesystem orphans, or an earlier runtime/process. It is **not authorized**.
- **Recovery** is continuation after process/runtime ownership loss or lease expiry. It is **not authorized**.

Phase I permits only analysis/hardening of the in-frame boundary. It does not authorize a new cache/recovery architecture, persisted cache marker, durable index, ownership transfer, scoring rerun, or semantic change.

## 2. Actual frozen runtime windows

| Window | Actual state | Phase I disposition |
|---|---|---|
| 1. Before REPAIR dispatch | No REPAIR evidence | Frozen H1 admission then legitimate dispatch; no reuse. |
| 2. After REPAIR validation | Current frame holds validated raw/candidate/language/gate/RNI/R evidence | It proceeds once through the existing lexical flow; no durable lookup or second dispatch. |
| 3. After REPAIR_JUDGE validation | Current frame also holds validated Judge input/evidence/result/attestation/J | It proceeds once to the H2-B aggregate/H2-C; no durable lookup or second dispatch. |
| 4. H2-C finalizer before Phase G | Current closure holds aggregate, replayed P/R/J/E/S/G envelope, and fresh success | Existing code passes it once to Phase G; no independent second consumer exists. |
| 5. Filesystem before commit | Possible orphaned files only | Non-authoritative; frozen handling only. |
| 6. Phase G transaction | Artifact and ProviderCall rows are atomically registered/rolled back | Frozen Phase G only. |
| 7. After commit | Job is durably complete | Existing idempotent/read semantics only; not Phase I execution reuse. |

Audit evidence: `runtime.py` constructs lexical `PhaseH2BValidatedRepairResult`, defines and invokes `_h2c_replay_continuation` once, mints `PhaseHTrustedRepairSuccess`, then calls `TrustedPersistenceEntry.persist_success()` once. The aggregate is local-only/untrusted and not retained on the runtime, in a registry, or cache. Therefore no current duplicate operation seam exists.

## 3. Durable reuse and recovery are forbidden

All proposals below are **NO**:

| Proposal | Decision |
|---|---|
| Durable ProviderCall/Artifact/raw/structured/Judge/G hit | NO |
| Durable Provider or Judge network skip | NO |
| Filesystem orphan or partial-G adoption | NO |
| Cross-process, restart, or new `RuntimeOperations` reuse | NO |
| Cross-job, same-G, same-request-hash, or response sharing | NO |
| Expired SCORING continuation / terminal resurrection | NO |
| PRIMARY semantic cache/reuse | NO |
| New ProviderCall/cache-hit marker or admission type | NO |
| Migration 003, lineage/schema change, ErrorCode/detail | NO |
| H1/H2-A/H2-B/H2-C/Phase G/reader reopening | NO |

`provider_calls` are global by request hash and do not prove Job-bound durable cache ownership. Before Phase G no durable same-Job artifact/provider graph exists; after Phase G the Job is terminal. Phase I must not bridge that infeasible gap.

## 4. Provider, Judge, admission, and audit policy

Initial REPAIR work remains exactly:

```text
REPAIR admission -> provider dispatch -> response validation -> in-frame evidence
```

Initial REPAIR_JUDGE work remains exactly:

```text
REPAIR_JUDGE admission -> Judge dispatch -> sealed validation -> in-frame evidence
```

Phase I does not consult an existing ProviderCall, request hash, Artifact, or file to skip either initial call. It does not alter `scoring_admission.py`, create cache admission, reuse admission, or reinterpret existing ProviderCall rejection. If a legitimately validated value is later consumed in the same frame, it creates no second dispatch, admission, or ProviderCall: that is ordinary one-pass object flow, not a cache hit.

ProviderCall auditability is unchanged: one admission, one actual dispatch, one original ProviderCall record where frozen Phase G creates it, and no cache-hit record/marker. `PENDING`, failed, historical, or otherwise existing rows never qualify as successful in-frame evidence.

## 5. Same-runtime, same-frame, and lease contract

**Same runtime** is the exact `RuntimeOperations` instance executing the current `scoring_stage`. **Same frame** is the same invocation and lexical H2-B/H2-C continuation, not merely matching IDs.

A new instance, process restart, or later invocation is outside the domain even where Job ID matches, an old lease has not expired, or files remain. No proof crosses those boundaries.

At frozen H2-C replay entry, the runtime proves the current SCORING `RUNNING` Job, same owner, and lease valid at current time. The subsequent replay and trusted-success mint occur in that same lexical execution. **There is no separate immediate pre-mint lease re-proof in current H2-C, and I-B does not require or authorize one.**

Existing H2-C integrity terminalization retains its own frozen stale-owner/lease handling; it is not a new global check. Frozen Phase G independently proves/re-proves current owner/lease authority before persistence or mutation. If a future I-B invariant consolidation ever contains an actual same-frame duplicate-dispatch guard, its authority requirements must be explicitly authorized then; no current duplicate-suppression seam exists.

If a future audit demonstrates a concrete security defect between replay-entry proof and trusted-success mint, an immediate pre-mint re-proof requires separate explicit H2-C hardening authorization, independent review, focused TDD, and regression evidence. It is not pre-authorized here.

## 6. Value inventory and I-B rationale

| Value | Current flow | Why it is not an optimization cache |
|---|---|---|
| `RepairNormalizedInput`, RNI bytes/hash, R | H2-B -> independently rebuilt in single H2-C replay | The replay is a frozen trust check; eliminating it weakens H2-C. |
| REPAIR raw/candidate/language/gate evidence | H2-B aggregate -> single H2-C replay | Claims must be replayed; no later consumer exists. |
| Judge input, H1/H2/J, evidence/result/attestation | H2-B aggregate -> single H2-C replay | Claims must be replayed; no duplicate dispatch exists. |
| `RepairPersistenceGraphIdentityV2` / G | H2-C -> one Phase G plan | One persistence consumer only. |
| `PhaseHTrustedRepairSuccess` | Fresh mint -> immediate one Phase G call | Normal lexical handoff, never cache reconstruction. |

A generic memo, retained runtime registry, reusable aggregate, or operation cache would add authority surface without eliminating real duplicate work. I-B permits only proof-preserving invariant consolidation if a concrete duplicate is later demonstrated; otherwise production work is none.

## 7. Durable state, partial state, and crash matrix

| State/event | Required disposition |
|---|---|
| ProviderCall, Artifact, raw/structured file, G directory, or committed graph | Not Phase I input; frozen Phase G/reader/idempotency only. |
| Orphan or partial G directory | Never reusable authority; frozen H2-C/Phase G handling only. |
| No in-frame verified REPAIR value | Normal REPAIR path; not a cache miss/error/retry. |
| Verified REPAIR/Judge/complete graph value in current frame | Existing one-pass lexical handoff only. |
| Lease lost, terminal Job, or new runtime | In-frame use unavailable; frozen state handling. |
| Crash before REPAIR completion | In-memory evidence lost; no recovery. |
| Crash after REPAIR before Judge | In-memory evidence lost; no durable reuse. |
| Crash after Judge or graph derivation before Phase G | In-memory proof lost; any orphan is non-authoritative; no recovery. |
| Crash during Phase G | Frozen rollback/idempotency/no-clobber semantics only. |
| Crash after Phase G | Durable completed-read semantics only. |
| Expired SCORING | H1 `UNKNOWN_PROVIDER_STATE` -> `FAILED_FINAL`; no continuation. |

In-frame hardening never bypasses PREWRITE_VALIDATE, filesystem integrity, no-clobber, Artifact/ProviderCall validation where Phase G requires it, lineage CAS, rollback, or re-proof.

## 8. Settings, versions, trusted success, and downstream

An in-frame value is usable only while bound to the exact current sealed input, derived request identity, provider/model/digest, prompt/schema/policy, settings provenance, and lineage/evidence/graph producer versions that produced it. Any mismatch makes it unavailable; no persistent invalidation index is authorized.

Trusted-success objects are never serialized, deserialized, persisted, or reconstructed as cache authority. Passing a freshly minted object directly through the existing same-frame lexical Phase G path is normal object flow.

`AuthoritativeScoringReader` remains unchanged and is the sole completed-result selector/verifier. Analysis, notes, weekly, reporting, `VerifiedScoringRead`, legacy classification, and v1 no-downgrade remain unchanged.

## 9. Schema, errors, and future file scope

Schema v2 is sufficient. Migration 003 is **NO** because Phase I stores no durable state. New ErrorCodes/detail literals are **NO**: in-frame value absence is normal execution, durable integrity keeps frozen behavior, and lease loss keeps frozen stale behavior.

Future production scope is **none by default**. If a concrete same-frame duplicate is demonstrated, scope may be only `runtime.py` and/or `scoring.py` plus focused tests, after separate implementation approval. `scoring_admission.py`, `state.py` semantics, migrations, providers, `reporting.py`, reader contracts, Phase G ordering, and configuration are out of scope. Stop with **DECISION NEEDED** if any optimization needs persistence, cross-process ownership, second dispatch, changed admission, schema, ErrorCode, lineage, or reader change.

## 10. Future TDD/security matrix

RED-first work must preserve existing tests. For I-B, tests prove absence of new reuse seams rather than inventing a cache:

1. same runtime instance; 2. same `scoring_stage` invocation; 3. same Job;
4. same owner; 5. H2-C replay entry requires its existing valid owner/lease
proof; 6. existing integrity-terminalization stale-owner behavior is unchanged;
7. Phase G still re-proves owner/lease before mutation; 8. no Phase I code adds
an immediate pre-mint lease check; 9. new
`RuntimeOperations` cannot reuse; 10. process restart cannot reuse; 11.
different Job cannot reuse; 12. expired SCORING cannot reuse; 13. `FAILED_FINAL`
cannot reuse; 14. `SUCCEEDED` does not re-enter Phase I; 15. no durable
ProviderCall hit; 16. existing ProviderCall keeps frozen admission semantics;
17. no durable raw Artifact hit; 18. filesystem orphan not reusable; 19.
partial G directory not reusable; 20. no migration 003; 21. no ErrorCode; 22.
no second REPAIR admission for an actual repeated in-frame use; 23. no second
REPAIR_JUDGE admission for that use; 24. no second ProviderCall for it; 25.
sealed semantic mismatch prevents use; 26. settings mismatch prevents use; 27.
version mismatch prevents use; 28. trusted-success is not reconstructed from
durable state; 29. Phase G unchanged; 30. `AuthoritativeScoringReader`
unchanged; 31. PRIMARY reuse absent; 32. H1 regression; 33. H2-B regression;
34. H2-C regression; 35. Phase G regression; 36. lineage regression; 37.
correction-round forgery regressions; 38. FIFO/symlink regressions; 39. weekly
authoritative-reader regression; 40. full `uv run pytest`; 41. `uv run mypy
src`; 42. `uv run ruff check .`; 43. security scan; 44. `git diff --check`.

## 11. Frozen preservation and implementation status

H1, H2-A, H2-B, H2-C, Phase G, lineage, no-rerun, no-cross-job, and the authoritative-reader boundary are preserved exactly. No durable provider/Judge/graph reuse, process recovery, PRIMARY reuse, terminal resurrection, schema change, or ErrorCode is authorized.

The original design proposal (`7018c83d6703cd03ef6f56ad206cf211f1d4db55`)
was independently reviewed as **REQUEST CHANGES**: a durable pre-persistence
reuse state was mechanically unavailable because schema-v2 cannot prove the
same-job condition without reopening frozen persistence/admission semantics.
Amendment Round 1 (`79b25729cf33ada554db3701f270e0b48d388661`) selected
**OPTION I-B — HARDENING ONLY** and was independently reviewed as **REQUEST
CHANGES** because it inaccurately claimed immediate pre-trusted-success-mint
lease re-proof. Amendment Round 2 (`52a7e4236337f39df199c51ef2badcf4274dd065`)
corrected that boundary and was independently **APPROVED**.

## 12. Final Phase I closeout and freeze

### Decision

**PHASE I IS IMPLEMENTED AS A HARDENING AUDIT / NO-OP.** It was not skipped:
the audit investigated cache, recovery, and reuse hardening against the
approved I-B contract and found that the current architecture already meets
that contract. Zero production change is therefore the correct implementation
outcome.

| Item | Final decision |
|---|---|
| Phase I mode | **I-B — HARDENING ONLY / NO-OP** |
| Production changes | None |
| Test changes | None |
| Schema changes / migration 003 | None / unauthorized and not required |
| New ErrorCode | None |
| Semantic cache | Not implemented, not authorized, not required |
| Durable cache or recovery | Not authorized |

### Audited execution and admission model

The confirmed execution is one H2-B validated continuation, one REPAIR
admission/dispatch/validation, one REPAIR_JUDGE admission/Judge
dispatch/validation, one H2-C replay, one freshly minted trusted repair
success, and one `Phase G persist_success`. There is no meaningful duplicate
semantic or network work, so no memo/cache layer is justified.

REPAIR and REPAIR_JUDGE admission remain unchanged. Existing ProviderCalls
continue to block admission exactly under frozen `scoring_admission.py`.
There is no cache-specific admission, bypass, historical reuse, or second
admission semantics; `scoring_admission.py` remains frozen.

`ProviderCall` remains the dispatch/evidence ledger, not cache authority. No
cache-hit ProviderCall, historical semantic reuse, network-skip marker,
duplicate ProviderCall semantics, or persistence column exists. One actual
dispatch retains the frozen audit trail.

### Reuse, trust, crash, and lease boundaries

All of the following are frozen **NO**: durable Provider, Judge, or graph
reuse; ProviderCall-as-cache-hit; Artifact cache authority; filesystem-orphan
reuse; G-only reuse; cross-process, new-`RuntimeOperations`, process-restart,
cross-job, same-G cross-job, or request-hash cross-job reuse; expired-SCORING
recovery; terminal Job resurrection; and PRIMARY semantic reuse.

Trusted-success objects remain freshly runtime-minted, exact-type gated,
lexically passed, non-serialized as authority, and non-reconstructed from
durable state. Phase I added no trusted-object lifecycle.

At H2-C replay entry, the existing Job/owner/lease proof exists. An immediate
pre-trusted-success-mint re-proof does **not** exist, and Phase I neither
requires nor authorizes one. Existing integrity-terminalization authority and
stale handling are unchanged. Phase G's owner/lease proof before
mutation/persistence exists and remains frozen. Any future immediate pre-mint
lease hardening requires a concrete defect, separate H2-C authorization,
independent review, focused TDD, and regression proof.

| Crash point | Frozen disposition |
|---|---|
| Before REPAIR completes | In-memory state lost; no Phase I recovery. |
| After REPAIR before Judge | In-memory state lost; no durable Phase I reuse. |
| After Judge | In-memory state lost; no durable Phase I reuse. |
| After graph derivation before Phase G | In-memory graph lost; files/orphans are non-authoritative; no Phase I recovery. |
| During Phase G | Existing frozen Phase G behavior only. |
| After Phase G commit | Existing committed/read/idempotency semantics only. |

### Frozen authority, persistence, lineage, and filesystem boundaries

Phase G remains closed. Phase I introduced no early Artifact registration,
early ProviderCall persistence, pre-Phase-G durable evidence table, second
persistence seam, atomic-ordering change, or lineage change. Existing
PREWRITE_VALIDATE, filesystem no-clobber, SQLite transaction, lineage
bookkeeping, Job/Video CAS, and rollback/re-proof remain frozen.

The audit found no reachable bypass of descriptor anchoring, `O_NOFOLLOW`,
`O_NONBLOCK` where required, immediate `fstat`, regular-file requirement, FIFO
rejection, symlink rejection, special-file rejection, no-clobber, or orphan
handling. Phase I added no filesystem path.

`AuthoritativeScoringReader` is unchanged and remains the persisted scoring
authority boundary. No latest-artifact shortcut, weekly authority bypass,
analysis/note/reporting cache authority, or Phase I read cache was added;
`VerifiedScoringRead` remains the frozen downstream authority.

Schema remains `user_version = 2`; scoring lineage remains
`task016c-scoring-lineage-v1`. Legacy NULL behavior, fail-closed unknown
generation behavior, and Video -> Job -> Artifact authority remain frozen. No
migration 003 exists.

### Independent hardening-audit evidence

These checks were run by the independent hardening audit; this documentation
closeout did not rerun them:

| Audit check | Result |
|---|---|
| Focused tests | 278 passed |
| Full pytest | 1761 passed; 1 pre-existing Pydantic serializer warning |
| mypy | PASS; 31 source files; no issues |
| Ruff | PASS |
| Security scan | PASS / `status=clean`; existing WARN-only findings remain |
| `git diff --check` | PASS |
| Worktree | Clean |

Self-consistent H2-C forgery defenses remained PASS, including forged
`RepairProviderEvidence` plus matching ProviderCall, forged `JudgeEvidence`
plus matching ProviderCall, forged `judge_h2`, and provider/model/prompt/schema
mutations. The audit found no production defect, meaningful test gap, or
missing Phase I regression test.

### Closed status and future change gate

**H1 CLOSED. H2-A CLOSED. H2-B CLOSED. H2-C CLOSED. Phase G CLOSED WITH
PREVIOUSLY AUTHORIZED LINEAGE BOOKKEEPING. Phase I CLOSED — HARDENING AUDIT /
NO-OP.** No semantic cache/recovery phase remains pending under TASK-016C.

Any future durable cache; Provider/Judge response reuse; process-restart,
cross-process, cross-job, same-G, or expired-SCORING reuse/recovery; terminal
resurrection; PRIMARY reuse; persistent cache state; migration 003; admission,
ProviderCall, lineage, `AuthoritativeScoringReader`, or Phase G ordering change
requires a **new explicit authorization**. This closeout is not authorization
for any such work.

**PHASE I CLOSEOUT RECORDED**

**PHASE I HARDENING AUDIT FROZEN**

**PHASE I NO-OP DETERMINATION FROZEN**

**NO PRODUCTION CHANGE REQUIRED**

**NO TEST CHANGE REQUIRED**

**TASK-016C IMPLEMENTATION PHASES COMPLETE**

**READY FOR TASK-016C FINAL INTEGRATION / RELEASE READINESS REVIEW**

## 13. Final integration freeze

The final independent integration result is recorded in
[`TASK-016C-FINAL-FREEZE.md`](TASK-016C-FINAL-FREEZE.md). Phase I remains
**CLOSED — HARDENING AUDIT / NO-OP** within a **TASK-016C COMPLETE** and
**TASK-016C FROZEN** record. This reference adds no implementation authority:
**MERGE NOT YET AUTHORIZED**.
