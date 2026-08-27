# TASK-016C 交接报告

## Phase H2-C — Final Closeout / Freeze

### Status and authority

**IMPLEMENTED — INDEPENDENTLY REVIEWED — APPROVED — CLOSED.**

- Authorization base: `59bcf282a7e6208eb8395ecc4cc9a3fdbf6d6011`.
- Final independently approved implementation HEAD: `2ae44b7`.
- This closeout records the approved implementation state; it does not rewrite,
  squash, or replace the historical authorization or REQUEST CHANGES evidence.
- The authoritative implementation chain is, in order:

  1. Original implementation: `e5031e8`, `ef3df66`, `e1488c9`, `ddd0a3c`,
     `02f397f`.
  2. Correction Round 1: `39f3a8f`, `7ed55ee`, `0395d09`, `6cb84e9`,
     `a46fa75`.
  3. Correction Round 2: `4b1ccd1`, `a70a2e9`, `1477fb0`.
  4. Correction Round 3: `1572142`, `2ae44b7`.

### Final independent-review evidence

- Persistence review suite: **53 passed**.
- Broader regression suite: **328 passed**.
- Full suite: **1761 passed**; one pre-existing Pydantic serializer warning
  remains.
- `uv run mypy src`: **PASS**, 31 source files, no issues.
- Ruff: **PASS**.
- `git diff --check`: **PASS**.
- Security scan: **PASS / clean status**; existing WARN-only findings remain.
- Independent adversarial reproductions both rejected the attack:
  self-consistent forged REPAIR model graph **REJECTED**; self-consistent forged
  Judge model graph **REJECTED**.

### Frozen H2-C trust and generation contracts

Untrusted REPAIR/Judge data never becomes trusted merely because its graph is
structurally self-consistent. Persisted evidence fields are claims, never trust
roots. The frozen trust direction is:

```text
sealed semantic inputs
  -> canonical deterministic derivation
  -> derived request/hash identities
  -> validation of duplicated evidence claims
  -> validation of persisted ProviderCall identities
  -> verified R/J
  -> verified E/S
  -> RepairPersistenceGraphIdentityV2
  -> verified G
  -> trusted persistence/read
```

For a new post-v2 `SCORING` job,
`scoring_lineage_version = task016c-scoring-lineage-v1`; non-`SCORING` jobs and
historical/pre-v2 jobs retain `NULL`. This value is repository-derived and
immutable: no caller controls the generation.

After validated H2-B PASS:

| Generation | Frozen outcome |
|---|---|
| `NULL` | `CAPABILITY_UNAVAILABLE`, `H2B_PASS_AWAITING_H2C`, `retry_at=None`, `FAILED_FINAL`, `TERMINAL`; no H2-C entry. |
| v1 | May enter H2-C. |
| Unknown non-`NULL` | `TRUST_INTEGRITY_INVALID`, exact detail `H2C_REPLAY_INVALID:SCORING_LINEAGE_VERSION_INVALID`, `retry_at=None`, `FAILED_FINAL`, `TERMINAL`; no H2-C entry. |

### Frozen repair admission and sealed-semantics verification

- `REPAIR` and `REPAIR_JUDGE` remain runtime-internal admissions. There is no
  caller repair receipt, token, or authority.
- Eligible failures remain the exact frozen closed set; `UNKNOWN` remains
  ineligible. H1 admission semantics and `scoring_admission.py` remain frozen.
- REPAIR verification is exactly: sealed `RepairNormalizedInput` -> derived
  normalized-input hash -> cross-check `RepairProviderEvidence` metadata ->
  derive the REPAIR `ProviderCall` request identity solely from sealed values ->
  verify the persisted `ProviderCall` -> verify R.
- JUDGE verification is exactly: sealed `QualityJudgeOperationInput` -> derive
  Judge H1/H2 -> cross-check every `JudgeEvidence` H1/H2/metadata claim ->
  derive the `REPAIR_JUDGE` `ProviderCall` identity from sealed values -> verify
  the persisted `ProviderCall` -> verify J.
- No evidence metadata may bootstrap its own authority.

### Frozen graph, filesystem, and lineage contracts

`RepairPersistenceGraphIdentityV2` is frozen. Its commitments are exactly:

```text
E = SHA256(exact H2-JCS RepairCompositeEnvelope bytes)
S = SHA256(exact finalizer structured bytes)
G = SHA256(H2-JCS(RepairPersistenceGraphIdentityV2))
```

There is no circular G/path/key dependency. Repair physical identity is bound to
the job P and graph G:

```text
scoring/<P>/repair/<G>/raw.json
scoring/<P>/repair/<G>/structured.json
```

or the exact already-implemented authorized suffix form. There is no P-only
repair authoritative alias, no cross-job same-G sharing, and no scoring rerun.

The reviewed filesystem contract covers both final artifact names and
deterministic temporary-name reopen: descriptor-anchored nested directory
handling, `O_NOFOLLOW` where required, `O_NONBLOCK` for attacker-influenced
artifact-verification reopens, immediate `fstat`, regular-file requirement
before read/hash, FIFO/symlink/directory/special-file rejection, no-clobber
publication, exact orphan adoption, hash/content revalidation, and required
`fsync` durability.

Schema remains `user_version=2` through `002_add_scoring_lineage.sql`. The
final lineage fields are:

- `videos.authoritative_scoring_job_id`
- `jobs.authoritative_scoring_artifact_key`
- `jobs.scoring_success_provenance`
- `jobs.scoring_lineage_version`

For v1 PRIMARY, provenance is `PRIMARY`; for H2-C repair it is `REPAIR_H2C`.
Authority is selected only as `Video -> authoritative scoring Job ->
authoritative structured Artifact`. No J1 -> J2 pointer replacement and no
cross-job graph sharing are authorized.

### Frozen reader and diagnostic contracts

`AuthoritativeScoringReader` / `VerifiedScoringRead` is the authority boundary.
For v1 there is no latest-artifact fallback. Pointerless legacy compatibility is
decided only inside that reader; v1 cannot downgrade into legacy. Analysis,
note, weekly, and reporting consumers must not independently select scoring
authority, and `WeeklyReportService` must not restore an optional
latest-artifact authority fallback.

The final `ErrorCode` set remains exactly ten. The
`TRUST_INTEGRITY_INVALID` H2-C detail family is closed: arbitrary
`H2C_REPLAY_INVALID:<anything>` values are not authorized. The authorized
unknown-generation reason remains `SCORING_LINEAGE_VERSION_INVALID`, with exact
detail `H2C_REPLAY_INVALID:SCORING_LINEAGE_VERSION_INVALID`. Retry behavior
remains `ErrorCode`-based.

### Closed boundaries and next-phase gate

- H1 is **CLOSED**.
- H2-A is **CLOSED**.
- H2-B is **CLOSED**.
- H2-C is **CLOSED**.
- Phase G is **CLOSED WITH AUTHORIZED LINEAGE BOOKKEEPING**. It remains
  accepted/frozen; the already-landed lineage bookkeeping extension is not a
  general reopening, and PRIMARY semantics remain frozen apart from that
  extension.
- Phase I remains **UNAUTHORIZED**. No Phase I design is approved.

Until separately authorized, do not implement cache hardening, cache recovery,
repair cache, cross-job reuse, scoring rerun, retry resurrection, or new
state-machine paths.

**H2-C CLOSEOUT RECORDED**

**H2-C IMPLEMENTATION FROZEN**

**H1 CLOSED**

**H2-A CLOSED**

**H2-B CLOSED**

**H2-C CLOSED**

**PHASE G CLOSED WITH AUTHORIZED LINEAGE BOOKKEEPING**

**PHASE I REMAINS UNAUTHORIZED**

**READY FOR PHASE I DESIGN / AUTHORIZATION**

## Phase I — Cache Hardening / Recovery / Reuse Boundary Design Draft

**SUPERSEDED BY PHASE I DESIGN AMENDMENT ROUND 1 BELOW.** Historical record
only; its durable-reuse statements are not normative.

### Status and scope

**PHASE I DESIGN DRAFTED — IMPLEMENTATION STILL UNAUTHORIZED.**

- Design commit base: `cf72e5dcc47eb7db75be53f3c1e637c8db4145fa`.
- Canonical draft: `docs/TASK-016C-PHASE-I-AUTHORIZATION.md`.
- Selected minimum scope: live, same-job, fully revalidated REPAIR/Judge and
  pre-persistence complete-H2-C-graph evidence reuse only; no PRIMARY cache
  redesign or cross-job cache.
- Frozen decisions: no cross-job reuse, expired-SCORING recovery, terminal Job
  resurrection, migration 003, new ErrorCode, lineage schema change, Phase G
  semantic change, or authoritative-reader bypass.
- This record is a design-status update only. It does not approve a source or
  test change, reopen H1/H2-A/H2-B/H2-C/Phase G, or authorize scoring rerun.

**READY FOR PHASE I DESIGN / AUTHORIZATION INDEPENDENT REVIEW**

**PHASE I IMPLEMENTATION REMAINS UNAUTHORIZED**

## Phase I — Design Amendment Round 1 (durable-reuse proposal superseded)

**DESIGN AMENDMENT DRAFTED — IMPLEMENTATION REMAINS UNAUTHORIZED.**

- The durable-reuse design recorded by `7018c83` is **SUPERSEDED** after
  independent review: no durable pre-Phase-G same-Job graph exists, global
  ProviderCalls cannot prove Job ownership, and durable hits conflict with H1
  admission and fresh-runtime ownership.
- Final selection is **I-B hardening-only**. Current H2-B/H2-C/Phase G is a
  one-pass lexical flow with no meaningful duplicate deterministic consumer or
  duplicate network dispatch to optimize. Phase I must not invent a cache.
- In-frame evidence is limited to the same `RuntimeOperations.scoring_stage`
  invocation, active lexical frame, Job, owner, and valid lease. It permits no
  durable, restart, cross-process, cross-job, PRIMARY, expired-SCORING,
  terminal, ProviderCall, Artifact, orphan, or G reuse.
- H1/H2-A/H2-B/H2-C/Phase G/lineage/reader remain frozen; no migration 003,
  ErrorCode, scoring-admission, Phase G ordering, or persistence change.

**READY FOR PHASE I DESIGN / AUTHORIZATION AMENDMENT ROUND 1 INDEPENDENT REVIEW**

**PHASE I IMPLEMENTATION REMAINS UNAUTHORIZED**

## Phase I — Design Amendment Round 2 (lease-proof boundary correction)

**DESIGN AMENDMENT DRAFTED — IMPLEMENTATION REMAINS UNAUTHORIZED.**

- Current H2-C proves current Job/owner/lease at replay entry, then performs
  replay and trusted-success minting in the same lexical execution. There is
  **no immediate pre-mint lease re-proof** in the frozen implementation.
- I-B hardening-only neither requires nor authorizes adding that check. Existing
  integrity-terminalization stale handling and Phase G's independent
  owner/lease proof before persistence/mutation remain exactly frozen.
- Any future pre-mint lease hardening needs a concrete finding, separate H2-C
  authorization, independent review, focused TDD, and regression evidence.

**READY FOR PHASE I DESIGN / AUTHORIZATION AMENDMENT ROUND 2 INDEPENDENT REVIEW**

**PHASE I IMPLEMENTATION REMAINS UNAUTHORIZED**

## TASK-016C Phase I — Final Closeout / Freeze

### Classification and history

- Final status: **CLOSED — HARDENING AUDIT / NO-OP**.
- Final mode: **I-B — HARDENING ONLY / NO-OP**.
- Design draft `7018c83d6703cd03ef6f56ad206cf211f1d4db55`: independent review
  **REQUEST CHANGES** because durable pre-persistence reuse was mechanically
  unavailable under schema-v2 same-job proof without reopening frozen
  persistence/admission semantics.
- Amendment Round 1 `79b25729cf33ada554db3701f270e0b48d388661`: selected I-B;
  independent review **REQUEST CHANGES** because it inaccurately claimed an
  immediate pre-trusted-success-mint lease re-proof.
- Amendment Round 2 `52a7e4236337f39df199c51ef2badcf4274dd065`: corrected that
  boundary; independent review **APPROVED**. The hardening audit then passed.

Phase I was not skipped. It investigated cache/recovery/reuse hardening and
confirmed that the frozen one-pass architecture already satisfies the approved
contract: one H2-B continuation; one REPAIR admission, dispatch, and
validation; one REPAIR_JUDGE admission, Judge dispatch, and validation; one
H2-C replay; one fresh trusted repair-success mint; and one Phase G
`persist_success`. No meaningful duplicate semantic/network work exists.
Therefore zero production change is the correct Phase I implementation outcome.

### Final frozen contract

- Production changes: **NONE**. Test changes: **NONE**. Schema changes:
  **NONE**. Migration 003: **UNAUTHORIZED / NOT REQUIRED**. New ErrorCode:
  **NONE**.
- Semantic cache: **NOT IMPLEMENTED / NOT AUTHORIZED / NOT REQUIRED**.
  Durable Provider/Judge/graph reuse, ProviderCall cache hits, Artifact cache
  authority, filesystem-orphan or G-only reuse, cross-process/new-runtime/
  restart/cross-job/same-G/request-hash sharing, expired-SCORING recovery,
  terminal resurrection, and PRIMARY semantic reuse: **NO**.
- REPAIR and REPAIR_JUDGE admission are unchanged; existing ProviderCall
  blocking semantics and `scoring_admission.py` are frozen. No cache admission,
  bypass, historical reuse, or second admission semantics was added.
- ProviderCall remains a dispatch/evidence ledger, not cache authority. No
  cache-hit marker, historical semantic reuse, network-skip marker, duplicate
  ProviderCall semantics, or persistence column exists.
- Trusted success remains freshly runtime-minted, exact-type gated, lexically
  passed, non-serialized as authority, and not reconstructed from durable state.
- H2-C replay entry has the existing Job/owner/lease proof. No immediate
  pre-mint re-proof exists or is authorized. Integrity terminalization is
  unchanged; Phase G retains its independent owner/lease proof before
  mutation/persistence. A future pre-mint hardening change needs a concrete
  defect, separate H2-C authorization, independent review, focused TDD, and
  regression proof.
- Crashes before REPAIR, after REPAIR before Judge, after Judge, or after graph
  derivation before Phase G lose in-memory state; there is no Phase I recovery
  and files/orphans remain non-authoritative. During/after Phase G, only frozen
  Phase G rollback/idempotency/committed-read behavior applies.
- Phase G is closed: no early Artifact/ProviderCall persistence, pre-Phase-G
  evidence table, second persistence seam, atomic-ordering change, or lineage
  change. PREWRITE_VALIDATE, no-clobber, SQLite transaction, lineage, Job/Video
  CAS, and rollback/re-proof remain frozen.
- Filesystem protections remain reachable and unchanged: descriptor anchoring,
  `O_NOFOLLOW`, `O_NONBLOCK` where required, immediate `fstat`, regular-file
  requirement, FIFO/symlink/special-file rejection, no-clobber, and orphan
  handling. No Phase I filesystem path was added.
- `AuthoritativeScoringReader` and `VerifiedScoringRead` remain the frozen
  persisted/downstream authority boundaries; no read cache or authority bypass
  exists. Schema remains `user_version = 2`, lineage remains
  `task016c-scoring-lineage-v1`, legacy NULL and unknown-generation fail-closed
  behavior remain frozen, and Video -> Job -> Artifact authority is unchanged.

### Independent audit evidence (not rerun by this documentation closeout)

| Check | Result |
|---|---|
| Focused tests | 278 passed |
| Full pytest | 1761 passed; 1 pre-existing Pydantic serializer warning |
| mypy | PASS; 31 source files; no issues |
| Ruff | PASS |
| Security scan | PASS / `status=clean`; existing WARN-only findings |
| `git diff --check` | PASS |
| Worktree | Clean |

H2-C self-consistent forgery defenses remained PASS for RepairProviderEvidence
plus matching ProviderCall, JudgeEvidence plus matching ProviderCall, forged
`judge_h2`, and provider/model/prompt/schema mutations. No production defect,
meaningful test gap, or missing Phase I regression was found.

### Final gate

H1, H2-A, H2-B, and H2-C are **CLOSED**. Phase G is **CLOSED WITH PREVIOUSLY
AUTHORIZED LINEAGE BOOKKEEPING**. Phase I is **CLOSED — HARDENING AUDIT /
NO-OP**. No semantic cache/recovery phase is pending under TASK-016C.

Any future durable cache, Provider/Judge response reuse, restart/cross-process/
cross-job/same-G/expired-SCORING recovery, terminal resurrection, PRIMARY reuse,
persistent cache state, migration 003, admission/ProviderCall/lineage/
AuthoritativeScoringReader/Phase G ordering change requires new explicit
authorization. This closeout authorizes none of it.

**PHASE I CLOSEOUT RECORDED**

**PHASE I HARDENING AUDIT FROZEN**

**PHASE I NO-OP DETERMINATION FROZEN**

**NO PRODUCTION CHANGE REQUIRED**

**NO TEST CHANGE REQUIRED**

**TASK-016C IMPLEMENTATION PHASES COMPLETE**

**READY FOR TASK-016C FINAL INTEGRATION / RELEASE READINESS REVIEW**

## Phase H2-C — Implementation Correction Round 3 (two P0 trust-chain breaks)

### Metadata and scope

- Task: fix ONLY the two P0 authoritative-reader trust-chain findings
  (Correction Round 3 base `1477fb0`).
- Correction Round 3 base SHA: `1477fb0`; final fix SHA: `1572142`.
- Status: `READY FOR H2-C IMPLEMENTATION CORRECTION ROUND 3 INDEPENDENT REVIEW`.
- P0 findings fixed: P0-1 (REPAIR request identity derived partly from mutable
  RepairProviderEvidence metadata), P0-2 (incomplete REPAIR_JUDGE binding).
  All PASS areas preserved; no H1/H2-A/H2-B, schema/migration, ErrorCode,
  filesystem, weekly-authority, scoring-rerun, cross-job, or Phase I changes.

### Correction commits

1. `1572142` fix(task016c): bind repair and judge identity to sealed semantics

### Changed files

- Production: `src/youtube_intel/scoring.py`
- Tests: `tests/integration/test_task016c_phase_h2c_persistence.py`

### P0-1 — REPAIR trust chain (sealed RepairNormalizedInput is truth)

- Sealed fields used as truth: `RepairNormalizedInput.operation`,
  `repair_provider`, `repair_model`, `repair_model_digest`,
  `repair_prompt_version`, `repair_schema_version`, `output_language`,
  `temperature`, `max_output_tokens`, `max_description_chars`.
- Derived normalized-input root: `repair_normalized_input_hash(sealed_rni)`,
  compared to the persisted `normalized_input_hash` claim.
- Cross-checked duplicated RepairProviderEvidence claims: operation, provider,
  model, model_digest, prompt_version, operation_schema_version,
  output_language, temperature, max_output_tokens, max_description_chars —
  each must equal the sealed RNI value before any builder use.
- Derived REPAIR ProviderCall identity: `build_provider_request_hash(operation,
  normalized_input_hash=derived_root, provider, model, prompt_version,
  schema_version)` with every field from the sealed RNI; compared to the
  persisted `request_hash` claim.
- Persisted REPAIR ProviderCall comparison: status/operation/provider/model/
  prompt_version/schema_version/request_hash/response_artifact_id all compared
  against the sealed-derived truth.
- R chain: sealed RNI -> derived root -> derived request identity -> verified
  evidence claims -> verified persisted ProviderCall -> R.
- Forgery tests (each confirmed RED pre-fix, GREEN post-fix): forged
  evidence model / provider / prompt_version / schema_version with
  consistently recomputed request hash + matching persisted ProviderCall +
  re-bound downstream graph. (operation is a Literal on both RNI and evidence,
  so no distinct forgery exists for it.)

### P0-2 — JUDGE trust chain (sealed QualityJudgeOperationInput is truth)

- Sealed semantic root: `quality_evidence.judge_operation_input`; the two
  sealed operation-input copies (quality-evidence and judge-evidence) are
  required equal.
- Derived Judge H1 and H2 via `build_judge_h1_h2(sealed_judge_input)`.
- judge_h1 comparisons: derived H1 vs `quality_evidence.judge_h1` and vs
  `judge_evidence.judge_h1`.
- judge_h2 comparisons: derived H2 vs `quality_evidence.judge_h2` AND vs
  `judge_evidence.judge_h2` (the previously missing check).
- Duplicated JudgeEvidence metadata cross-checks against the sealed operation
  input: operation, provider, model, model_digest, policy_version,
  prompt_version, operation_schema_version.
- Derived REPAIR_JUDGE ProviderCall identity: the derived H2 (which binds the
  sealed judge provider/model/prompt/schema); persisted REPAIR_JUDGE
  ProviderCall compared against the sealed-derived identity.
- J chain: sealed operation input -> derived H1/H2 -> verified JudgeEvidence
  claims -> derived REPAIR_JUDGE identity -> verified persisted ProviderCall
  -> J -> fed into G.
- Forgery tests (RED pre-fix, GREEN post-fix): forged JudgeEvidence.judge_h2
  claim; forged JudgeEvidence model / provider / prompt_version /
  schema_version each with matching persisted REPAIR_JUDGE ProviderCall and
  re-bound downstream graph.

### GRAPH / circular trust

- Final chain: sealed semantics -> R/J -> E/S/G. G inputs are p (verified vs
  result.request_hash), derived R, derived J, recomputed settings hash,
  recomputed E, sealed structured content hash — all verified values.
- Confirmed no code path uses evidence metadata as request-hash builder input
  or trusts judge_h2 without derived-H2 comparison.

### Preservation confirmation

- Temp-file O_NONBLOCK fix, final-name FIFO fix, closed-detail fix, weekly
  required reader, schema v2, generation, H1/H2-A/H2-B, repair eligibility,
  admission ordering, 23-step replay, settings provenance,
  RepairPersistenceGraphIdentityV2 / E/S/G / G paths, filesystem no-clobber,
  lineage persistence, Job/Video CAS, legacy reader, analysis/note/weekly/
  reporting authority, retry policy, state machine, no rerun, no cross-job,
  Phase I absent — all unchanged and green.

### Gates

- Pre-fix RED proof: pre-fix production reader accepts all nine forgeries
  (verified directly).
- Post-fix GREEN: all nine forgery tests fail closed; full persistence suite
  53 passed.
- Full `pytest tests/unit tests/integration tests/e2e`: 1761 passed, 1
  pre-existing Pydantic serializer warning.
- `mypy src`: Success, no issues in 31 source files. `ruff check .`: All
  checks passed. `git diff --check`: clean. `scripts/security_scan.sh`:
  status=clean (pre-existing WARNs unchanged).

### Remaining concerns

- None blocking; both P0 trust-chain breaks fixed with self-consistent forgery
  RED tests first and no PASS area regressed.

## Phase H2-C — Implementation Correction Round 2 (two remaining P1 findings)

### Metadata and scope

- Task: fix ONLY the two independently reviewed remaining P1 findings on the
  H2-C implementation (Correction Round 2 base `a46fa75`; original
  implementation base `59bcf28`).
- Correction Round 2 base SHA: `a46fa75`; final HEAD SHA: `a70a2e9`.
- Status: `READY FOR H2-C IMPLEMENTATION CORRECTION ROUND 2 INDEPENDENT REVIEW`.
- P0 findings: NONE. All Correction Round 1 PASS areas preserved (closed-detail
  enforcement, final-name FIFO/special-file rejection, weekly authoritative
  reader, 20-reason closed set, schema v2, ErrorCode count). No H1/H2-A/H2-B,
  schema/migration, scoring rerun, cross-job sharing, or Phase I changes.

### Correction commits

1. `4b1ccd1` fix(task016c): harden repair temp verification against special files
2. `a70a2e9` fix(task016c): rederive repair request roots in authoritative reads

### Changed production files

- `src/youtube_intel/scoring.py` (both fixes)

### Changed test files

- `tests/integration/test_task016c_phase_h2c_persistence.py` (both fixes)

### FIX 1 — temporary verification reopen FIFO race

- Old vulnerable reopen: after write/fsync/close of the deterministic `.tmp`
  name, the verification reopen used `os.open(..., O_RDONLY | O_NOFOLLOW)`
  without `O_NONBLOCK` and without an immediate regular-file check; a
  close->reopen replacement with a FIFO could block.
- Corrected open flags: descriptor-relative `O_RDONLY | O_NOFOLLOW |
  O_NONBLOCK`; the nonblocking open cannot block on a FIFO.
- Descriptor anchoring: the reopen remains `dir_fd`-anchored to the validated
  repair G directory (no path-string reopening); directory traversal and
  no-clobber/orphan-adoption unchanged.
- Immediate fstat: `fstat(opened_fd)` is required to be `S_ISREG` BEFORE any
  read/hash/content verification; FIFO/socket/device/directory/symlink are
  rejected fail-closed through the existing filesystem-integrity error path
  (no new ErrorCode/detail), with descriptor cleanup preserved.
- Tests: deterministic `os.open`-hook replacement-race coverage (no timing
  sleeps) for the raw and structured temporary names with FIFO/symlink/
  directory replacements, run under a bounded worker proving no hang and no
  leftover blocked thread, plus a normal temporary verification success
  regression; the final-name FIFO regressions and orphan-adoption/no-clobber
  behaviors remain green.

### FIX 2 — repair reader must rederive request roots

- Exact sealed REPAIR semantic input used: the sealed `normalized_input`
  (RepairNormalizedInput) embedded in the repair provider evidence.
- Exact REPAIR normalized-input canonicalization: H2 JCS canonical bytes via
  `repair_normalized_input_hash(normalized_input)`.
- Exact rederived normalized-input hash compared to the persisted
  `normalized_input_hash` claim (mismatch fails closed).
- Exact REPAIR request-hash rederivation: `build_provider_request_hash` from
  the rederived root + sealed operation/provider/model/prompt/schema; compared
  to the persisted `request_hash` claim.
- Exact sealed Judge semantic input: the sealed `judge_operation_input`
  (QualityJudgeOperationInput) embedded in the repair quality evidence.
- Exact Judge H1 canonicalization and rederivation: `build_judge_h1_h2(
  judge_operation_input)`; rederived H1 compared to the persisted `judge_h1`
  claims (quality-evidence and judge-evidence copies) and rederived H2
  compared to the persisted `judge_h2` claim.
- Exact REPAIR_JUDGE request-hash rederivation: from the rederived Judge H1
  via `build_judge_h1_h2`'s H2; the persisted ProviderCall is compared to the
  rederived R/J.
- R/J downstream relationship: G identity and the persisted REPAIR/
  REPAIR_JUDGE ProviderCall checks use the rederived R/J, keeping the chain
  sealed inputs -> derived roots -> request identities -> R/J -> E/S/G acyclic.
- Persisted roots are claims, not trust anchors; no network is used (pure
  canonicalization/hash).

### FIX 2 corruption tests

- Corrupted sealed repair normalized-input (semantic) with unchanged stored
  roots -> fail closed (confirmed RED without the fix).
- Corrupted stored repair normalized-input-root claim -> fail closed.
- Corrupted stored Judge H1 claim -> fail closed.
- Corrupted sealed Judge operation input (semantic) with unchanged stored H1
  -> fail closed (confirmed RED without the fix).
- Existing Round 1 ProviderCall corruption tests (REPAIR and REPAIR_JUDGE
  provider/model/prompt/schema/request/response) and the valid REPAIR_H2C
  authoritative read all remain green.

### Preservation confirmation

- Closed-detail correction (Fix 1, Round 1) still PASS; final-name FIFO
  correction still PASS; weekly authority correction still PASS.
- Schema unchanged (migrations `001`,`002`; no `003`); `scoring_admission.py`
  unchanged; ErrorCode/detail set unchanged; no rerun; no cross-job sharing;
  Phase I absent.

### Gates

- H2-C focused suites (schema/data-layer/persistence/runtime/weekly): 97 passed.
- Full `pytest tests/unit tests/integration tests/e2e`: 1752 passed, 1
  pre-existing Pydantic serializer warning.
- `mypy src`: Success, no issues in 31 source files. `ruff check .`: All checks
  passed. `git diff --check`: clean. `scripts/security_scan.sh`: status=clean
  (pre-existing high-entropy/wheel-license WARNs unchanged).

### Remaining concerns

- None blocking; both remaining P1 findings fixed with focused RED tests first
  and no review-PASS area regressed.

## Phase H2-C — Implementation Correction Round 1 (four P1 findings)

### Metadata and scope

- Task: fix ONLY the four independently reviewed P1 findings on the approved
  H2-C implementation (reviewed HEAD `02f397f`, authorization base `59bcf28`).
- Correction base SHA: `02f397f`; final HEAD SHA: `6cb84e9`.
- Status: `READY FOR H2-C IMPLEMENTATION CORRECTION ROUND 1 INDEPENDENT REVIEW`.
- P0 findings: NONE. All review-PASS areas preserved; no H1/H2-A/H2-B/schema
  semantics reopened; no scoring rerun, cross-job sharing, Phase I, or
  ErrorCode/detail-policy expansion.

### Correction commits

1. `39f3a8f` fix(task016c): enforce closed H2-C replay diagnostics
2. `7ed55ee` fix(task016c): reject final repair special files safely
3. `0395d09` fix(task016c): bind repair provider calls in authoritative reads
4. `6cb84e9` fix(task016c): require verified scoring reads for weekly reports

### Changed production files

- `src/youtube_intel/runtime.py` (Fix 1)
- `src/youtube_intel/scoring.py` (Fix 2, Fix 3)
- `src/youtube_intel/reporting.py` (Fix 4)

### Changed test files

- `tests/unit/test_task016c_phase_h2c_runtime.py` (Fix 1)
- `tests/integration/test_task016c_phase_h2c_persistence.py` (Fix 2, Fix 3)
- `tests/integration/test_task016c_phase_h2c_weekly.py` (new; Fix 4)
- `tests/integration/test_weekly_report.py` (Fix 4 wiring)
- `tests/e2e/test_mvp_flow.py` (Fix 4 wiring)

### FIX 1 — closed H2C_REPLAY_INVALID details

- Previous bypass: `_H2CReplayInvalid` accepted any string and runtime
  formatted `"H2C_REPLAY_INVALID:" + reason` directly.
- Final mechanism: `_H2CReplayInvalid.__init__` validates the reason against
  the approved closed `H2C_REPLAY_INVALID_REASONS` set (arbitrary reason raises
  before any terminal emission), and every emission path routes through the
  single `h2c_replay_invalid_detail(reason)` helper (unknown-generation,
  settings-bound, envelope-oversize, and replay-invalid terminals).
- Reason set unchanged (20 reasons incl. `SCORING_LINEAGE_VERSION_INVALID`).
- Tests: constructor closed-set rejection; every reason -> exact qualified
  detail; two LIVE production terminal-path tests proving emission through the
  closed helper and that the old unqualified detail is never emitted.

### FIX 2 — final-name FIFO / special-file safe inspection

- Previous blocking mechanism: `_repair_orphan_state` opened `raw.json` /
  `structured.json` with `O_RDONLY | O_NOFOLLOW` before fstat; opening a FIFO
  could block (O_NOFOLLOW does not prevent FIFO blocking).
- Final strategy: descriptor-relative `stat(..., follow_symlinks=False)` type
  check BEFORE any read open, then `O_NOFOLLOW | O_NONBLOCK` open + fstat
  regular-file confirmation. Race-safe: a name swapped between stat and open
  cannot block and cannot pass as a regular file.
- Post-publication reopen in `_write_repair_final_in_directory` also uses
  `O_NOFOLLOW | O_NONBLOCK` + fstat regular-file check.
- Symlink protection (O_NOFOLLOW) and no-clobber/orphan-adoption unchanged.
- Tests: final-name raw FIFO and structured FIFO rejected quickly via a bounded
  daemon-thread guard (fails if a blocking open occurs); final-name symlink and
  directory rejected; exact-orphan adoption, conflicting regular-file, and
  no-clobber publication regressions all hold.

### FIX 3 — repair ProviderCall identity revalidation

- Reader now re-proves persisted REPAIR / REPAIR_JUDGE ProviderCalls against
  the sealed envelope evidence (not merely status/operation/response artifact).
- REPAIR fields validated: status, operation, provider, model, prompt_version,
  operation_schema_version, request_hash == sealed R + recomputed
  build_provider_request_hash binding normalized_input_hash (RNI hash),
  response_artifact_id == raw artifact id.
- REPAIR_JUDGE fields validated: status, operation, provider, model,
  prompt_version, operation_schema_version, request_hash == sealed J +
  recomputed build_provider_request_hash binding Judge H1, response_artifact_id.
- Tests: twelve one-field-at-a-time corruption cases (REPAIR and REPAIR_JUDGE x
  provider/model/prompt_version/schema_version/request_hash/response_artifact)
  each fail the authoritative read closed; valid repair-read happy path holds.

### FIX 4 — weekly must not own scoring authority

- Removed/constrained fallback: `scoring_reader` is now a required
  WeeklyReportService argument; the `_verified_score` latest-artifact
  authority helper is deleted; `_verified_item` resolves every weekly score
  only via the reader's VerifiedScoringRead.
- Legacy NULL-pointer compatibility lives inside
  `AuthoritativeScoringReader._read_legacy`, not in weekly.
- Production wiring: `runtime.weekly` injects the authoritative reader.
- Tests: construction without a reader raises TypeError; corrupted latest
  artifact cannot influence weekly when the reader resolves the pointer
  artifact; v1 PRIMARY, v1 REPAIR_H2C, and legacy NULL-pointer weekly all
  succeed through VerifiedScoringRead; production wiring provides a callable
  reader. test_weekly_report.py formatting tests inject a VerifiedScoringRead
  stub (post-verification rendering); e2e harness passes a real reader.

### Regressions and gates

- H1 admission, H2-B repair flow/correction, Phase G, H2-C focused
  (schema/data-layer/persistence/runtime), state-store, pipeline, and
  reporting/weekly suites all pass.
- Full `pytest tests/unit tests/integration tests/e2e`: 1743 passed, 1
  pre-existing Pydantic serializer warning.
- `mypy src`: Success, no issues in 31 source files. `ruff check .`: All checks
  passed. `git diff --check`: clean. `scripts/security_scan.sh`: status=clean
  (pre-existing high-entropy/wheel-license WARNs unchanged).

### Non-scope confirmation

- `scoring_admission.py` diff: EMPTY (unchanged).
- No schema change (migrations remain `001`, `002`; no `003`).
- No ErrorCode/detail-policy expansion (ErrorCode still exactly ten; reason set
  unchanged).
- No scoring rerun, no cross-job graph sharing, Phase I still absent.

### Remaining concerns

- None blocking; all four P1 findings fixed with focused RED tests first and no
  review-PASS area regressed.

## Phase H2-C — Trusted repair execution and authoritative scoring lineage (implementation)

### Metadata and scope

- Task: `TASK-016C Phase H2-C` implementation per the fully approved final
  authorization (amendment `59bcf28`), the Round-6 authoritative scoring
  lineage authorization, and the authoritative-G schema authorization.
- Base HEAD: `59bcf28` (worktree clean, required ancestry verified).
- Implementation base SHA: `59bcf28`; final HEAD SHA: `ddd0a3c`.
- Status: `READY FOR H2-C IMPLEMENTATION INDEPENDENT REVIEW`.
- Phase I: NOT implemented. No scoring rerun, no cross-job graph sharing, no
  cache/recovery, no merge/push/tag/rebase/reset/squash.

### Implementation commits

1. `e5031e8` feat(task016c): add scoring lineage schema v2
2. `ef3df66` feat(task016c): implement H2-C repair execution and lineage persistence
3. `e1488c9` feat(task016c): add authoritative scoring readers
4. `ddd0a3c` test(task016c): close H2-C generation decision and replay matrix

### Changed production files

- `src/youtube_intel/migrations/002_add_scoring_lineage.sql` (new)
- `src/youtube_intel/state.py`
- `src/youtube_intel/scoring.py`
- `src/youtube_intel/runtime.py`
- `src/youtube_intel/pipeline.py`
- `src/youtube_intel/reporting.py`
- `src/youtube_intel/h2_evidence.py`
- `src/youtube_intel/domain.py`
- `src/youtube_intel/providers/subtitles.py`
- `src/youtube_intel/transcripts.py`

Unchanged (frozen): `scoring_admission.py` (H1 guard), `quality.py`, `jobs.py`,
Phase G `TrustedPersistenceEntry.persist_success` PRIMARY internals (additive
lineage bookkeeping only), legacy `scoring/<P>/raw(.json)` /
`scoring/<P>/structured(.json)` PRIMARY paths.

### SCHEMA (migration 002)

- Applied via the ordered loader (`001` then `002`); final `PRAGMA user_version`
  = 2; history rows `(1, 001_initial.sql)`, `(2, 002_add_scoring_lineage.sql)`.
- Added exactly four nullable columns:
  `videos.authoritative_scoring_job_id -> jobs(job_id) ON DELETE RESTRICT`,
  `jobs.authoritative_scoring_artifact_key -> artifacts(artifact_key) ON DELETE
  RESTRICT`, `jobs.scoring_success_provenance` CHECK `('PRIMARY','REPAIR_H2C')`,
  `jobs.scoring_lineage_version` CHECK `(NULL | 'task016c-scoring-lineage-v1')`.
- Two partial UNIQUE indexes: `uq_jobs_authoritative_scoring_artifact_key`,
  `uq_videos_authoritative_scoring_job_id`.
- No historical backfill; migrated rows stay NULL (pre-lineage generation).
  Unsupported schema versions fail closed; doctor `_database_check` accepts
  exactly version 2.

### GENERATION

- Repository derives `scoring_lineage_version` at `create_job` (VIDEO_STAGE +
  SCORING → `task016c-scoring-lineage-v1`, else NULL); caller cannot submit or
  change it (no parameter; immutable after creation).
- Post-H2-B-PASS generation decision point: NULL → frozen
  `CAPABILITY_UNAVAILABLE`/`H2B_PASS_AWAITING_H2C` terminal; v1 → H2-C entry;
  unknown non-NULL → `TRUST_INTEGRITY_INVALID` +
  `H2C_REPLAY_INVALID:SCORING_LINEAGE_VERSION_INVALID` terminal. The schema
  CHECK admits only NULL/v1 at write time, so the unknown state is defensive and
  tested via read-time override.

### H2-C

- Entry point: lexical continuation inside the actual SCORING frame,
  immediately after the local H2-B aggregate (runtime-only; no caller ingress).
- Trust roots: current job/owner/active lease, original `ScoringInput`, rebuilt
  `PrimaryTrustedContext`, validated settings, runtime quality authority, and
  the untrusted aggregate.
- Eligible failure classes: `SCHEMA_OR_PARSE_INVALID`, `LANGUAGE_INVALID`,
  `JUDGE_REJECT`, `JUDGE_UNCERTAIN` (UNKNOWN/other reject).
- 23-step no-network replay re-derives every security-significant value and
  mints `PhaseHTrustedRepairSuccess`; zero `/api/tags`, `/api/generate`,
  provider-factory, or Judge network contact.
- Settings provenance `H2CSettingsProvenance` (30 fields) + admission ceilings
  (`max_transcript_chars <= 131072`, `max_output_tokens <= 2147483647`,
  provenance bytes `<= 8192`) → `SETTINGS_BOUND_EXCEEDED`.
- REPAIR/REPAIR_JUDGE admission precedes dispatch (unchanged H1 state-only
  consumption); provider evidence and Judge evidence exact.

### GRAPH

- `RepairPersistenceGraphIdentityV2` (14 fields, `task016c-repair-persistence-
  graph-v2`); `G = SHA256(H2-JCS(identity))`.
- `E = SHA256(envelope_bytes)`, `S = SHA256(structured_bytes)`; neither depends
  on G (no circularity). Envelope carries neither G nor artifact key/path.
- G-based paths: `scoring/<P>/repair/<G>/raw(.json)` and
  `scoring/<P>/repair/<G>/structured(.json)`; no P-only repair alias.

### FILESYSTEM

- Descriptor-anchored nested directory creation (`scoring/<P>/repair/<G>`),
  no-follow/no-special-file, fsync parent+child, no-clobber link promotion,
  exact-orphan adoption, symlink/FIFO rejection, reopen hash/length verify.

### LINEAGE

- v1 PRIMARY success: additive `PRIMARY` provenance + structured-key pointer +
  Video pointer (atomic, same transaction); pre-v2 NULL-generation PRIMARY
  writes no lineage fields.
- Repair success: `REPAIR_H2C` provenance + G-based structured-key pointer +
  Video pointer.
- Job/Video lineage CAS with tx-local zero-row classification
  (`_read_job_in_transaction`/`_read_video_in_transaction`), rollback before
  fail_job, lease re-proof, exactly-one fail_job terminalization, and same-graph
  idempotency. Pre-commit orphans invisible; post-commit complete graph visible.

### READERS

- `VerifiedScoringRead` + `AuthoritativeScoringReader` (sole scoring
  selector/verifier). Non-NULL pointer → v1 lineage branch (PRIMARY or
  REPAIR_H2C with full P/R/J/E/S/G verification); pointerless → legacy branch
  requiring a NULL-generation SCORING job (no v1 downgrade).
- `_load_scoring` delegates to the reader; independent
  `_validate_scoring_provenance` reconstruction removed; weekly consumes
  `VerifiedScoringRead` via injected reader.

### ERRORS

- Final `ErrorCode` count: exactly ten (added `TRUST_INTEGRITY_INVALID`).
- Closed `H2C_REPLAY_INVALID:<REASON>` set (20 reasons);
  `h2c_replay_invalid_detail` rejects arbitrary/unqualified reasons.
- Retry exclusion is code-only for `TRUST_INTEGRITY_INVALID` and
  `CAPABILITY_UNAVAILABLE`.

### NON-SCOPE confirmation

- `scoring_admission.py` unchanged (zero diff). No scoring rerun
  (`TRANSCRIPT_READY -> SCORED` only, no second SCORING job for a scored
  video). No cross-job same-G sharing (unique Job-key index + Artifact
  ownership). Phase I absent (no cache/recovery/resume).

### Evidence (gate results)

- Full `uv run --offline pytest tests/unit tests/integration tests/e2e`:
  1714 passed, 1 pre-existing Pydantic serializer warning.
- Focused H2-C suites: schema (19), data layer (18), persistence boundary (16),
  runtime decision/replay (6).
- `uv run --offline mypy src`: Success, no issues in 31 source files.
- `uv run --offline ruff check .`: All checks passed.
- `git diff --check`: clean. `bash scripts/security_scan.sh`: status=clean
  (pre-existing high-entropy/wheel-license WARNs unchanged).
- Coherently updated frozen tests whose committed-graph semantics are now
  lineage-aware: Phase G R2 corruption/idempotency (→
  `H2CAuthoritativeGraphConflict`), H2-B flow/correction full-PASS tests (→
  H2-C success or pre-lineage capability terminal).

### Remaining concerns

- The unknown non-NULL generation branch is defensive: the schema CHECK admits
  only NULL/v1 at write time, so it is exercised via read-time override.
- `AuthoritativeScoringReader` PRIMARY verification matches the frozen
  `_validate_scoring_provenance` strictness (producer/provider/model/prompt/
  schema/raw/config checks).
- No other open items; all approved H2-C objectives implemented and tested.

## Phase H2-B — Final correction implementation (Round 5 + capability policy)

### Metadata and scope

- Task: `TASK-016C Phase H2-B` FINAL additive correction, per the approved
  Round 5 provider semantic-boundary authorization
  (`d0af25a`), the approved `CAPABILITY_UNAVAILABLE` staged-terminal policy
  (`4639f33`), and the approved exhaustive consumer scope completion
  (`a674370`). Base HEAD: `a674370` (worktree clean, required ancestry
  verified). Additive only; rejected/corrected lineage `c8a6e04` /
  `5e8f046` / `787a682` / `288602d` retained unchanged; no history rewrite.
- Status: `READY FOR H2-B FINAL CORRECTION IMPLEMENTATION INDEPENDENT REVIEW`.
- H2-C: NOT implemented, NOT authorized. No `PhaseHTrustedRepairSuccess`, no
  REPAIR persistence, no merge/push/tag.

### What was corrected (approved objectives)

1. Removed the independently callable semantic REPAIR provider API
   (`OllamaScoringProvider.dispatch_exact_repair_generate`) — no rename, no
   wrapper. Replaced by the role-neutral `dispatch_exact_generate(body,
   body_sha256, body_length) -> bytes` (payload integrity check, `/api/tags`
   preflight, exact POST, raw outer bytes returned uninterpreted; accepts no
   PFE/admission/role/flag/callback and establishes no role meaning).
2. Removed the independently callable semantic REPAIR_JUDGE provider API
   (`OllamaQualityJudgeProvider.judge_exact_model_content`) — replaced by the
   same role-neutral `dispatch_exact_generate` on the judge provider (loopback
   revalidation, payload integrity, strict tags preflight, raw outer bytes),
   plus the pure frozen payload builder `build_quality_judge_generate_body`
   (byte-for-byte the legacy judge payload; `_generate` refactored onto it).
   The judge provider's `_request_json` factored into behavior-identical
   `_request_raw_body` + JSON interpretation.
3. RuntimeOperations remains the sole semantic H2-B boundary: the lexical
   `scoring_stage` closure consumes state-only roles, revalidates identity and
   payload (now including the Judge payload — payload-level J-to-J), invokes
   role-neutral transport, and alone interprets the returned raw as the
   admitted REPAIR / REPAIR_JUDGE attempt (strict outer capture + model
   content extraction at the runtime frame; ambiguity → UNKNOWN).
4. Removed RuntimeOperations aggregate retention
   (`_last_h2b_validated_repair_result` deleted; no getter/dict/cache/registry/
   module global). The aggregate is constructed as a lexical local only.
5. Exact H2-B-only PASS transitional terminalization: after complete valid
   H2-B success and local aggregate construction,
   `fail_job(ErrorCode.CAPABILITY_UNAVAILABLE, "H2B_PASS_AWAITING_H2C",
   retry_at=None)` → `FAILED_FINAL` → `StageDisposition.TERMINAL`, exactly one
   `fail_job`, zero generic `_fail`, zero persistence, no SUCCEEDED job. The
   aggregate is then discarded with the frame; a future separately authorized
   H2-C will replace exactly this terminalization (no hook/placeholder added).
6. `RuntimeOperations.retry()` excludes CAPABILITY_UNAVAILABLE jobs by the
   ErrorCode predicate alone (never detail) before `rerun_job`/`process()`.
7. `ErrorCode.CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"` added to
   `domain.py` (exactly one member; no other domain change; no migration —
   error codes persist as unconstrained TEXT).
8. Exhaustive ErrorCode consumers completed: `subtitles.py
   _safe_boundary_error()` dict entry `f"{subject} required capability
   unavailable in this build"`; `transcripts.py _adapter_boundary_error()`
   explicit branch `detail = "required capability unavailable in this build"`
   before the LOCAL_RESOURCE else. All existing mappings unchanged.
9. Contract test updated to the exact nine-code set (still an exact set
   assertion).

### Changed files (authorized scope only)

- `src/youtube_intel/domain.py` — one ErrorCode member.
- `src/youtube_intel/runtime.py` — role-neutral dispatch call sites, Judge
  payload derivation + payload-level J-to-J revalidation, runtime-side Judge
  outer capture/extraction, aggregate retention removal, transitional
  terminalization, retry exclusion.
- `src/youtube_intel/providers/ollama.py` — semantic APIs removed; role-neutral
  transport on both providers; judge payload builder; `_request_raw_body`
  factoring.
- `src/youtube_intel/providers/subtitles.py` — one exhaustive mapping entry.
- `src/youtube_intel/transcripts.py` — one explicit branch.
- Tests: new `tests/unit/test_task016c_phase_h2b_final_correction.py`
  (provider composition attacks with REAL providers + fake transport, manual
  raw-injection attacks, transitional PASS semantics, retry exclusion incl.
  altered-detail/same-detail-different-code/mixed/repeated/only-candidate,
  aggregate exposure scans, constructed-aggregate persistence rejection,
  subtitle/transcript boundary tests); updated seams (role-neutral transport
  tests, semantic-API absence), flow (transitional PASS assertions,
  lexical-aggregate persistence coverage), authority (lexical aggregate), and
  contract (nine codes) test files.

### Frozen files confirmed unchanged (zero diff)

`src/youtube_intel/scoring.py`, `src/youtube_intel/state.py`,
`src/youtube_intel/pipeline.py`, `migrations/`, Phase G persistence,
`scoring_admission.py` / `quality.py` / `h2_evidence.py` (unchanged this
round; their Round 4 correction state is retained).

### Stop-boundary confirmation

Role-neutral transport: YES. RuntimeOperations sole semantic boundary: YES.
State-only admission: YES. Lexical-only aggregate: YES. Transitional PASS
(CAPABILITY_UNAVAILABLE + H2B_PASS_AWAITING_H2C + retry_at=None + FAILED_FINAL
+ TERMINAL, fail_job once): YES. Retry exclusion by code only: YES. Nine-code
exact set: YES. PhaseHTrustedRepairSuccess: NO. H2-C: NO. REPAIR persistence:
NO. SUCCEEDED job for H2-B PASS: NO. h2c_callback/post_repair_hook: NO.

### Evidence (gate results)

- Focused H2-B suites (flow + seams + correction authority/finalizer + final
  correction + contracts): 208 passed.
- Full `uv run --offline pytest tests/unit tests/integration`: 1646 passed,
  1 pre-existing Pydantic serializer warning.
- `uv run --offline pytest tests/e2e`: 9 passed.
- `uv run --offline mypy src`: Success, no issues in 31 source files.
- `uv run --offline ruff check .`: All checks passed.
- `git diff --check`: clean. `bash scripts/security_scan.sh`: status=clean
  (pre-existing wheel-license WARN unchanged).
- Manual source searches: `dispatch_exact_repair_generate`,
  `judge_exact_model_content`, `dispatch_repair`, `execute_repair`,
  `run_exact_repair`, `send_admitted_repair`, `_h2b_validated_repair_result`,
  `last_h2b_result`, `h2b_result`, `h2c_callback`, `post_repair_hook`,
  `h2c_finalize`, `persist_repair`, `finalize_repair`, `mint_repair_success`,
  `verify_h2b_result` — none found. `repair_generate` matches only the pure
  frozen payload serializer `build_task016c_repair_generate_body` (data
  construction; no transport/admission/role semantics).
  `PhaseHTrustedRepairSuccess` appears only in a comment stating it is not
  minted.
- Exhaustive ErrorCode consumer audit: only the two authorized boundary
  consumers enumerate the taxonomy; both now map CAPABILITY_UNAVAILABLE
  safely. All other occurrences are specific producers/narrow equality checks
  (no KeyError, no LOCAL_RESOURCE misclassification); `obsidian.py`
  filesystem classifier is unaffected (CAPABILITY_UNAVAILABLE is not a
  filesystem input).

### Remaining concerns

- The staged terminal `CAPABILITY_UNAVAILABLE` + `H2B_PASS_AWAITING_H2C` is
  intentionally final for this build: historical FAILED_FINAL records remain
  terminal after any future H2-C upgrade (H2-C operates only on a live
  same-runtime lexical aggregate; no resurrection code exists now).
- No other open items; all approved objectives implemented and tested.

## Phase H2-B — Correction implementation (Round 4 authorization)

### Metadata and scope

- Task: `TASK-016C Phase H2-B` CORRECTION implementation only, per the fully
  approved Round 4 authorization amendment
  (`cc7ba59ca143fc08be5ecfbf1ee5401d225cb1a3`). Additive correction of the
  rejected implementation `c8a6e04` / `5e8f046`; no history rewrite, no
  reset/rebase/squash/amend, no H2-C, no `PhaseHTrustedRepairSuccess`, no
  repair persistence.
- Base HEAD: `cc7ba59` (worktree clean, required ancestry verified).
- Status: `READY FOR H2-B CORRECTION IMPLEMENTATION INDEPENDENT REVIEW`.

### What was corrected (frozen objectives)

1. Removed the generic caller-controlled identity+callback dispatch authority
   `ScoringDispatchAdmission._consume_runtime_role_and_dispatch` entirely (no
   rename, no double-underscore, no wrapper). `scoring_admission.py` is now
   state/policy enforcement only.
2. Removed the caller-triggerable authoritative `_h2b_execute_repair(...)`
   execution seam. No production function that accepts caller-selectable
   ScoringInput/ScoringDispatchAdmission/PrimaryFailureEvidence can trigger
   H2-B provider contact; pure classification helpers remain (data only).
3. Made the actual `RuntimeOperations` PRIMARY execution frame the sole
   authoritative H2-B owner: the entire provider-contacting REPAIR flow is now
   a function-local closure `_h2b_repair_continuation` defined and invoked
   only inside `scoring_stage`, with no class/module attribute exposing it.
4. Added the repaired-candidate deterministic Content Quality gate to the
   REPAIR flow (accepted gate reused unchanged, no second algorithm).
5. Preserved EMPTY_CONTENT runtime reachability semantics: empty/whitespace
   repaired content fails schema/parse before the gate
   (`REPAIR_SCHEMA_OR_PARSE_INVALID`, `FAILED_FINAL`, zero Judge); the pure
   gate's `EMPTY_CONTENT` contract remains as a pure-function regression only.
6. Added `RepairTrustedScoringFinalizer` in `quality.py` (authorized option B),
   reusing a private pure finalization core extracted from the PRIMARY
   finalizer (`_build_trusted_score_result`) and the unchanged frozen sealed
   serializer from `scoring.py` (called, never modified).
7. The finalizer independently fresh-revalidates every input (object.__new__/
   object.__setattr__/model_construct bypasses re-run through strict
   validation), independently reruns the deterministic gate, replays the Judge
   raw requiring PASS, re-verifies the attestation against the current
   authority, and enforces the dual binding.
8. Successful H2-B now carries the finalizer-produced `TrustedScoreResult`
   plus exact structured UTF-8 bytes / SHA-256 / length / schema-version
   metadata.
9. Expanded `PhaseH2BValidatedRepairResult` accordingly.
10. Added adversarial RED tests for every corrected boundary.

### Changed files (all within authorized scope)

- `src/youtube_intel/scoring_admission.py` — removed
  `_consume_runtime_role_and_dispatch` and its `Callable`/`TypeVar` surface.
  Remaining state-only API: `verify_active_lease`, `admit` (still rejects
  REPAIR/REPAIR_JUDGE), `consume_repair_role`, `consume_repair_judge_role`
  (each verifies live lease, frozen role/operation literal, predecessor role,
  one-shot budget, ProviderCall conflict; accepts no callback; returns None),
  plus the shared private state mutation `_consume_runtime_role` and the
  unchanged registry/identity builders.
- `src/youtube_intel/runtime.py` — `_h2b_execute_repair` removed. The
  authoritative flow is the lexical `_h2b_repair_continuation(pfe)` closure
  inside `scoring_stage`: verify PFE against the runtime-owned trusted
  context → derive RNI/request hash/frozen prompt/payload and payload
  SHA-256/length → collision guards vs PRIMARY request hash / PRIMARY Judge
  H2 → `admission.consume_repair_role` → same-frame recompute of identity and
  payload requiring exact equality → exact REPAIR dispatch → outer seal →
  inner candidate parse/schema → TASK-016B → derive REPAIR Judge context
  (accepted gate input) → deterministic gate (reject →
  `REPAIR_DETERMINISTIC_GATE_REJECT:<reason>` terminal, zero Judge) →
  collision guard vs REPAIR Judge H2 → `admission.consume_repair_judge_role`
  → same-frame Judge identity/input revalidation → exact Judge dispatch →
  strict raw capture → pure replay requiring PASS → REPAIR-bound attestation
  → `RepairTrustedScoringFinalizer` → sealed structured evidence → untrusted
  aggregate. Known terminal failures map through the existing
  `fail_job(INVALID_RESPONSE, <message>, retry_at=None)` exactly once;
  finalizer failures map to `REPAIR_FINALIZATION_INVALID`. Classification
  helpers renamed to pure `_h2b_pfe_for_parse_failure` /
  `_h2b_pfe_for_known_failure` (build + immediately verify PFE; no admission,
  no provider contact, return data only).
- `src/youtube_intel/quality.py` — extracted the shared pure core
  `_build_trusted_score_result` (candidate/result construction + opaque
  wrapping only; no I/O/persistence/Phase G). PRIMARY
  `TrustedScoringFinalizer.finalize` retains byte-for-byte behavior via that
  core. Added `RepairFinalizationInvalid`, `RepairFinalizerOutput`, and
  `RepairTrustedScoringFinalizer` with the frozen local order: fresh schema
  revalidation → reconstruct accepted REPAIR gate input → run accepted gate
  requiring PASS → Judge binding derivation/replay requiring PASS → result
  cross-binding/provenance checks → fresh attestation verification →
  RNI/REPAIR request identity + dual-binding provenance → pure core →
  unchanged frozen sealed serializer.
- `src/youtube_intel/h2_evidence.py` — aggregate fields added:
  `repair_normalized_input_bytes`, `quality_input_hash`,
  `deterministic_gate_status`, `finalizer_trusted_result`,
  `structured_result_bytes`, `structured_result_sha256`,
  `structured_result_length`, `structured_result_schema_version`,
  `structured_result_prompt_version`. No schema/hashing change.
- Tests: rewrote the admission/executor tests in
  `test_task016c_phase_h2b_repair_seams.py` /
  `test_task016c_phase_h2b_repair_flow.py` (no test demonstrates a generic
  callback authority anymore); extended the PASS-aggregate and forgery tests;
  added `test_task016c_phase_h2b_correction_authority.py` (authority-surface
  introspection, forged-PFE-after-genuine-PRIMARY attack, state-only
  consumption semantics, concurrency winner/loser with zero contact, EMPTY/
  whitespace/tab-newline schema terminals, CONTROL_CHARACTER_INVALID and
  EXACT_REPETITION gate terminals with scripted-but-unconsumed Judge PASS,
  REPAIR_FINALIZATION_INVALID mapping, candidate-equality-vs-provenance
  distinction, structured-evidence mutation → persistence rejection) and
  `test_task016c_phase_h2b_correction_finalizer.py` (valid chain →
  TrustedScoreResult + sealed bytes/hash/length; gate replay rejects despite
  Judge PASS/attestation; low-level forged EMPTY candidate; model_construct
  bypass; PRIMARY-hash-as-REPAIR-provenance; wrong REPAIR identity; wrong RNI
  hash; mutated RNI; PRIMARY-role Judge evidence; non-PASS Judge; forged/
  mutated attestation; spoofed capabilities; substituted settings; candidate
  substitution).

### Frozen modules confirmed unchanged (zero diff)

`src/youtube_intel/scoring.py`, `src/youtube_intel/state.py`,
`src/youtube_intel/pipeline.py`, `src/youtube_intel/providers/ollama.py`,
`src/youtube_intel/domain.py`, `migrations/`, and all Phase G persistence
machinery (`TrustedPersistenceEntry`, `persist_success()`, PREWRITE,
filesystem protocol, SQLite registration, Artifact namespace/idempotency).
The sealed serializer was called, never modified.

### Stop-boundary confirmation

actual admitted REPAIR: YES; deterministic gate: YES; admitted REPAIR Judge:
YES; Quality PASS attestation: YES; RepairTrustedScoringFinalizer: YES;
TrustedScoreResult: YES; sealed structured bytes/hash/length: YES;
PhaseH2BValidatedRepairResult: YES; PhaseHTrustedRepairSuccess: NO; H2-C: NO;
repair persistence: NO; Phase G changes: NO. Direct persistence of a valid
corrected aggregate still rejects with zero side effects.

### Evidence (gate results)

- Focused H2-B suites (flow + seams + both correction files): 99 passed.
- Full `uv run --offline pytest tests/unit tests/integration`: 1626 passed,
  1 pre-existing Pydantic serializer warning.
- `uv run --offline pytest tests/e2e`: 9 passed.
- `uv run --offline mypy src`: Success, no issues in 31 source files.
- `uv run --offline ruff check .`: All checks passed.
- `git diff --check`: clean. `bash scripts/security_scan.sh`: status=clean
  (pre-existing high-entropy/wheel-license WARNs unchanged).
- Manual security searches over `src/`/`migrations/`:
  `_consume_runtime_role_and_dispatch`, `consume_role_and_dispatch`,
  `admit_and_dispatch`, `consume_repair_dispatch`, `dispatch_after_admission`,
  `_h2b_execute_repair`, `h2c_finalize`, `persist_repair`,
  `mint_repair_success`, `verify_h2b_result`, repair receipt/token/registry —
  none found. `PhaseHTrustedRepairSuccess` appears only in a comment stating
  it is not minted. `_h2b_repair_continuation` is the lexical closure (not a
  durable continuation/receipt/capability).

### Remaining concerns

- The REPAIR flow still stashes the untrusted aggregate on the runtime
  (`_last_h2b_validated_repair_result`) and finalizes the job through the
  generic non-SUCCEEDED path; without separately authorized H2-C a successful
  repair cannot persist. This is the frozen H2-B end state.
- No other open items; all correction objectives were implemented and tested.

## Phase H2-B — Runtime REPAIR execution (implementation)

### Metadata and scope

- Task: `TASK-016C Phase H2-B` implementation only (runtime REPAIR control
  flow; H2-C NOT implemented, NOT authorized).
- Base HEAD: `4f8bb56` (H2-B authorization closure); implementation commit:
  `c8a6e04`.
- Authorization document: `docs/TASK-016C-PHASE-H2B-AUTHORIZATION.md`.
- Status: `READY FOR H2-B IMPLEMENTATION INDEPENDENT REVIEW`.

### What was implemented

Actual runtime REPAIR execution for one actually received eligible PRIMARY
failure, stopping at the untrusted `PhaseH2BValidatedRepairResult` evidence
aggregate. REPAIR persistence, `PhaseHTrustedRepairSuccess`, and H2-C remain
unimplemented.

Changed production files (all within the authorized scope):

- `src/youtube_intel/runtime.py` — private H2-B branch inside the scoring
  stage's actual PRIMARY execution:
  - `scoring_stage` observes an eligible PRIMARY failure (post-capture parse
    failure via the sealed provider capture; language/gate/judge failures via
    deterministic replay of the frozen checks) and enters the REPAIR branch;
    ineligible failures re-raise the original error unchanged.
  - `_h2b_execute_repair(...)` derives RNI + exact `local-scoring-repair-v1`
    request hash from `build_repair_normalized_input` /
    `build_repair_request_hash`, assembles the frozen `TASK016C_REPAIR_PROMPT_V2`
    prompt and the exact frozen Ollama payload, computes payload SHA-256/length,
    and atomically admits+dispatches REPAIR; then seals the authoritative
    REPAIR outer raw (`seal_primary_raw_capture`), parses the repaired
    candidate through the shared parser, runs the TASK-016B validator, derives
    the REPAIR Judge context via `derive_repair_judge_trusted_context`, and
    atomically admits+dispatches REPAIR_JUDGE; pure-replays the exact Judge raw
    requiring PASS before constructing the aggregate.
  - Known terminal failures (`REPAIR_SCHEMA_OR_PARSE_INVALID`,
    `REPAIR_LANGUAGE_INVALID`, `REPAIR_JUDGE_REJECT`,
    `REPAIR_JUDGE_UNCERTAIN`) use `fail_job(..., ErrorCode.INVALID_RESPONSE,
    retry_at=None)` exactly once, confirm `FAILED_FINAL`, and return
    `StageDisposition.TERMINAL` (TERMINAL_ALREADY_HANDLED).
  - All post-contact ambiguity raises `UnknownProviderState` (existing H1
    route); pre-contact denials stay `ScoringDispatchDenied`.
  - H2-B PASS stashes the aggregate on the runtime
    (`_last_h2b_validated_repair_result`); no persistence occurs and the job
    is finalized by the existing generic non-SUCCEEDED path.
- `src/youtube_intel/pipeline.py` — narrow `_execute()` branch: when the
  disposition is `StageDisposition.TERMINAL`, read the job back via
  `get_job()`; only a durably `FAILED_FINAL` job suppresses the duplicate
  generic `_fail()`; any other state preserves the existing generic failure
  behavior (fake-TERMINAL defense). No other behavior changed.
- `src/youtube_intel/providers/ollama.py`:
  - frozen `render_task016c_repair_prompt_v2(...)` (exact block order/text,
    literal `null` fallbacks, `score-result-v2` schema block via H2 JCS) and
    `build_task016c_repair_generate_body(...)` (exactly `model`, `prompt`,
    `stream=false`, `format`, `think=false`, `options.temperature`,
    `options.num_predict`; compact `ensure_ascii=False` serialization).
  - `OllamaScoringProvider.dispatch_exact_repair_generate(...)`: local payload
    hash/length equality re-check before any transport, `/api/tags` model
    preflight first, then POST of the exact derived body; returns the exact
    outer response body bytes uninterpreted.
  - `OllamaScoringProvider.primary_attempt(...)` now seals the exact
    `/api/generate` body as a `PrimaryRawCapture` before the inner parse and
    exposes it once via `consume_primary_parse_failure_capture()` for the
    runtime's eligibility classification; success behavior unchanged
    (ambiguous outer bodies never promote).
  - `_request_json` factored into behavior-identical `_request_raw_body`
    (bounded transport/read mechanics) + JSON interpretation.
  - `OllamaQualityJudgeProvider.judge_exact_model_content(...)`: strict H2-B
    REPAIR Judge seam — locally-proven rejections (invalid inputs, binding/
    loopback/identity mismatches, including J1/J2 and PRIMARY-Judge identity
    substitution) deny before contact; `/api/tags` then `/api/generate`
    transport ambiguities propagate (runtime maps to UNKNOWN), never
    collapsing into semantic UNCERTAIN.
  - legacy `judge()` preserves the exact extracted model content once
    (`consume_extracted_judge_model_content()`) so PRIMARY Judge raw can back
    eligible JUDGE_REJECT/JUDGE_UNCERTAIN PFE; legacy behavior otherwise
    unchanged.
- `src/youtube_intel/scoring_admission.py` — the single authorized minimal
  change: private `ScoringDispatchAdmission._consume_runtime_role_and_dispatch(
  identity, dispatch, *, now)`. REPAIR/REPAIR_JUDGE only; frozen operation
  literals enforced; live lease proof; shared execution-state lock; one-shot
  role budget with predecessor requirement (REPAIR requires consumed PRIMARY;
  REPAIR_JUDGE requires consumed REPAIR); ProviderCall-existence check for the
  exact derived request hash; then immediate dispatch of the caller closure.
  No identity persistence, token, receipt, continuation, registry, or public
  REPAIR admission. Public `admit()` is unchanged and still rejects REPAIR/
  REPAIR_JUDGE.
- `src/youtube_intel/h2_evidence.py` — pure additions only:
  `derive_repair_judge_trusted_context(...)` (REPAIR analog of the PRIMARY
  derivation; Judge input/operation `scoring_request_hash` is exactly the
  role-distinct REPAIR request hash per the frozen RepairQualityEvidence
  binding; no caller JudgeTrustedContext accepted) and the frozen dataclass
  `PhaseH2BValidatedRepairResult` (evidence-only aggregate).

Frozen modules confirmed unchanged (zero diff): `scoring.py`, `state.py`,
`quality.py`, `domain.py`, migrations, Phase G persistence machinery
(`TrustedPersistenceEntry`, `persist_success()`, PREWRITE, filesystem
persistence, SQLite registration, Artifact namespace/idempotency).

### Runtime H2-B entry seam and eligibility

Entry exists only inside the actual PRIMARY execution branch of
`scoring_stage` after the runtime's own admitted PRIMARY attempt. Closed
eligible classes: `SCHEMA_OR_PARSE_INVALID` (post-capture parser codes only,
via `H2_ELIGIBLE_PARSER_CODES`), `LANGUAGE_INVALID` (validator result exactly
INVALID), `JUDGE_REJECT`, `JUDGE_UNCERTAIN` (requires trustworthy PRIMARY
Judge raw from the actual dispatch). Not eligible: UNKNOWN_PROVIDER_STATE,
deterministic-gate rejections, pre-capture/protocol failures, timeouts,
authority/config mismatches. PFE is re-verified against the runtime-derived
`PrimaryTrustedContext` + validated settings before any REPAIR identity is
derived. There is no public `repair(...)`/`run_repair(...)`/`dispatch_repair(
...)` API; the private methods take only runtime-owned execution state.

### Admission-to-dispatch atomicity and identity binding

REPAIR and REPAIR_JUDGE each derive their complete immutable identity and
payload locally, construct the provider (proven-local constructors) and then
invoke the private atomic composition: consume role under the shared lock and
immediately run the closure built over the same function-local values. There
is no token/receipt/continuation and no caller return between consume and
dispatch, so admit-A/dispatch-B is structurally impossible. Defense in depth:
the REPAIR provider seam re-verifies payload SHA-256/length immediately before
transport; the strict Judge seam re-derives H1/H2 from fresh-revalidated
operation input and requires the expected identity. `/api/tags` is treated as
external contact: admission always precedes it (denied -> zero `/api/tags`,
zero `/api/generate`).

### Outcome classification

- REPAIR `/api/tags` or `/api/generate` timeout/reset/interruption, malformed/
  duplicate-key/non-object outer body, missing/non-string `response` ->
  `UNKNOWN_PROVIDER_STATE` via the existing H1 `finalize_unknown_provider_state`
  route; no retry, no second REPAIR.
- Inner repaired-candidate parse/schema failure -> known terminal
  `REPAIR_SCHEMA_OR_PARSE_INVALID`; language INVALID/UNCERTAIN ->
  `REPAIR_LANGUAGE_INVALID` (no Judge in both cases).
- REPAIR Judge: transport/protocol ambiguity -> UNKNOWN (never UNCERTAIN);
  semantic REJECT -> `REPAIR_JUDGE_REJECT`; semantic UNCERTAIN ->
  `REPAIR_JUDGE_UNCERTAIN`; PASS -> aggregate.
- Known terminals: `fail_job(INVALID_RESPONSE, <exact message>, retry_at=None)`
  exactly once -> `FAILED_FINAL`; pipeline TERMINAL read-back suppresses the
  duplicate generic `_fail()`; one job attempt row; crash-after-finalize stays
  terminal on restart (disposition is process-local).

### Aggregate and persistence rejection

`PhaseH2BValidatedRepairResult` is an untrusted in-memory evidence aggregate:
PRIMARY provenance/PFE/failure class; exact RNI + JCS hash + REPAIR request
hash; exact outbound prompt/payload bytes + SHA-256/length; authoritative
REPAIR outer raw + hash/length + extracted model content; repaired candidate +
hash; TASK-016B language evidence; REPAIR Judge operation input, role REPAIR,
H1/H2, `JudgeEvidence`, exact Judge raw + hash/length, PASS result; PASS
attestation; model/digest/prompt/schema/policy/settings provenance. It is NOT
a persistence authority: `TrustedPersistenceEntry.persist_success(...)`
rejects it (exact-type Phase G ingress), including `object.__new__` forged,
`object.__setattr__` mutated, `copy`/`deepcopy`, and pickle-round-tripped
variants. No `persist_repair`, no REPAIR ProviderCall/Artifact/SQLite writes,
no H2-C ingress API (`h2c_finalize`/`finalize_repair`/`mint_repair_success`/
`persist_validated_repair`/`verify_h2b_result` all absent).

### Contractual observation (flagged for reviewer/orchestrator)

Authorization §9 lists a "finalizer-produced `TrustedScoreResult`, its sealed
structured bytes/hash/length" among the aggregate's minimum contents. H2-B
does NOT carry a `TrustedScoreResult`: the existing `TrustedScoringFinalizer`
is frozen to the PRIMARY scoring-request binding (its cross-bindings require
`scoring_request_hash == PRIMARY identity`), while the frozen REPAIR quality
binding requires the role-distinct REPAIR request hash; minting one for REPAIR
within H2-B would require modifying `quality.py` (outside the authorized H2-B
file scope) or inventing minting authority. The aggregate instead carries the
complete finalizer-input evidence set (repaired candidate, original
ScoringInput, REPAIR quality input/result/operation, PASS attestation,
settings provenance), and H2-C's own mandatory replay obligation (step 12:
"rederive the finalizer-produced TrustedScoreResult ... from the trusted
candidate/context") establishes that value independently. Flagging for the
orchestrator: if carrying the finalizer result inside the H2-B aggregate is
required, that needs a scope/authorization amendment (finalizer support for
the REPAIR binding).

Second observation: the parent H2 authorization §4 mentions the deterministic
quality gate before the REPAIR Judge; the H2-B authorization's frozen flow and
closed error map (the normative H2-B execution contract) contain no gate step
and no gate-rejection outcome, and the H2-C replay checklist (21 steps)
likewise omits it. The implementation follows the H2-B normative flow; the
gate remains enforced for PRIMARY.

### Tests and checks

New RED-first suites (all failing before implementation):

- `tests/unit/test_task016c_phase_h2b_repair_seams.py` (27 tests): frozen
  prompt/payload contract; exact-body dispatch with hash/length equality;
  tags-before-generate ordering; PRIMARY parse-failure capture; strict Judge
  seam UNKNOWN-vs-UNCERTAIN split; identity substitution denials; private
  atomic admission composition (role/lease/predecessor/duplicate/provider-call
  guards); REPAIR Judge trusted-context derivation.
- `tests/unit/test_task016c_phase_h2b_repair_flow.py` (33 tests): production
  runtime + SQLite + real Ollama adapters with scripted transport — entry
  authority (forged PFE, UNKNOWN relabel, no-PRIMARY denial, lease denial),
  PASS aggregate flow (exact payload send-equality, zero persistence),
  transport UNKNOWN outcomes (tags/generate timeouts, malformed/duplicate-key
  outer), known terminal flows (schema/language/judge REJECT/UNCERTAIN) with
  fail_job-once and no Judge contact, PRIMARY language/judge-failure repair
  paths, pipeline TERMINAL read-back + fake-TERMINAL defense + unrelated
  failure regression + crash-after-finalize, Phase G direct persistence
  rejection including low-level forgery, concurrency, duplicates, and
  no-recursive-repair after every failure kind.

| Command | Result |
| --- | --- |
| `uv run --offline pytest tests/unit/test_task016c_phase_h2b_repair_seams.py tests/unit/test_task016c_phase_h2b_repair_flow.py` | 60 passed |
| `uv run --offline pytest tests/unit tests/integration` | 1587 passed |
| `uv run --offline pytest tests/e2e` | 9 passed |
| `uv run --offline mypy src` | clean (31 files) |
| `uv run --offline ruff check .` | clean |
| `git diff --check` | clean |
| `bash scripts/security_scan.sh` | status=clean |
| H2-A focused suites | passed |
| H1 admission suite | passed |
| Phase G / Phase F / finalizer / quality suites | passed |
| Ollama provider / pipeline / runtime composition integration | passed |

Security searches (all zero in `src/`): `PhaseHTrustedRepairSuccess`,
`persist_repair`, `h2c_finalize`/`finalize_repair`/`mint_repair_success`/
`persist_validated_repair`/`verify_h2b_result`, repair receipt/token/
continuation/registry, new migrations, new artifact kinds, new SQLite writers.

## Phase H2-A Correction Round 3 — derive H2 trust from runtime inputs

### Metadata and scope

- Task: `TASK-016C Phase H2-A Correction Round 3` only (runtime-owned trust
  composition; do NOT start H2-B).
- Reviewed HEAD: `4934c7a`; previous correction commit: `43ad2dc`.
- Correction commit: `c58396b` — `fix(task016c): derive H2 trust from runtime
  inputs`.
- Status: `READY FOR H2-A CORRECTION ROUND 3 INDEPENDENT REVIEW`.

Findings addressed: P1-1 (a caller-supplied `JudgeTrustedContext` could act as
authority), P1-2 (a directly constructed `RepairTrustedConfig` could establish RNI
trust), P1-3 (Judge-based PFE could not enter the trusted RNI builder without an
invented Judge-context binding).

### Corrected trust model

The foundation now uses: ALREADY TRUSTED RUNTIME INPUTS -> RUNTIME-OWNED
DETERMINISTIC COMPOSITION -> EXPECTED DATA -> EVIDENCE REPLAY. No authoritative
verifier/builder establishes trust merely because a caller supplied a
`JudgeTrustedContext` or `RepairTrustedConfig` instance. All changes are in
`src/youtube_intel/h2_evidence.py`.

- **P1-1 — independent trusted Judge context:** added
  `derive_primary_judge_trusted_context(*, primary_trusted_context,
  trusted_candidate, validated_settings) -> (JudgeTrustedContext, judge_input)`.
  It derives the judge input, candidate/scoring-request/quality-input hashes,
  provider/model/digest (from the validated `LocalScoringSettings`, checked
  against the trusted PRIMARY context), frozen policy/prompt/schema/operation
  literals, and expected H1/H2 — with no caller override for any expected value.
  `verify_primary_failure_evidence(evidence, trusted_context, validated_settings)`
  now derives the expected Judge context internally for JUDGE_REJECT/
  JUDGE_UNCERTAIN and no longer accepts a caller-supplied `JudgeTrustedContext`.
- **P1-2 — RepairTrustedConfig not a security root:**
  `build_repair_normalized_input(*, job_id, primary_trusted_context,
  failure_evidence, validated_settings)` derives the `RepairTrustedConfig`
  internally via `build_repair_trusted_config(validated_settings)`; it exposes no
  REPAIR config parameter, so an attacker-constructed `RepairTrustedConfig`
  cannot be supplied or influence the trusted RNI.
- **P1-3 — Judge-based PFE enters the RNI builder:** the trusted RNI builder
  handles all four eligible classes (SCHEMA_OR_PARSE_INVALID, LANGUAGE_INVALID,
  JUDGE_REJECT, JUDGE_UNCERTAIN) using the frozen contracts; for Judge-based
  failures it re-verifies the PFE, re-derives the trusted PRIMARY candidate, and
  derives the expected PRIMARY Judge context internally. H2-B need not invent a
  caller-selected Judge context.
- `verify_judge_evidence_replay` and `build_judge_trusted_context` are documented
  as low-level data-level primitives, not security ingresses; the authoritative
  PFE/RNI composition derives its expected data internally.

### Behavioral proof (PART 26)

All three reviewer attacks reject through real production composition/verifier
paths, in `tests/unit/test_task016c_phase_h2a_correction_r3.py` (and one in
correction_r2):

1. PRIMARY A + attacker model/digest Judge B + attacker self-consistent Judge
   context B -> authoritative PFE verification REJECTS
   (`test_pfe_rejects_self_consistent_judge_b_for_primary_a`); the verifier
   accepts no `judge_trusted_context` parameter
   (`test_attacker_judge_trusted_context_cannot_be_injected`,
   `test_pfe_authoritative_verifier_has_no_judge_context_parameter`).
2. Valid PFE/context A + directly constructed RepairTrustedConfig B -> trusted
   RNI composition MUST NOT emit B configuration
   (`test_rni_builder_rejects_direct_repair_trusted_config_argument`,
   `test_attacker_repair_trusted_config_cannot_influence_trusted_rni`,
   `test_trusted_rni_always_reflects_validated_settings`).
3. Valid JUDGE_REJECT / JUDGE_UNCERTAIN PFE -> trusted RNI composition succeeds
   using the internally derived expected Judge context, without the caller
   supplying a JudgeTrustedContext (`test_judge_reject_pfe_enters_trusted_rni_builder`,
   `test_judge_uncertain_pfe_enters_trusted_rni_builder`).

For attacks 1 and 2: no provider calls, no Judge calls, no filesystem/Artifact/
SQLite writes, and no success transition (pure pre-plan rejection).

### Tests and checks

| Command | Result |
|---|---|
| H2-A focused suites (jcs, raw_capture, judge_replay, evidence, correction_r1/r2/r3) | PASS (`244 passed`) |
| `test_task016c_phase_h1_admission.py` | PASS |
| `test_task016c_phase_g.py` | PASS |
| Ollama provider + Judge contract + runtime composition + TASK-016B language | PASS |
| Full unit + integration offline | PASS (`1527 passed`) |
| E2E offline | PASS (`9 passed`) |
| `uv run --offline mypy src` | PASS (`31 source files`) |
| `uv run --offline ruff check .` | PASS |
| `git diff --check` | PASS |
| `bash scripts/security_scan.sh` | `status=clean` (warnings pre-existing) |

### Boundary confirmation

- Production change is limited to `src/youtube_intel/h2_evidence.py`;
  `scoring.py`, `state.py`, `runtime.py`, `scoring_admission.py`, `domain.py`,
  `quality.py`, `migrations/`, `providers/ollama.py`, and `h2_jcs.py` have zero
  diff.
- REPAIR dispatch remains disabled: no `PhaseHTrustedRepairSuccess`,
  `persist_repair()`, REPAIR/REPAIR_JUDGE dispatch, repair persistence branch,
  public repair API, or repair token/receipt/registry/continuation.
- No hidden registry/sentinel/nonce/token/closure/global-state trust mechanism;
  trust is derived from existing validated runtime inputs at the authoritative
  composition boundary.

Status: `READY FOR H2-A CORRECTION ROUND 3 INDEPENDENT REVIEW`.

---

## Phase H2-A Correction Round 2 — seal H2 judge and repair config bindings

### Metadata and scope

- Task: `TASK-016C Phase H2-A Correction Round 2` only (fix independent-review
  findings; do NOT start H2-B).
- Reviewed HEAD: `0c9abc9`; previous correction commit: `f36f12e`.
- Correction commit: `43ad2dc` — `fix(task016c): seal H2 judge and repair config
  bindings`.
- Status: `READY FOR H2-A CORRECTION ROUND 2 INDEPENDENT REVIEW`.

Findings addressed: P1-1 (Judge replay lacked an independent trusted expected
Judge context; a self-consistent Judge for candidate/request B could be embedded
in a PFE whose PRIMARY raw/candidate/request are A), P1-2 (trusted RNI builder
still accepted authoritative REPAIR configuration from the caller), P1-3
(low-level frozen-field mutation bypass via `object.__setattr__`/`model_construct`).

### How each finding is corrected (all in `src/youtube_intel/h2_evidence.py`)

- **P1-1 — independent trusted Judge context:** added `JudgeTrustedContext`
  (data-only, immutable expected provenance, built via
  `build_judge_trusted_context` from trusted runtime inputs, never from a
  `JudgeEvidence` object). `verify_judge_evidence_replay(evidence,
  judge_trusted_context)` compares every metadata field, the operation literal,
  the role, the exact operation input, H1/H2, and the judge-input
  candidate/request/hash bindings against the trusted context; `evidence.
  operation_input` and `evidence.judge_input` can no longer authenticate each
  other. `verify_primary_failure_evidence` for JUDGE_REJECT/JUDGE_UNCERTAIN now
  requires a trusted Judge context whose candidate hash equals the trusted
  PRIMARY candidate (parsed from the trusted raw) and whose scoring-request hash
  equals the trusted PRIMARY scoring request, enforcing complete
  raw→candidate→request→Judge continuity.
- **P1-2 — trusted REPAIR config:** added `RepairTrustedConfig` (immutable
  expected configuration DATA derived from validated `LocalScoringSettings` via
  `build_repair_trusted_config`). The trusted RNI builder now derives every
  authoritative REPAIR field (provider/model/digest/prompt/schema/temperature/
  output/description limits/operation) from it; the builder exposes no
  model/temperature/limit overrides, so attacker-selected REPAIR configuration is
  impossible through the trusted path.
- **P1-3 — fresh exact-model revalidation:** added `_fresh_revalidate_exact`
  (model_dump → strict `model_validate`). `verify_primary_failure_evidence` and
  `verify_judge_evidence_replay` freshly revalidate the evidence object at the
  boundary, defeating `object.__setattr__`/`model_construct`/copy/pickle mutation
  of frozen fields (e.g. `primary_raw_capture_kind`, `raw_capture_kind`) and
  nested `operation_input`/`judge_input` mutations. Invalid typed values are
  rejected by revalidation; valid-but-wrong values are rejected by the
  trusted-context comparison.
- Both trusted contexts are plain data only — no token, authority, receipt,
  admission, sentinel, registry, continuation, or persistence capability; they
  grant no dispatch and no persistence.

### Behavioral proof (PART 25)

All three reviewer acceptance paths reproduce and reject through real production
verifier/builder boundaries, in `tests/unit/test_task016c_phase_h2a_correction_r2.py`:

1. PFE A + self-consistent Judge B → REJECT
   (`test_pfe_a_with_self_consistent_judge_b_rejected`,
   `test_cross_object_judge_substitution_rejected`).
2. Valid trusted PFE/context + attacker REPAIR config → trusted RNI builder
   refuses overrides (`test_rni_builder_refuses_caller_repair_config_overrides`
   across model/model_digest/temperature/max_output_tokens/max_description_chars/
   provider/prompt_version/schema_version).
3. `object.__setattr__`: PFE `primary_raw_capture_kind` and Judge
   `raw_capture_kind` set to `ATTACKER_KIND` → both production verifiers REJECT
   (`test_pfe_raw_capture_kind_mutation_rejected`,
   `test_judge_raw_capture_kind_mutation_rejected`, plus nested mutation and
   copy/deepcopy/pickle variants).

These are pure pre-plan rejection tests: no provider calls, no Judge calls, no
filesystem/Artifact/SQLite writes, and no success transition.

### Tests and checks

| Command | Result |
|---|---|
| H2-A focused suites (jcs, raw_capture, judge_replay, evidence, correction_r1, correction_r2) | PASS (`232 passed`) |
| `test_task016c_phase_h1_admission.py` | PASS |
| `test_task016c_phase_g.py` / `test_task016c_phase_f.py` | PASS |
| Ollama provider + Judge contract + runtime composition + TASK-016B language | PASS |
| Full unit + integration offline | PASS (`1515 passed`) |
| E2E offline | PASS (`9 passed`) |
| `uv run --offline mypy src` | PASS (`31 source files`) |
| `uv run --offline ruff check .` | PASS |
| `git diff --check` | PASS |
| `bash scripts/security_scan.sh` | `status=clean` (warnings pre-existing) |

### Boundary confirmation

- Production change is limited to `src/youtube_intel/h2_evidence.py`; the
  protected modules (`scoring.py`, `state.py`, `runtime.py`,
  `scoring_admission.py`, `domain.py`, `quality.py`, `migrations/`) and
  `providers/ollama.py` have zero diff. The approved `h2_jcs.py` is unchanged.
- REPAIR dispatch remains disabled: no `PhaseHTrustedRepairSuccess`,
  `persist_repair()`, repair token/registry/receipt/admission, or alternate
  persistence ingress; `h2_evidence.py` performs no I/O.
- StrictInt, duplicate-key rejection, and PFE raw hash/length replay behaviors
  are preserved (their tests still pass).

Status: `READY FOR H2-A CORRECTION ROUND 2 INDEPENDENT REVIEW`.

---

## Phase H2-A Correction Round 1 — bind H2 evidence to trusted provenance

### Metadata and scope

- Task: `TASK-016C Phase H2-A Correction Round 1` only (fix independent-review
  findings; do NOT start H2-B).
- Reviewed HEAD: `c391d36`; H2-A implementation commit: `9de5e69`.
- Correction commit: `f36f12e` — `fix(task016c): bind H2 evidence to trusted
  provenance`.
- Status: `READY FOR H2-A CORRECTION ROUND 1 INDEPENDENT REVIEW`.

Findings addressed: P1-1 (protocol-invalid PRIMARY evidence treated as
SCHEMA_OR_PARSE_INVALID), P1-2 (JudgeEvidence metadata not bound to
operation_input), P1-3 (PrimaryFailureEvidence provenance not bound to a trusted
context), P2-4 (coercive integer typing), P2-5 (last-key-wins outer JSON capture).

### How each finding is corrected

- **P1-1 / P2-5 (protocol-invalid + duplicate-key raw):** the PRIMARY capture gate
  `seal_primary_raw_capture` now parses the outer body with the existing strict
  decoder `jcs_loads_strict`, rejecting duplicate object keys (and non-finite
  constants). SCHEMA_OR_PARSE_INVALID eligibility requires both a post-capture
  parser code (new `H2_ELIGIBLE_PARSER_CODES`) and a capturable raw body. Raw such
  as `{bad`, `{"response":7}`, `[1]`, or `{"response":7,"response":"second"}`
  never promotes and cannot back eligible evidence; it stays on
  UNKNOWN_PROVIDER_STATE semantics.
- **P1-3 (trusted PRIMARY context):** `verify_primary_failure_evidence` now
  requires an immutable `PrimaryTrustedContext` (`build_primary_trusted_context`)
  and independently compares/rederives every PRIMARY provenance binding (attempt
  identity, request/normalized-input hash, provider/model/digest, prompt/schema,
  output language, temperature, output/description limits, scoring input, and
  `primary_scoring_input_sha256`) against it. Self-consistent but forged evidence
  no longer verifies.
- **primary_scoring_input_sha256 rederivation:** computed with the frozen PRIMARY
  identity serializer (`canonical_primary_scoring_input_hash` via
  `_canonical_json_bytes`), never H2 JCS.
- **P1-2 (Judge metadata binding):** `verify_judge_evidence_replay` binds
  provider/model/digest/policy/prompt/operation-schema and the operation literal
  to `operation_input`, and ties `candidate_hash`/`scoring_request_hash` between
  the operation input and the judge input. Detached or forged metadata, or a
  PRIMARY/REPAIR role mismatch against the operation input, is rejected.
- **P2-4 (strict integers):** exact integer fields (`max_output_tokens`,
  `max_description_chars`, `primary_max_output_tokens`,
  `primary_max_description_chars`, `primary_raw_utf8_length`, `raw_utf8_length`)
  use `StrictInt`, rejecting `true`/`false`/`1.0`/`0.0`/`"1"` in sealed JSON.
- **RNI trusted derivation:** `build_repair_normalized_input` is a trusted
  builder that verifies the PFE against the trusted context and derives the
  authoritative PRIMARY bindings from trusted/verified inputs, so a forged PFE
  cannot seed a trustworthy RNI. A low-level typed constructor remains for
  parsing/tests and is clearly distinct from the trusted builder.

### Candidate/request/input cross-binding (PART 12)

Judge evidence is tied to the exact candidate/scoring operation it claims to
judge: candidate-hash substitution, scoring-request-hash substitution, and
PRIMARY-Judge-evidence-on-REPAIR-operation (and converse) all reject via
`verify_judge_evidence_replay`.

### Behavioral proof (PART 20)

All 15 original reviewer attacks now reject through real production paths, covered
by `tests/unit/test_task016c_phase_h2a_correction_r1.py` (60 tests):
protocol-invalid `{bad` / `{"response":7}` / `[1]`; outer duplicate
`{"response":7,"response":"second"}`; forged Judge provider/model/digest/policy/
prompt/schema; forged PRIMARY request hash / scoring-input hash / provider/model/
config; boolean and `1.0` in exact integer fields. Because H2-A has no
persistence/dispatch path, these are pure rejection tests with zero provider/Judge
calls, zero filesystem/Artifact/SQLite writes, and no success transition.

### Tests and checks

| Command | Result |
|---|---|
| H2-A focused suites (jcs, raw_capture, judge_replay, evidence, correction_r1) | PASS (`202 passed`) |
| `test_task016c_phase_h1_admission.py` | PASS |
| `test_task016c_phase_g.py` / `test_task016c_phase_f.py` | PASS |
| Ollama provider + Judge contract + runtime composition + TASK-016B language | PASS |
| Full unit + integration offline | PASS (`1485 passed`) |
| E2E offline | PASS (`9 passed`) |
| `uv run --offline mypy src` | PASS (`31 source files`) |
| `uv run --offline ruff check .` | PASS |
| `git diff --check` | PASS |
| `bash scripts/security_scan.sh` | `status=clean` (warnings pre-existing) |

### Boundary confirmation

- REPAIR dispatch remains disabled: no `PhaseHTrustedRepairSuccess`,
  `persist_repair()`, repair token/registry/receipt/admission, or alternate
  persistence ingress exists; H1 public REPAIR paths remain fail-closed; no
  provider/Judge dispatch was added (`h2_evidence.py` / `h2_jcs.py` perform no
  I/O).
- Phase G production files unchanged: `scoring.py`, `state.py`, `runtime.py`,
  `scoring_admission.py`, `domain.py`, `quality.py`, and `migrations/` have zero
  diff. The approved `h2_jcs.py` is unchanged.
- `src/youtube_intel/providers/ollama.py` change is limited to the PRIMARY
  outer-protocol capture rejecting duplicate keys (+ the strict-decoder import).

Status: `READY FOR H2-A CORRECTION ROUND 1 INDEPENDENT REVIEW`.

---

## Phase H2-A — Evidence Foundations implementation

### Metadata and scope

- Task: `TASK-016C Phase H2-A Evidence Foundations` only.
- Frozen authorization baseline: `611d899` (in ancestry; branch clean at start).
- Authorization contract: `docs/TASK-016C-PHASE-H2-AUTHORIZATION.md`.
- Implementer: 千问办公 (implementation-only executor).
- Worktree/branch: `task-016c-content-quality-layer` /
  `workbuddy/task-016c-content-quality-layer`.
- Implementation commit: `9de5e69` — `feat(task016c): add H2 evidence foundations`.
- Status: `READY FOR H2-A INDEPENDENT REVIEW`.

Delivered exactly the 8 H2-A foundations; full H2 / H2-B not started:

- `src/youtube_intel/h2_jcs.py` — dependency-free RFC 8785 / JCS serializer:
  exact ECMAScript `NumberToString` number formatting (normative vectors as exact
  UTF-8 bytes), UTF-16 code-unit key ordering, RFC 8785 string escaping, strict
  UTF-8 output, duplicate-key/non-finite/non-canonical rejection, and canonical
  SHA-256 primitives. Isolated from the frozen `_canonical_json` serializers.
- `src/youtube_intel/h2_evidence.py` — typed `task016c-*` evidence schemas
  (`RepairNormalizedInput`, `PrimaryFailureEvidence`, `CandidateEvidence`,
  `ParserFailureEvidence`, `LanguageValidationEvidence`, `JudgeEvidence`,
  `NotApplicableEvidence`), the closed failure-class combination matrix, the
  canonical `typed -> JCS -> SHA-256` and `sealed -> parse -> validate ->
  reserialize -> byte-equality -> hash` primitives, and parser/language/judge
  replay foundations. Evidence objects are data only, never authority.
- `src/youtube_intel/providers/ollama.py` — private PRIMARY/Judge received-raw
  seals (`seal_primary_raw_capture`, `seal_judge_raw_capture`) applying the frozen
  strict-UTF-8 and 1,000,000-byte / 20,000-byte bounds; the closed parser
  diagnostic mapper `diagnose_scoring_parse_failure` mirroring the exact
  `parse_scoring_candidate` fail-closed order; and a factored pure Judge
  raw-to-result verifier `verify_judge_model_content` shared by the live adapter
  and H2 replay (behavior-preserving delegation).

### What was explicitly NOT done

- No REPAIR provider dispatch, REPAIR_JUDGE dispatch, public REPAIR admission,
  `persist_repair()`, repair repository API, repair token/registry/receipt/
  continuation/factory, or caller-supplied repair authority.
- No alternate persistence writer, SQLite transaction, Artifact namespace,
  database/schema migration, or broad provider refactor.
- No change to the Phase G filesystem persistence protocol or SQLite registration
  semantics, and no change to PRIMARY normalized-input/request hashes, Judge
  H1/H2, or the Phase G PRIMARY ProviderCall identity.
- `PhaseHTrustedRepairSuccess` was NOT defined; no active REPAIR persistence path
  exists. REPAIR remains fail-closed and unreachable.

### Verification evidence

| Command | Result |
|---|---|
| `uv run --offline pytest` (4 H2-A focused files) | PASS (`142 passed`) |
| `uv run --offline pytest tests/unit tests/integration` | PASS (`1425 passed`) |
| `uv run --offline pytest tests/e2e` | PASS (`9 passed`) |
| Phase G (`test_task016c_phase_g.py`) | PASS |
| H1 admission (`test_task016c_phase_h1_admission.py`) | PASS |
| TASK-016B language (`test_scoring_language.py`) | PASS |
| Judge contract + Ollama provider + runtime | PASS |
| `uv run --offline mypy src` | PASS (`31 source files`) |
| `uv run --offline ruff check .` | PASS |
| `git diff --check` | PASS |
| `bash scripts/security_scan.sh` | `status=clean` (warnings are pre-existing test constants) |

Normative JCS number vectors all assert exact UTF-8 byte equality; `NaN`/`+Inf`/
`-Inf` reject; `-0.0` serializes as `0`. Existing-identity non-regression tests
prove PRIMARY normalized-input/request hashes and Judge H1/H2 still use the frozen
serializer and differ from H2 JCS where the number domain distinguishes them.

### Diff review and boundary

- Modified: `src/youtube_intel/providers/ollama.py` (+325 / -53). The deletions are
  only the Judge parse/build method bodies relocated to module-level functions so
  the live path and replay share one deterministic implementation; live behavior is
  preserved (judge contract suite green). `parse_scoring_candidate` and the PRIMARY
  scoring path are byte-for-byte unchanged.
- Added: `src/youtube_intel/h2_jcs.py`, `src/youtube_intel/h2_evidence.py`, and four
  H2-A test files. No generated files or formatting noise.
- Frozen modules `scoring.py`, `quality.py`, `state.py`, `domain.py`, `runtime.py`,
  `scoring_admission.py`, and `migrations/` have zero diff.
- No dependency, lockfile, schema/migration, secret, real Vault, cloud, or
  launchd change.

### Remaining risk

- `verify_language_evidence_replay` retains a defense-in-depth
  `validator_contract` equality check that is unreachable through normal typed
  construction (the `Literal` already rejects unknown contracts); it only guards
  against low-level forgery.
- The PRIMARY/Judge raw seals are pure foundations; they are not yet wired into the
  live runtime failure path (that wiring is H2-B and remains unauthorized).

Status: `READY FOR H2-A INDEPENDENT REVIEW`.

---

## Phase H1-B Correction Round 3 — adversarial behavioral evidence

### Metadata and scope

- Task: `TASK-016C H1-B Correction Round 3` only.
- Direct parent: `b249341`.
- Test implementation commit: `b07f4e2` —
  `test(task016c): exercise H1 repair forgery attacks`.
- Status: `READY FOR REVIEW`; no production design changed. Phase G,
  `TrustedPersistenceEntry`, `persist_success()`, and H2 repair execution remain
  untouched.

### Adversarial behavioral evidence

- A test creates the exact private `_AdmissionExecutionState` with
  `object.__new__`, populates its fields via `object.__setattr__`, installs it at
  the live runtime execution key, and attempts both REPAIR and REPAIR-Judge
  dispatch. Both are denied and the Judge provider receives zero calls.
- A captured exact admission-state object is copied, deep-copied, and pickled /
  restored after a hostile lock/role replacement. Each restored state is installed
  at the active runtime key; direct REPAIR and REPAIR-Judge dispatch remain denied
  and the Judge provider receives zero calls.
- A real language-invalid PRIMARY trusted-scoring failure is captured, deep-copied
  and pickled. Its diagnostic metadata is injected into a forged REPAIR identity;
  direct REPAIR and runtime REPAIR-Judge dispatch remain denied, with zero Judge
  calls and unchanged Job/Video records.
- A real post-contact `UNKNOWN_PROVIDER_STATE` is captured. Its diagnostics cannot
  admit REPAIR or REPAIR Judge: exactly one PRIMARY provider call is recorded, no
  Judge call occurs, and Job/Video records remain unchanged.

### Reuse and validation

- Reuse decision: `DIRECT` — existing H1 fake providers, temporary SQLite runtime
  harness, pytest `monkeypatch`, and standard-library `copy`, `pickle`, and
  `object.__setattr__`; no dependency, schema, registry capability, persistence,
  network, cloud, or Vault change.

| Command | Result |
|---|---|
| `uv run --offline pytest tests/unit/test_task016c_phase_h1_admission.py -q` | PASS (`31 passed`) |
| `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` | PASS (`76 passed`) |
| `uv run --offline pytest tests/integration/test_runtime_composition.py -q` | PASS (`7 passed`) |
| `uv run --offline mypy src` | PASS (`29 source files`) |
| `uv run --offline ruff check .` | PASS |
| `git diff --check` | PASS |

### Diff review and remaining risk

- The implementation commit changes only the authorized H1 test file; this
  subsequent commit records evidence only.
- No production source, schema, dependency, secret, real Vault, provider/network
  call, Phase G boundary, or H2 capability was changed.

## Phase H1-B Correction Round 2 — internal-only repair control flow

### Metadata and scope

- Task: `TASK-016C H1-B Correction Round 2` only.
- Direct parent: `bc78cc7`.
- Implementation commit: `83a9b5f` — `fix(task016c): internalize H1 repair control flow`.
- Status: `READY FOR REVIEW`; Phase G `TrustedPersistenceEntry` and
  `persist_success()` are unchanged. H2 repair execution, repair persistence,
  recovery, schema, and later work were not started.

### Corrections delivered

- Removed the exposed repair identity factory, the runtime continuation factory,
  the callable runtime repair-admission method, and the admission-level repair
  admission method.
- Removed `repair_identity` and failure-class fields from process-local admission
  state and failure exceptions. The shared state retains only the normal dispatch
  consumption budget; there is no canonical repair identity for a caller to
  replace.
- Public `ScoringDispatchAdmission.admit()` now rejects both `REPAIR` and
  `REPAIR_JUDGE` before consulting mutable state. A caller can neither forge a
  continuation nor promote a copied identity, exception, or modified registry
  state into repair admission.
- Received PRIMARY failures remain diagnostic-only and fail closed. A future H2
  implementation must introduce REPAIR only as a runtime-local branch immediately
  after its own verified PRIMARY dispatch; this correction does not dispatch,
  persist, retry, or recover repair work.

### RED/GREEN and adversarial evidence

- RED: the H1 suite initially failed on the exposed runtime continuation and on
  public `REPAIR_JUDGE` paths that consulted mutable state before denial.
- GREEN: H1 tests prove callers receive no repair continuation/factory, fake
  continuation paths are denied, `object.__setattr__` cannot add/replace repair
  authority, exception replay cannot enable repair, copy/deepcopy/pickle does
  not preserve repair authority, and `UNKNOWN_PROVIDER_STATE` cannot enter
  REPAIR or REPAIR Judge admission.

### Reuse and validation

- Reuse decision: `DIRECT` — existing standard-library `copy`, `pickle`,
  `object.__setattr__`, pytest, and the existing H1 shared-admission registry;
  no dependency, schema, lockfile, persistence, network, cloud, or Vault change.

| Command | Result |
|---|---|
| `uv run --offline pytest tests/unit/test_task016c_phase_h1_admission.py -q` | PASS (`29 passed`) |
| `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` | PASS (`76 passed`) |
| `uv run --offline pytest tests/integration/test_runtime_composition.py tests/integration/test_state_store.py tests/integration/test_pipeline.py -q` | PASS (`58 passed`) |
| `uv run --offline pytest -x -q` | PASS (`1311 passed`; one pre-existing Pydantic serializer warning) |
| `uv run --offline mypy src` | PASS (`29 source files`) |
| `uv run --offline ruff check .` | PASS |
| `git diff --check` | PASS |

### Diff review and remaining risk

- Implementation diff is limited to `runtime.py`, `scoring_admission.py`, and
  the H1 admission tests; the subsequent handoff commit records evidence only.
- No dependencies, schema, migration, secrets, real Vault, network/cloud call,
  Phase G persistence boundary, or H2 implementation was touched.
- Remaining risk: H2 must implement any future REPAIR dispatch as a single
  runtime-local control-flow branch, without reintroducing any caller-visible
  authority, factory, continuation, token, or exception-carried authorization.

## Phase H1-B Correction Round 1 — sealed repair eligibility provenance

### Metadata and scope

- Task: `TASK-016C H1-B Correction Round 1` only.
- Direct parent: `8784c64`.
- Implementation commit: `7972ea5` — `fix(task016c): seal repair eligibility provenance`.
- Status: `READY FOR REVIEW`; Phase G `TrustedPersistenceEntry` is unchanged. H2
  repair execution, repair persistence, recovery, schema, and all later work were
  not started.

### Corrections delivered

- Removed `_PrimaryFailureReceipt`, its sentinel, and every caller-supplied
  `runtime_receipt_authority` path. `ScoringDispatchAdmission.admit()` now rejects
  all public REPAIR requests fail-closed.
- A scoring-stage-only, stack-local closure is created immediately after the
  runtime-owned PRIMARY dispatch returns. It rechecks the exact admission,
  active lease, consumed PRIMARY role, exact PRIMARY attempt/raw hash, trusted
  scoring context, and closed eligible failure class before storing the derived
  REPAIR identity in process-local admission state.
- `_KnownPrimaryFailure` carries only the closed failure classification; exception
  paths expose neither a receipt nor a REPAIR identity. A direct public
  `run_primary_trusted_scoring()` call cannot activate repair eligibility.
- `UNKNOWN_PROVIDER_STATE` reaches no PRIMARY-failure closure and leaves
  `repair_identity` absent. The public REPAIR/Judge boundary remains denied.

### Adversarial evidence

- H1 tests prove that the receipt class and sentinel are no longer importable;
  caller-controlled admission authority is rejected by the constructor; and a
  `ScoringDispatchIdentity` forged via `object.__new__` plus
  `object.__setattr__` cannot admit REPAIR.
- Copy, deepcopy, and pickle restoration of a REPAIR-shaped identity cannot
  bypass the runtime-owned admission boundary. An UNKNOWN provider result followed
  by the same forgery remains denied. Exception objects are asserted not to expose
  `receipt` or `repair_identity`.

### Reuse and validation

- Reuse decision: `DIRECT` — existing Python standard-library closure, copy, and
  pickle behavior plus the existing H1 admission registry; no dependency, schema,
  lockfile, persistence, network, or Vault change.

| Command | Result |
|---|---|
| `uv run --offline pytest tests/unit/test_task016c_phase_h1_admission.py -q` | PASS (`29 passed`) |
| `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` | PASS (`76 passed`) |
| `uv run --offline pytest tests/integration/test_pipeline.py tests/integration/test_state_store.py tests/integration/test_task015_p1_fix.py -q` | PASS (`97 passed`) |
| `uv run --offline pytest -x -q` | PASS (`1311 passed`, one pre-existing Pydantic serialization warning) |
| `uv run --offline mypy src` | PASS (`29 source files`) |
| `uv run --offline ruff check .` | PASS |
| `git diff --check` | PASS |

---

## Phase H1-A Correction Round 2 — shared active-lease admission

### Metadata and scope

- Task: `TASK-016C Phase H1-A Correction Round 2` only.
- Baseline: `49f4409`.
- Implementation commit: `2fbf94b` — `fix: share H1 admission by active scoring lease`.
- Status: `READY FOR REVIEW`; H1-B, H2, H3, repair execution, recovery, schema,
  and Phase G changes were not started.

### Corrections delivered

- `ScoringAdmissionRegistry` now owns a process-local, shared admission object and
  consumption state for each active execution key: repository scope, Job, owner,
  and attempt number. Separate `RuntimeOperations` instances using the same active
  lease receive the same admission object; independently constructed admission views
  still resolve the same consumption state.
- PRIMARY, REPAIR, PRIMARY Judge, and REPAIR Judge consumption therefore remains
  fail-closed across concurrent invocations. The existing lease, ownership, expiry,
  and provider-state checks still execute before every external call.
- Provider construction was separated from provider contact. Factory/client
  construction failures now raise `ScoringDispatchDenied` before contact; only an
  exception from `primary_attempt()` after that call begins becomes
  `UnknownProviderState`.
- `TrustedPersistenceEntry`, `persist_success()`, state schema, and all Phase G
  files remain unchanged.

### Behavioral and mutation evidence

- H1 tests now use two real `RuntimeOperations` over one SQLite scoring Job, prove
  that their admission accessor returns the same object, and prove concurrent
  PRIMARY dispatch permits exactly one provider dispatch. Separate admission
  instances are likewise blocked; REPAIR and Judge duplicate/concurrent behavior
  is covered through distinct admission views.
- Real runtime construction covers factory failure as pre-contact dispatch denial
  and a provider that records call start then times out/interrupts as
  `UnknownProviderState`. Existing terminal unknown restart/retry-block evidence
  remains in the H1 state-machine test.
- Mutation proof: replacing shared state with a fresh state per admission made 8 H1
  duplicate/concurrency/budget tests fail. Reclassifying factory failure as
  `UnknownProviderState` made the pre-contact factory test fail. Both mutations were
  restored before commit.

### Validation

| Command | Result |
|---|---|
| `uv run --offline pytest tests/unit/test_task016c_phase_h1_admission.py tests/unit/test_task016c_phase_g.py tests/integration/test_pipeline.py tests/integration/test_state_store.py -q` | PASS (`148 passed`) |
| `uv run --offline mypy src` | PASS (`29 source files`) |
| `uv run --offline ruff check .` | PASS |
| `git diff --check` | PASS |

---

## Phase H1-A Correction Round 1 — Judge admission and unknown provider state

### Metadata and scope

- Task: `TASK-016C Phase H1-A Correction Round 1` only.
- Baseline: `c692681` (`docs: record H1-A admission evidence`).
- Implementation commit: `1a2873f` — `fix: close H1 judge admission and unknown outcomes`.
- Status: `READY FOR REVIEW`; stop here. H1-B, H2, H3, repair execution, and recovery work were not started.

### Corrections delivered

- `RuntimeOperations.run_primary_trusted_scoring()` and its private continuation now
  require a `ScoringDispatchAdmission`; the Judge dispatch seam always admits the
  PRIMARY/REPAIR Judge identity immediately before provider contact. There is no
  `admission=None` path.
- Admission consumption is locked, so one shared runtime gate permits at most one
  PRIMARY Judge and one REPAIR Judge dispatch (Judge budget `<= 2`), and concurrent
  reuse fails closed. Existing provider states, including `PENDING`, remain blocking.
- Post-contact PRIMARY or Judge exceptions are classified as
  `UnknownProviderState`, not `ScoringDispatchDenied`/`INVALID_RESPONSE`.
  `PipelineOrchestrator` atomically finalizes the owned SCORING JobAttempt and Job as
  `FAILED_FINAL` with existing persisted diagnostic code `UNKNOWN_PROVIDER_STATE`.
  The terminal Job cannot be reclaimed or retried after restart.
- The existing Phase G trusted persistence entry and `persist_success()` boundary
  were not modified. No schema migration, scoring ingress, alternate success writer,
  manual Artifact/ProviderCall success, or repair execution was added.

### Behavioral and mutation evidence

- H1 tests cover no-lease and expired-lease Judge dispatch (provider contact count
  remains zero), duplicate and concurrent Judge rejection, two-Judge budget
  exhaustion, PRIMARY/REPAIR and Judge identity stability/non-collision, existing
  provider-state blocking, contacted-provider timeout/exception classification,
  atomic terminal unknown persistence/restart/retry blocking, and expired SCORING
  lease finalization.
- Mutation proof: temporarily removing the Judge admission call made 5 H1 tests
  fail (no-lease, expired lease, duplicate, concurrent, and budget). Temporarily
  restoring the former `ScoringDispatchDenied` mapping made the two timeout/exception
  unknown-state tests fail. Both mutations were restored before the implementation
  commit.

### Validation

| Command | Result |
|---|---|
| `uv run --offline pytest tests/unit/test_task016c_phase_h1_admission.py tests/unit/test_task016c_phase_g.py tests/integration/test_pipeline.py tests/integration/test_state_store.py -q` | PASS (`145 passed`) |
| `uv run --offline mypy src` | PASS (`29 source files`) |
| `uv run --offline ruff check .` | PASS |
| `git diff --check` | PASS |

`uv run --offline mypy src tests` was also attempted and is not a project-green
gate: it reports 760 strict typing errors across legacy fixtures and missing
third-party stubs, including unscoped legacy tests that still call the now
admission-required direct seam. The production-source target required for this
implementation is clean.

---

## Legacy Migration-06 — Scoring Unit Harness Trusted Flow Cutover

### Metadata and scope

- Task: `TASK-016C Legacy Migration-06`.
- Base: `6d95e8f` (Legacy Migration-05 handoff evidence).
- Implementation commit: `619ddc6` — `TASK-016C Legacy Migration-06 scoring unit trusted flow cutover`.
- Allowed and changed implementation file: `tests/unit/test_scoring.py` only.
- Reuse decision: `DIRECT` — reuses the existing `RuntimeOperations`, runtime-owned
  `TrustedPersistenceEntry`, `PhaseFTrustedScoringSuccess`, Phase G
  `PREWRITE_VALIDATE`/filesystem/atomic SQLite protocol, offline Ollama Quality
  Judge fake transport, and existing state-store prerequisite APIs. No external
  source, dependency, schema, migration, lockfile, production code, network,
  cloud, or real Vault operation was added.

### Legacy removal and trusted-flow proof

- Removed the legacy success harness: its repository-backed persistence/cache/
  recovery fixtures and all tests that expected `RepositoryBackedScoringService.score()`
  to complete the scoring stage. This unit file no longer creates scoring-success
  Artifacts, successful ProviderCalls, or a `SCORED` video by hand, and has no
  `complete_stage(..., target_status=SCORED)` call.
- The only retained direct legacy invocation is the required negative regression:
  `test_legacy_repository_backed_score_cannot_produce_trusted_scoring_success`.
  It asserts the retired `.score()` route raises `ScoringPersistenceError`, writes
  neither scoring Artifact, and leaves the Video at `TRANSCRIPT_READY` and Job
  `RUNNING`.
- The trusted-success test executes exactly:

  ```text
  canonical PrimaryScoringAttempt
    -> RuntimeOperations.run_primary_trusted_scoring
    -> PhaseFTrustedScoringSuccess
    -> RuntimeOperations._trusted_persistence_entry(...).persist_success
    -> PREWRITE_VALIDATE -> filesystem -> atomic SQLite registration
  ```

  It verifies raw/structured Artifact hashes and kinds, the scoring ProviderCall
  request identity/status/raw-artifact binding, and the resulting `SCORED` Video
  plus `SUCCEEDED` Job.
- Invalid provider response parsing is rejected before trusted persistence and
  proves zero scoring Artifacts, zero scoring ProviderCall, a non-`SCORED` Video,
  and a `RUNNING` Job. Duplicate trusted persistence uses a fixed test clock and
  proves exactly two scoring artifacts and two provider calls (scoring + quality
  judge), with no duplicate output.
- Existing scoring input, sampling, cache, threshold policy-disagreement, and
  frozen cache-dimension assertions remain. The cache hash test still covers
  prompt, schema, and operation-version changes.

### Validation

| Command | Result |
|---|---|
| `./.venv/bin/pytest tests/unit/test_scoring.py -q` | PASS (`9 passed`) |
| `./.venv/bin/pytest tests/integration/test_task015_p1_fix.py -q` | PASS (`46 passed`) |
| `./.venv/bin/pytest tests/integration/test_state_store.py -q` | PASS (`36 passed`) |
| `./.venv/bin/pytest tests/integration/test_pipeline.py -q` | PASS (`15 passed`) |
| `./.venv/bin/pytest tests/integration/test_ollama_provider.py -q` | PASS (`72 passed`) |
| `./.venv/bin/pytest tests/e2e/test_mvp_flow.py -q` | PASS (`3 passed`) |
| `./.venv/bin/pytest tests/unit/test_task016c_phase_g.py -q` | PASS (`76 passed`) |
| `./.venv/bin/pytest -x -q` | PASS (`1281 passed, 1 existing warning`) |
| `./.venv/bin/ruff check tests/unit/test_scoring.py` | PASS |
| `git diff --check` | PASS |

The shell does not expose a bare `pytest`; the checked-in `.venv` runner above
is the project environment and is the command actually used for every check.

### Diff review and conclusion

- Implementation diff is limited to the authorized scoring unit harness; this
  handoff commit contains evidence only.
- No dependencies, Schema, migrations, credentials, production source, real
  Vault/cloud operation, retry/recovery/cache implementation, or Phase H work
  was touched.

Status: `IN_REVIEW — Legacy Migration-06 implementation complete; do not enter Phase H.`

---

## Legacy Migration-05 — TASK-015 integration trusted-flow cutover

### 元数据

- Task: `TASK-016C Legacy Migration-05`
- Role: `Implementer`
- Base commit: `3bb2c4b82e7ca5a0ba515d0f6f947ce69aa56592`
- Worktree / branch: `/Users/hua/Documents/yia-worktrees/task-016c-content-quality-layer` / `workbuddy/task-016c-content-quality-layer`
- Reuse decision: `DIRECT` — reuses the accepted Phase F/G runtime-owned
  `RuntimeOperations.run_primary_trusted_scoring()` and
  `RuntimeOperations._trusted_persistence_entry().persist_success()` seams;
  no dependency, source, schema, migration, provider, or filesystem-protocol
  implementation was added or modified.

### 目标、范围与实现

- 目标：迁移 `tests/integration/test_task015_p1_fix.py` 的 legacy scoring
  completion harness，保留 TASK-015 的 scoring artifact/provider recovery
  provenance assertions。
- 实际修改：删除手工 `ScoreResult`、Artifact、ProviderCall SUCCESS 与
  `complete_stage(TRANSCRIPT_READY -> SCORED)` fixture construction。新的 helper
  通过 `RuntimeOperations` 生成 exact `PhaseFTrustedScoringSuccess`，再由
  runtime-minted `TrustedPersistenceEntry.persist_success()` 执行 PREWRITE、文件
  protocol 与 atomic SQLite registration。
- 攻击/回归证据新增：
  - legacy `complete_stage(...SCORED)` 仅在 dedicated attack test 中调用，断言
    `IntegrityConflict` fail-closed，并且无 Artifact、ProviderCall SUCCESS、Video
    `SCORED` 或 Job `SUCCEEDED`；
  - injected `atomic_register.after_pipeline` failure 后断言没有任何已登记的
    Artifact/ProviderCall SUCCESS、Video `SCORED` 或 Job `SUCCEEDED`；
  - 同一 trusted success 重复 persist 后断言恰有两个 scoring artifacts、两个
    provider calls 与两个 JSON outputs，且第二次结果等于第一次；
  - 原有 artifact/file/provider/job/config mutation 的 fail-closed recovery
    coverage 继续使用 trusted-persisted provenance。
- 明确未做：未修改 `src/youtube_intel/`、schema、migration、dependencies、`uv.lock`
  或 Phase G tests；未进入 Phase H；未执行网络、真实 Ollama、cloud 或真实 Vault。

### 验收与检查

| 命令 | 结果 | 证据 |
|---|---|---|
| `uv run pytest tests/integration/test_task015_p1_fix.py -q` | PASS | `46 passed in 3.10s` |
| `uv run pytest tests/integration/test_state_store.py -q` | PASS | `36 passed in 1.81s` |
| `uv run pytest tests/integration/test_pipeline.py -q` | PASS | `15 passed in 2.73s` |
| `uv run pytest tests/integration/test_ollama_provider.py -q` | PASS | `72 passed in 1.91s` |
| `uv run pytest tests/e2e/test_mvp_flow.py -q` | PASS | `3 passed in 3.60s` |
| `uv run pytest tests/unit/test_task016c_phase_g.py -q` | PASS | `76 passed in 3.17s` |
| `uv run ruff check .` | PASS | all checks passed |
| `uv run mypy src` | PASS | 28 source files, no issues |
| `git diff --check` | PASS | no whitespace errors |
| `uv run pytest -x -q` | BLOCKED | first failure: `tests/unit/test_scoring.py::test_repository_backed_scoring_commits_artifacts_call_summary_and_reuses_verified_result` calls legacy `RepositoryBackedScoringService.score()` and receives `ScoringPersistenceError: local scoring stage completion failed` after Phase G closes legacy completion; `1 failed, 649 passed in 28.71s`. |

### Diff 复核与结论

- 修改文件：`tests/integration/test_task015_p1_fix.py`、本 handoff。
- 范围外、依赖、Schema、密钥、真实 Vault、云调用或调度红线：均未触及。
- `pytest -x -q` 的首失败不由本任务 diff 引入（本任务未改 source 或该 unit
  harness），但它与“当前 full pytest 唯一 blocker 为 TASK-015”的输入状态冲突。
  迁移该 legacy unit harness 不在本任务允许文件范围内，需主控另行授权。
- 建议状态：`IN_REVIEW`，TASK-015 migration implementation 已完成；全量绿灯需
  对上述 scope-conflict 作出 `DECISION NEEDED`。

## Phase F accepted-equivalent integration 与 Phase G discovery

- Current Phase G baseline：`2f6e30bd4720e76a72783974704e8e975b6f60c0`，tracked worktree clean。
- 用户已授权把 conflict-free cherry-pick 的线性 integration equivalents 视为 Phase F 的 accepted
  implementation history：`c0268a… -> 61bb0bb…`、`df920cc… -> d059bea…`、
  `931674e… -> 2f6e30b…`。三组 tree/content diff 均为空；不要求 original source SHA 成为
  current HEAD ancestor，严禁 rewrite/rebase/squash/amend 以恢复原 SHA。
- Phase D `2c11faf…` 与 Phase E `9b92946…` 均已核验为当前 HEAD ancestor；Phase F 状态更新为
  `APPROVED`。Phase G design/control-plane 已完成，状态为 `READY / AUTHORIZED / IMPLEMENTATION NOT STARTED`。
- Discovery 事实：legacy `RepositoryBackedScoringService` 在 provider call 前持久化 reserve，随后直接
  写 raw/structured files，最后由 `complete_stage()` 的一笔 SQLite transaction 登记 Artifact、完成 call、
  更新 score/stage/job；它没有 tmp/fsync/promote protocol，filesystem 与 SQLite 不跨资源原子。
- 设计发现并关闭：当前 Phase F success 未保存完整 ScoringInput/quality PASS/attestation evidence，无法在
  “G only accepts success”条件下重验 trusted provenance。G 将最小 enrich 同一 sealed aggregate，以
  canonical bytes/hashes 封存该 evidence；不得以 caller DTO 补信任。
- G future normal path：`primary_attempt -> run_primary_trusted_scoring -> enriched success -> PREWRITE_VALIDATE
  -> ValidatedScoringWritePlan -> verified tmp/promote -> one atomic SQLite registration`。G 不得在 prewrite
  前 reserve/write/cache/stage，不得 provider/Judge recall；repair/recovery/cache verification 仍分别属于 H/I。
- Design authority：[Phase G Amendment](../docs/TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md)。
- 本条仅为 control-plane discovery；未实施 Phase G、未运行真实 provider/network、未写 DB/filesystem。

## Phase F Implementation Authorization（历史控制面；当前状态由上方 integration 条目 supersede）

- Historical status at `acdaac1…`: `READY / AUTHORIZED / IMPLEMENTATION NOT STARTED`。该授权随后已经
  accepted-equivalent linear integration 实施并 APPROVED；本段仅保留历史上下文。
- Authority: `agent-prompts/TASK-016C-PHASE-F-IMPLEMENTATION-AUTHORIZATION.md`、
  `agent-prompts/TASK-016C-PHASE-F-IMPLEMENTER-WORKBUDDY.md` 与
  `docs/TASK-016C-PHASE-F-HANDOFF-CHECKLIST.md`。实现必须是本控制面提交和 Round 4 accepted design
  `e00f957…` 的 descendant，禁止 squash/rebase/history rewrite。
- 唯一阶段顺序已冻结：F=PRIMARY-only、candidate-only 的 non-production in-memory seam；
  G=pre-write validation + persistence registration + production cutover；H=repair/retry/recovery/
  budget；I=derived cache verification/recovery + production hardening/release acceptance。旧 J/K
  验收标签并入 I，不存在 capability 双重归属。
- 兼容生产链 `RuntimeOperations → RepositoryBackedScoringService → bare ScoreResult → persistence`
  仍是 `PRE-TASK-016C COMPATIBILITY PATH`，不能被称为 trusted path；Phase F 不改 default
  dispatch。F future seam 必须 exact-type 拒绝 bare ScoreResult、Mapping、JSON 和 legacy output，
  但不实例化/调用 RepositoryBackedScoringService。G 才可在 persistence boundary 后授权 cutover。
- Finalizer 输出合同已统一为 `TrustedScoringFinalizer -> TrustedScoreResult`。wrapper 内部保留
  已验证的 ScoreResult 业务字段；bare ScoreResult 只可位于 `LEGACY / EXTERNAL COMPATIBILITY
  BOUNDARY`。Phase F-G-H 不授权 internal unwrap。
- F 不拥有 repair/retry/budget/recovery：PRIMARY 任一步失败即 fail-closed，不能自动 repair；
  repair 的 operation identity 与未知 reservation recovery 都留给 H。
- F→G continuation 已冻结为内存 `PrimaryScoringAttempt`：它绑定既有 canonical scoring request
  identity、canonical candidate identity、`raw_response_hash = SHA-256(exact raw UTF-8 bytes)`、provider/model/
  digest、`PRIMARY` role 和唯一权威的 bounded UTF-8 decoded 完整 Provider HTTP JSON raw string。F/G 必须复用
  同一 pure canonical candidate parser，形成 `raw -> parser-derived candidate -> candidate hash -> Finalizer`
  的不可拆分语义链，故 raw A 与 candidate B 不能拼接通过。F 成功只输出
  `PhaseFTrustedScoringSuccess(TrustedScoreResult, PrimaryScoringAttempt)`；attempt 不可信、不可持久化、
  不可恢复且不授权任何写入。G 只能消费该 aggregate 的 raw source，必须按 request/raw hash/same-parser
  reparse/candidate hash/result/attestation 重新交叉验证；不得 provider recall、caller/cache/legacy raw substitution 或用 result
  反向重建 raw。
- 未执行：Phase F–I 代码、Provider/网络、持久化、cache、DB、Artifact、merge 或 history rewrite。

### Round 4 design provenance

- Phase F Runtime Integration Amendment Round 4 已以 `e00f957…` 获独立设计批准：它冻结 exact raw-body hash、
  shared canonical parser 与 F/G raw→candidate revalidation；本授权不改变该设计或扩大 Phase G–I。

## Phase E 实现交接

- Status: `IN_REVIEW`；仅实现纯内存 Trusted Finalizer，尚未进入 Phase F 或持久化。
- Base: `2c11faf41e17c3b823a39bfd1018c5c876b236c5`（Phase D 已批准）；Phase E control-plane
  authorization: `8aa9f0bb99d6c83250407d53bbb63eb909da0212`。
- 目标：建立 runtime-only `TrustedScoringContext`、唯一 canonical scoring request identity、
  `TrustedScoreResult` opaque wrapper 与无副作用 `TrustedScoringFinalizer`。
- 实际修改：
  - `src/youtube_intel/scoring.py`：抽取 `build_scoring_request_identity()`；
    `build_scoring_input()` 与 Repository-backed `_provider_request()` 均复用该纯函数，
    保持既有 request hash 行为。
  - `src/youtube_intel/runtime.py`：仅从已验证的 `AppConfig` 通过 `RuntimeOperations`
    铸造 `TrustedScoringContext`；LocalScoringSettings、Mapping、JSON、Provider、cache 和
    Artifact 均不能单独铸造 capability。
  - `src/youtube_intel/quality.py`：增加 exact-type、private-sentinel、不可复制/序列化/
    子类化的 Context 和 Result wrapper；Finalizer 先检查 capabilities，再重建所有
    不可信 DTO，重算 scoring identity，交叉验证 candidate/quality/attestation provenance，
    最后才创建 `TrustedScoreResult`。
  - `tests/unit/test_task016c_finalizer.py`：覆盖 hash compatibility、真实 Runtime
    authority chain、PASS 最终化、candidate hash 篡改、Mapping capability spoof 与 capability
    直接构造/复制/pickle/subclass 拒绝。
- 明确未做：Provider/Ollama 调用、repair orchestration、ProviderCall、Artifact、cache、
  filesystem、SQLite、migration、依赖或网络调用；Phase F–I 未启动。

### TDD 与验证证据

- RED：新增 Finalizer 端到端测试先因 `TrustedScoringFinalizer` 尚不存在而 collection
  ImportError；canonical identity 测试也先因 builder 不存在而 ImportError。
- GREEN：焦点 finalizer 测试 `3 passed`；与已有 scoring/attestation 回归组合 `159 passed`。
- 全量：`uv lock --check` → PASS；`uv sync --locked --offline` → PASS（84 packages checked）；
  `uv run pytest -x -q` → `1174 passed, 1 warning`；`uv run mypy src` → 28 source files PASS；
  `uv run ruff check .` → PASS；`uv build --offline` → sdist/wheel PASS；
  `bash scripts/security_scan.sh` → `status=clean`（已有非阻断 WARN 与项目 LICENSE unresolved
  warning）；`git diff --check` → PASS。
- 剩余风险：Phase E 只证明内存内 trust/provenance binding。尚未授权/实现 artifact file
  commit、atomic persistence、cache recovery、retry/recovery 或真实模型验证。

### Phase E Correction 1（主控独立式审查发现）

- P1：`TrustedScoringContext` 与 `TrustedScoreResult` 初版可通过普通 attribute assignment
  改写 private slot，破坏 opaque capability 的运行时不可变性。
- RED：`test_finalizer_accepts_only_runtime_bound_pass_material` 在尝试写入 Context language
  时复现 `Failed: DID NOT RAISE TypeError`。
- 修复：两个 wrapper 增加 sealed slot 与 fail-closed `__setattr__`；私有构造仍先使用
  sentinel，实例完成初始化后拒绝任何普通属性赋值。
- GREEN：Phase E focused `3 passed`；修正后重新执行 `uv lock --check`、
  `uv sync --locked --offline`、全量 pytest（`1174 passed, 1 warning`）、`mypy src`
  （28 files）、Ruff、offline build、security scan 与 diff check，均通过。

### Phase E 主控独立式最终复核

- Verdict: `APPROVE`；P0=0、P1=0、P2=0、P3=0。
- Git/范围：`2c11faf` 为 HEAD ancestor；implementation+correction 相对
  `8aa9f0b` 精确为 5 条授权路径（quality/runtime/scoring、Phase E test、handoff）；
  `git diff --check` 通过，worktree clean。
- 信任边界：RuntimeOperations 是唯一 production Context minting path；Finalizer 在读取
  capability 字段前执行 exact-type 验证，重建每个外来 DTO、重算 canonical request
  identity、验证 candidate/quality/attestation 交叉绑定，并只返回 opaque wrapper。
- 对抗覆盖：直接构造、subclass、copy/deepcopy、pickle、普通 slot mutation、Mapping
  capability spoof 和 candidate hash 篡改均 fail-closed；没有 ProviderCall、cache、Artifact
  或 filesystem 副作用。
- 检查复核：lock/offline sync、focused 3、scoring+attestation 159、full pytest 1174、
  mypy 28、Ruff、offline build、security scan clean 与 diff check 均通过；未运行网络、
  实际模型、云、数据库 migration 或 Phase F–I。

## Phase E control-plane authorization

- Status: `READY / AUTHORIZED`；implementation 尚未开始。
- Phase D baseline: `2c11faf41e17c3b823a39bfd1018c5c876b236c5`。
- Authority: `docs/TASK-016C-PHASE-E-AUTHORITY-AMENDMENT-ROUND-3.md`、
  `tasks/TASK-016C-PHASE-E-trusted-scoring-finalizer.md` 与
  `agent-prompts/TASK-016C-PHASE-E-IMPLEMENTER-CODEX.md`。
- 本控制面不含 production/test/dependency 变更；Phase E only，Phase F–K 保持未授权。

## 元数据

- Task: `TASK-016C Phase A`
- Role: `Implementer (Correction Round 1)`
- Agent/session: `WorkBuddy`
- Accepted design baseline: `c547b7c46afbf254979331c2c56cddb93a8503f2`
- Original Phase A implementation commit: `cd9d8b2c41a130aadfc828559d537611f341850a`
- Correction Round 1 commit: `e9ffe699c52d1c2f4a20f9322df3c5eb445b1cf5`
- Correction Round 1.1 commit: `e8ccc2d9e3b348d23942450b3f99861cdbc25aa3`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-016c-content-quality-layer`
- Branch: `workbuddy/task-016c-content-quality-layer`
- Started: `2026-08-14`
- Reported: `2026-08-14`

### Git 事实澄清

- `5ddc5f66c42433097e04f3d7adbb86fec61126dd` 是旧 handoff 元数据中的错误 base，不是 Phase A implementation base。
- `0b78787d9cbc7bd253e150c6ba6a13100ea9a955` 是 accepted-design baseline `c547b7c...` 的 sibling control-plane 子节点，用于冻结设计状态与任务卡；它不是 implementation branch 的 ancestor，本次 correction 未 cherry-pick/merge 该 commit。
- Control-plane history integration 由 Codex / Orchestrator 在 Phase A accepted 后另行处理。

### 设计状态

- Round 4.6 Independent Design Review verdict: `APPROVE FOR IMPLEMENTATION`
- Accepted design SHA: `c547b7c46afbf254979331c2c56cddb93a8503f2`
- 工作树里的 design headers 仍可能显示旧 `PROPOSED / INDEPENDENT DESIGN REVIEW REQUIRED` 文本，这是 control-plane ancestry 问题，不代表设计未批准。

## 目标与范围

- 任务目标：在 `src/youtube_intel/domain.py` 中建立 Content Quality Layer 的领域契约（Phase A），为后续 Deterministic Gate、Local Quality Judge、Finalizer、Attestation 与持久化提供可信输入边界。
- 本次 correction 范围：仅关闭 Codex Independent Review 在 Phase A 中明确列出的 P1/P2 findings。
- 允许修改：
  - `src/youtube_intel/domain.py`
  - `tests/unit/test_task016c_domain_contracts.py`
  - `handoffs/TASK-016C.md`
- 实际修改：
  - `src/youtube_intel/domain.py`：修正 `ContentQualityResult` REJECT 矩阵分派；补全 Evidence Registry canonical ordering、uniqueness、count/total-size bound；统一 `ScoringEvidence.evidence_id` 与 `ContentQualityResult.evidence_ids` 的 lexical/length contract。
  - `tests/unit/test_task016c_domain_contracts.py`：新增 26 项 RED-before-GREEN 测试（P1-1 矩阵 11 项、P1-2 registry 8 项、revalidation 2 项，以及 annotation 修复触发的覆盖），总计 59 项；Correction Round 1.1 再补充 1 项独立 total-character 测试与 1 项旧测试缺陷证明，总计 60 项。
  - `handoffs/TASK-016C.md`：修正 base/original/correction SHA、design status、test coverage 与验证结果。
- 明确未做：Deterministic Gate 实现、Local Quality Judge 调用、H1/H2 persistence、Quality PASS Attestation、`TrustedScoringFinalizer`、pre-write validation、`ValidatedScoringWritePlan`、Artifact 文件提交协议、原子 DB 登记、cache recovery、CLI 改动、数据库 migration、新依赖。

## P1-1 矩阵修正

### Gate REJECT

- 实现按 `decision_source` 明确分派：Gate 路径完成 source-specific validation 后不再落入 Local_Judge REJECT matrix。
- 三个 deterministic reason 全部合法：`EMPTY_CONTENT`、`CONTROL_CHARACTER_INVALID`、`EXACT_REPETITION`。
- Gate REJECT 强制：signals 为空、evidence_ids 为空、Judge identity 为空、confidence = HIGH/LOW/LOW。

### Grounding REJECT

- `LOCAL_JUDGE + REJECT + GROUNDING_INSUFFICIENT` 现在合法。
- grounding REJECT 的 usefulness confidence 边界为 `{LOW, MEDIUM, HIGH}`（ frozen matrix ）。
- grounding REJECT 要求 `grounding_confidence == LOW`、包含 `GROUNDING_INSUFFICIENT` signal、不得包含 `GROUNDING_PRESENT`。

### 负向矩阵

- Gate REJECT 使用 Judge-only reason → 拒绝。
- Local Judge REJECT 使用 Gate-only reason → 拒绝。
- UNCERTAIN 使用 deterministic rejection reason → 拒绝。
- PASS 携带 rejection reason → 拒绝。
- source/reason/status 不匹配仍 fail-closed。

## P1-2 Evidence Registry 修正

### Evidence ID 单一 Contract

- `_validate_evidence_identity` 是 `ScoringEvidence.evidence_id` 与 `ContentQualityResult.evidence_ids` 共享的唯一入口。
- 约束：non-empty、无空白-only、最大长度 100。

### Registry Uniqueness

- `ContentQualityInput.evidence_registry` 拒绝重复的 `evidence_id`（fail-closed，不采用 last-write/first-write/silent dedupe）。

### Canonical Ordering

- `ContentQualityInput.evidence_registry` 按 `evidence_id` 字典序稳定排序。
- 语义相同、输入排列不同的 registry 得到相同的 validated representation。

### Registry Bounds

- 条目数上限：100（复用项目既有 registry 模式）。
- 总字符上限：200,000（= 100 × 单条 excerpt 上限 2000，从 frozen per-item limit 推导）。
- 单条上限：`evidence_id` ≤ 100、`excerpt` ≤ 2000（已冻结）。
- Correction Round 1.1 已补充独立 total-character 回归测试，确保 count bound 不掩盖 total bound。

### Registry / Result 分离

- `ContentQualityResult.evidence_ids` 仅复用与 registry 相同的 identity lexical/length contract。
- 未实现 cross-object registry-membership validation（留给后续 Finalizer/Wrapper phase）。

## TDD RED Evidence

Correction 开始时新增测试全部 RED：

- 失败数：17
- 失败类别：
  - Gate REJECT 合法路径被错误拒绝（4 例）
  - grounding REJECT 合法 usefulness 边界被错误拒绝（4 例）
  - Evidence Registry canonical ordering / duplicate / count / total-size 未生效（4 例）
  - `ContentQualityResult.evidence_ids` 长度约束未与 `ScoringEvidence.evidence_id` 对齐（2 例）
  - Gate / grounding REJECT 的 trusted JSON revalidation 失败（2 例）
  - 另有 1 例测试期望去重但实际应拒绝重复，已按 fail-closed 修正测试本身

## Correction Round 1.1：独立 total-character 测试

### 旧测试缺陷

`test_evidence_registry_rejects_total_chars_above_max` 原实现使用 101 条 excerpt 最大长度（2000）的 evidence。该输入已经违反条目数上限（100），因此即使删除总字符上限校验，旧测试仍然会因 count bound 失败，无法独立证明总字符上限存在。

### RED Evidence

新增 `test_evidence_registry_old_total_chars_test_depended_on_count_bound`：

- 构造与原测试相同的 101 条 max-length registry；
- 通过 monkeypatch 将 `_MAX_EVIDENCE_REGISTRY_TOTAL_CHARS` 放大 100 倍，模拟移除总字符上限；
- 验证该输入仍因 "at most 100 items" 被拒绝。

这证明旧测试无法区分 count validation 与 total-character validation。

### GREEN Evidence

新增/替换 `test_evidence_registry_rejects_total_chars_above_max`：

- 使用恰好 100 条 evidence（count 合法，不触发 count bound）；
- 每条 excerpt 取 frozen 单条上限 2000，evidence_id 取最短合法长度；
- 总字符 = 100 × (2000 + 1..3) = 200100+，超过 frozen 总上限 200,000；
- 验证仅因 "total characters" 被拒绝。

## GREEN Evidence

| 检查 | 结果 |
|---|---|
| Phase A focused tests (`tests/unit/test_task016c_domain_contracts.py`) | 60 passed |
| TASK-016B language regression (`tests/unit/test_scoring_language.py`) | 101 passed |
| 全量 unit tests (`tests/unit`) | 456 passed |
| 全量 pytest | 912 passed, 2 warnings |
| `uv lock --check` | PASS |
| `uv run ruff check .` | PASS |
| `uv run mypy src` | PASS |
| `uv run youtube-intel --help` | PASS |
| `uv build --offline` | PASS |
| `bash scripts/security_scan.sh` | `status=clean` |
| `git diff --check cd9d8b2..HEAD` | PASS |

## 失败、跳过与风险

- 已解决失败：P1-1 Gate/grounding REJECT 矩阵、P1-2 Evidence Registry contract（含 Correction Round 1.1 独立 total-character 测试）、P2-1 handoff 元数据。
- 剩余风险：
  - Phase A 仍为纯内存 schema/matrix 验证契约，未涉及真实 Ollama、SQLite 持久化、文件提交协议或 cache recovery。
  - Registry 总字符上限 200,000 是从 frozen per-item excerpt limit（2000）与既有项目 registry count pattern（100）推导得出；frozen design 文本中未显式给出总上限数字。
- `DECISION NEEDED`：无（Phase A correction 范围内）。

## 实现者结论

- 建议状态：`IN_REVIEW / CORRECTION ROUND 1 COMPLETE`
- 复现/验证说明：
  ```bash
  uv lock --check
  uv run ruff check .
  uv run mypy src
  uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py
  uv run pytest -x -q tests/unit/test_scoring_language.py
  uv run pytest -x -q
  uv run youtube-intel --help
  uv build --offline
  bash scripts/security_scan.sh
  git diff --check cd9d8b2..HEAD
  ```

## Reviewer 结论

- Reviewer agent/session：
- 审查 commit：
- 重新运行的检查：
- Findings：
- Verdict：`APPROVE | REJECT`
- 未解决 P0/P1：

## 主控验收

- Orchestrator：
- Verdict：`ACCEPT | REJECT`
- 依据：
- 批准整合的 commit：

## 整合结果

- Integrator：
- 主线 commit：
- 整合后检查：
- 最终状态：`DONE | BLOCKED`

---

# TASK-016C Phase B 交接报告

## 元数据

- Task: `TASK-016C Phase B`
- Role: `Implementer`
- Agent/session: `WorkBuddy`
- Phase B authorization commit: `0f558f36376f3f113e68d1ab7a2e5969aabd0073`
- Phase B implementation commit: `7e5e71d02e9d270a69da9f140d2ff7e7c9a92061`
- Phase B correction round commit: see 实现者结论 below
- Worktree: `/Users/hua/Documents/yia-worktrees/task-016c-content-quality-layer`
- Branch: `workbuddy/task-016c-content-quality-layer`

## 目标与范围

- 任务目标：实现纯本地的 `DeterministicContentQualityGate`，仅覆盖 `EMPTY_CONTENT`、`CONTROL_CHARACTER_INVALID`、`EXACT_REPETITION` 三类 REJECT；所有结构合法但未命中门控的内容返回 `None`，交给后续阶段。
- 允许修改：
  - `src/youtube_intel/quality.py`
  - `tests/unit/test_task016c_quality_gate.py`
  - `handoffs/TASK-016C.md`
- 实际修改（原始 Phase B commit）：
  - `src/youtube_intel/quality.py`：新建 `DeterministicContentQualityGate`，按 raw empty → raw control scan → ASCII-whitespace empty → exact-repetition 顺序分类；结果通过 `ContentQualityResult.model_validate` 构造 DETERMINISTIC_GATE REJECT。
  - `tests/unit/test_task016c_quality_gate.py`：新建 35 项 RED-before-GREEN 测试，覆盖三类 REJECT、边界、结果契约与 mutation killers。
- 明确未做：Local Quality Judge、H1/H2 persistence、Quality PASS Attestation、`TrustedScoringFinalizer`、pre-write validation、`ValidatedScoringWritePlan`、Artifact 文件提交协议、原子 DB 登记、cache recovery、CLI 改动、数据库 migration、新依赖。

## Phase B 原始 RED/GREEN Evidence

- 原始 Phase B commit `7e5e71d` 实施前，`src/youtube_intel/quality.py` 不存在，35 项新增测试全部 RED（ImportError / 未实现失败）。
- 实现后：
  - `tests/unit/test_task016c_quality_gate.py`：35 passed
  - 全量 pytest：948 passed, 2 warnings（来自 Phase A 既有 bypass-revalidation 测试）
  - `uv run mypy src`：PASS
  - `uv run ruff check .`：PASS
  - `git diff --check`：PASS
- Mutation 验证（均已还原）：临时移除 control validation、使用 `lower()`/`casefold()` 比较、移除 exact-empty filter 均导致对应测试失败。

## Phase B Correction Round 1

### 范围声明

- 本 correction round 仅修正 Review 发现的 P1-1 顺序回归、增加 P1-2 frozen CONTINUE adversarial vectors，并补充 P2-1 handoff 说明。
- 本 correction commit **不**重新证明原始 Phase B RED chronology；原始 RED/GREEN evidence 已由 `7e5e71d` 记录。

### P1-1 CONTROL_CHARACTER 检测顺序

- 问题：原始实现先执行 `_is_empty()`（含 ASCII trim），导致 `\r`、`\v`、`\f` 等 raw control characters 被错误归类为 `EMPTY_CONTENT`。
- 修正：`_classify()` 现在严格按 `raw empty → raw control-character scan → ASCII-whitespace empty → EXACT_REPETITION` 顺序执行。
- 结果：
  - `\r`、`\v`、`\f`、`\x00`、`\u200b`、`\ufeff` 单独出现均返回 `CONTROL_CHARACTER_INVALID`。
  - `""`、`" "`、`"   "`、`"\t"`、`"\n"` 等仅含合法 ASCII whitespace 的内容返回 `EMPTY_CONTENT`。
- 测试：新增 `test_cr_only_rejects_control`、`test_vt_only_rejects_control`、`test_ff_only_rejects_control`；修正 `test_ascii_whitespace_only_rejects` 仅使用 space/TAB/LF。

### P1-2 冻结 CONTINUE adversarial vectors

- 仅增加测试，未增加任何实现逻辑：
  - `"API SDK GPT LLM"`
  - `"Docker Kubernetes Terraform"`
  - `"General Dynamics Corporation"`
  - `"Amazon Connect Salesforce"`
- 目的：证明 Gate 不包含 token、acronym、entity 或 uppercase heuristic。

### 修改文件

- `src/youtube_intel/quality.py`
- `tests/unit/test_task016c_quality_gate.py`
- `handoffs/TASK-016C.md`

## Correction Round 1 验证结果

| 检查 | 结果 |
|---|---|
| `uv lock --check` | PASS |
| `uv run pytest -x -q tests/unit/test_task016c_quality_gate.py` | 44 passed |
| `uv run pytest -x -q` | 957 passed, 2 warnings |
| `uv run mypy src` | PASS |
| `uv run ruff check .` | PASS |
| `git diff --check` | PASS |

## 实现者结论

- 建议状态：`IN_REVIEW / PHASE B CORRECTION ROUND 1 COMPLETE`
- 复现/验证说明：
  ```bash
  uv lock --check
  uv run pytest -x -q tests/unit/test_task016c_quality_gate.py
  uv run pytest -x -q
  uv run mypy src
  uv run ruff check .
  git diff --check
  ```
- 设计偏差：NONE

---

# TASK-016C Phase C Correction Round 2 交接报告

## 元数据

- Task: `TASK-016C Phase C`
- Role: `Implementer (Correction Round 2)`
- Agent/session: `WorkBuddy`
- Previous correction commit: `69b508b`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-016c-content-quality-layer`
- Branch: `workbuddy/task-016c-content-quality-layer`
- Started: `2026-08-14`
- Reported: `2026-08-14`

## 目标与范围

- 仅关闭独立审查在 Phase C 中剩余的 P1 findings，不扩展 Phase C 范围，不进入 Phase D+。
- 允许修改：
  - `src/youtube_intel/domain.py`
  - `src/youtube_intel/quality.py`
  - `src/youtube_intel/providers/ollama.py`
  - `tests/unit/test_task016c_quality_judge_contract.py`
  - `tests/integration/test_ollama_provider.py`
  - `handoffs/TASK-016C.md`
- 明确未做：ProviderCall persistence、Quality PASS Attestation、`TrustedScoringFinalizer`、pre-write validation、`ValidatedScoringWritePlan`、Artifact 文件提交协议、原子 DB 登记、cache recovery、Primary/Repair 编排、CLI 改动、数据库 migration、新依赖、Phase D+。

## P1-1 H1/H2 可信身份边界

### 问题

`_validated=True` 可通过 `model_construct()`、private attribute 赋值、subclass override、model_dump override 绕过。

### 修正

- 移除 `QualityJudgeOperationInput._validated` 可变标记与 after-validator。
- 禁用 `QualityJudgeOperationInput.model_construct()`，任何构造绕过直接失败。
- `build_judge_h1_h2` 仅接受精确类型 `QualityJudgeOperationInput`，拒绝 subclass。
- 身份计算前必须从原始 `__dict__` 重新执行一次 `model_validate`，使 overridden `model_dump`/property 无法影响 H1/H2。
- 修改文件：
  - `src/youtube_intel/domain.py`
  - `src/youtube_intel/quality.py`
  - `tests/unit/test_task016c_quality_judge_contract.py`

### 新增回归测试

- `test_model_construct_and_private_marker_injection_fails`
- `test_subclass_property_override_rejected_for_h1_h2`
- `test_model_dump_override_rejected_for_h1_h2`
- 保留 `test_unchecked_model_copy_update_cannot_produce_trusted_h1`

## P1-2 Trusted policy binding

### 问题

`policy_version` 未与固定 Judge 配置绑定；仅校验了 provider/model/digest/prompt/schema。

### 修正

- `OllamaQualityJudgeProvider._validate_trusted_binding` 增加 `policy_version == _QUALITY_POLICY_VERSION` 检查。
- 任何 mismatch 在发起 transport 前返回 `UNCERTAIN`/`JUDGE_UNAVAILABLE`，零 fake/真实请求。

### 新增回归测试

- `test_config_mismatch_fails_closed_without_transport` 参数化增加 `policy_version`。

## P1-3 Canonical Judge Payload Boundary

### 问题

Judge 请求参数 `reason=None`、`topics=()`  defaults 允许空评估材料；payload 不是 canonical、bounded、identity-bound。

### 修正

- `OllamaQualityJudgeProvider.judge` 改为要求 `content_input: ContentQualityInput`。
- 新增 `build_content_quality_input_hash`（`src/youtube_intel/quality.py`），对 `ContentQualityInput` 做精确类型检查 + raw `__dict__` 重验证 + canonical SHA-256。
- Provider 在校验 trusted binding 与 loopback 之后、transport 之前验证：
  - `content_input` 精确类型为 `ContentQualityInput`；
  - `content_input.candidate_hash == operation_input.candidate_hash`；
  - `content_input.scoring_request_hash == operation_input.scoring_request_hash`；
  - `build_content_quality_input_hash(content_input) == operation_input.quality_input_hash`。
- 任何失败 fail closed 为 `UNCERTAIN`/`JUDGE_UNAVAILABLE`，不发出请求。
- Prompt 仅由固定前缀 + 一个 canonical JSON payload 组成，payload 包含：
  - `judge_identity`（H1）
  - `quality_input_hash`
  - `language`
  - `candidate_reason`
  - `candidate_topics`
  - `evidence_registry`（id + excerpt）
- 无 raw 字符串插值，无空默认评估材料。
- `ContentQualityInput.evidence_registry` 增加非空校验，确保 payload Nonempty。

### 新增回归测试

- `test_missing_payload_is_rejected`
- `test_noncanonical_payload_type_is_rejected`
- `test_quality_input_hash_mismatch_is_rejected`
- `test_payload_requires_nonempty_reason_topics_and_evidence`
- `test_judge_request_payload_contains_bounded_evaluation_content` 改为解析 prompt 中单一 canonical JSON 并校验字段。

## P2 Loopback URL 变体

### 新增测试

`test_non_loopback_base_url_fails_closed_before_transport` 覆盖：

- `https://example.com`
- `http://example.com:11434`
- `http://user@127.0.0.1:11434`
- `http://127.0.0.1:11434?query=1`
- `http://127.0.0.1:11434#fragment`

复用现有 `_validate_loopback_http_base_url`，所有变体在 transport 收到请求前返回 `UNCERTAIN`。

## TDD RED Evidence

本次 correction 先写测试再实现。由于接口签名变化，原有部分调用在修正前直接触发 `TypeError`/`ImportError`；针对新增回归用例的 RED 表现：

- `test_model_construct_and_private_marker_injection_fails`：修正前 `model_construct` 成功 + private marker 注入后 `build_judge_h1_h2` 返回可信身份。
- `test_subclass_property_override_rejected_for_h1_h2`：修正前 subclass 被接受，H2 使用被覆盖 property。
- `test_model_dump_override_rejected_for_h1_h2`：修正前 subclass 被接受，H2 使用被篡改 `model_dump`。
- `test_config_mismatch_fails_closed_without_transport[policy_version]`：修正前 policy mismatch 仍发起 transport 并返回 `PASS`。
- `test_missing_payload_is_rejected`、`test_noncanonical_payload_type_is_rejected`、`test_quality_input_hash_mismatch_is_rejected`：修正前新 signature 不存在，调用异常或绕过 payload 校验。
- `test_judge_request_payload_contains_bounded_evaluation_content`：修正前 prompt 使用多字段 `.format` 插值，非 canonical JSON。

**RED chronology 说明**：Phase C 原始实现 commit `da1154d` 的 RED evidence 已由该 commit 记录；Correction Round 1 commit `69b508b` 的 RED evidence 已由该 commit 记录。本 Round 2 仅针对新增/调整用例记录 RED，不重新证明前序 RED chronology。

## GREEN Evidence

| 检查 | 结果 |
|---|---|
| `uv lock --check` | PASS |
| `uv sync --locked --offline` | PASS |
| `uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py` | 57 passed |
| `uv run pytest -x -q tests/integration/test_ollama_provider.py` | 71 passed |
| `uv run pytest -x -q` | 1017 passed, 2 warnings |
| `uv run mypy src` | PASS |
| `uv run ruff check .` | PASS |
| `git diff --check` | PASS |

## 修改文件

- `src/youtube_intel/domain.py`
  - `QualityJudgeOperationInput`：移除 `_validated`，禁用 `model_construct`。
  - `ContentQualityInput.evidence_registry`：增加非空校验。
- `src/youtube_intel/quality.py`
  - `build_judge_h1_h2`：精确类型检查 + raw `__dict__` 重验证。
  - 新增 `build_content_quality_input_hash` 与内部 `_revalidated_fields`/`_canonical_json` helper。
- `src/youtube_intel/providers/ollama.py`
  - `OllamaQualityJudgeProvider.judge`：改为要求 `content_input`。
  - `_validate_trusted_binding`：增加 `policy_version` 校验。
  - 新增 `_validate_content_input_identity`。
  - `_generate`：prompt 改为固定前缀 + canonical JSON payload。
- `tests/unit/test_task016c_quality_judge_contract.py`：新增/调整 57 项测试。
- `tests/integration/test_ollama_provider.py`：调整 Judge 调用为新的 payload API，新增 `_judge_content_input` helper。
- `handoffs/TASK-016C.md`：本报告。

## 失败、跳过与风险

- 已解决：P1-1 H1/H2 信任边界、P1-2 policy_version 绑定、P1-3 canonical payload boundary、P2 loopback URL 变体。
- 剩余风险：
  - 同进程内存模型下 `object.__setattr__` 仍可修改 `__dict__`；本修正通过“每次都从 raw `__dict__` 重验证”将风险转化为“只能传入有效数据”，但不具备密码学防篡改能力。
  - `ContentQualityInput` 非空 evidence 约束是新增强制规则；后续调用方需保证至少一条 evidence。
- `DECISION NEEDED`：无（Phase C correction 范围内）。

## 实现者结论

- 建议状态：`IN_REVIEW / PHASE C CORRECTION ROUND 2 COMPLETE`
- 复现/验证说明：
  ```bash
  uv lock --check
  uv sync --locked --offline
  uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py
  uv run pytest -x -q tests/integration/test_ollama_provider.py
  uv run pytest -x -q
  uv run mypy src
  uv run ruff check .
  git diff --check
  ```
- 设计偏差：NONE

---

# TASK-016C Phase C Correction Round 3

## 元数据

- Role: `Implementer (Correction Round 3)`
- Agent/session: `WorkBuddy`
- Parent commit: `eba5420f3ab89076f99c527743a55a11c99fa3fd`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-016c-content-quality-layer`
- Branch: `workbuddy/task-016c-content-quality-layer`
- Started: `2026-08-14`
- Reported: `2026-08-14`

## 目标与范围

- 仅关闭 Phase C Correction Round 2 Independent Review 剩余的 3 个 P1 与相关 P2 gaps。
- 禁止进入 Phase D；禁止扩大 Phase C 范围。
- 允许修改：
  - `src/youtube_intel/domain.py`
  - `src/youtube_intel/quality.py`
  - `src/youtube_intel/providers/ollama.py`
  - `tests/unit/test_task016c_quality_judge_contract.py`
  - `tests/integration/test_ollama_provider.py`
  - `handoffs/TASK-016C.md`
- 明确未做：scoring.py、state.py、runtime composition、Artifact、cache、DB、migration、ProviderCall persistence、Attestation、Finalizer、filesystem protocol、Phase D+。

## P1-1 — H1/H2 可信身份边界

- 问题：`QualityJudgeOperationInput` 的 deprecated `copy(update=...)` 仍可产生被修改的实例并进入 `build_judge_h1_h2`。
- 修复：在 `QualityJudgeOperationInput` 上覆盖 `copy()`，当 `update is not None` 时直接抛 `ValueError`；`model_copy(update=...)` 已由 `_UpdateProtectedQualityContract` 拒绝。
- 回归测试：
  - `test_deprecated_copy_update_cannot_produce_trusted_h1`
  - `test_unchecked_model_copy_update_cannot_produce_trusted_h1`
  - `test_unchecked_model_construct_cannot_produce_trusted_h1`
  - `test_subclass_property_override_rejected_for_h1_h2`
  - `test_model_dump_override_rejected_for_h1_h2`

## P1-2 — Judge 入口处立即重建

- 问题：`OllamaQualityJudgeProvider.judge()` 在信任重建前读取原始 operation input 的属性，subclass spoof 可到达 `GET /api/tags`。
- 修复：`judge()` 入口立即通过 `_revalidated_fields` 重建 `QualityJudgeOperationInput` 与 `ContentQualityInput`；所有后续 binding/loopback/identity/transport 逻辑只使用重建后的精确基类对象。
- 回归测试：
  - `test_subclass_getattribute_spoof_emits_zero_transport`
  - `test_subclass_model_dump_spoof_emits_zero_transport`
  - `test_model_construct_operation_input_emits_zero_transport`
  - `test_malformed_content_input_fails_closed_without_validation_error`
  - `test_zero_transport_on_content_input_hash_mismatch`

## P1-3 — 恢复空 Evidence Registry

- 问题：Correction Round 2 未经授权地给 `ContentQualityInput.evidence_registry` 增加了非空约束，导致 `ContentQualityResult` PASS 矩阵也要求至少一个 evidence ID。
- 修复：
  - 移除 `ContentQualityInput._canonical_registry` 中的非空检查。
  - 移除 `ContentQualityResult._validate_pass_matrix` 中 "PASS requires at least one evidence ID" 的检查。
  - 保留 canonical ordering、duplicate ID rejection、registry bounds、evidence ID lexical constraints。
- 回归测试：
  - `test_empty_evidence_registry_is_valid`
  - `test_empty_evidence_registry_hash_is_deterministic`
  - `test_judge_with_empty_evidence_registry_succeeds`

## 相关 P2 — Malformed Content Input Fail-Closed

- 问题：`ContentQualityInput.model_construct(...)` 绕过验证后，judge 内部重建时可能抛出 `ValidationError` 给调用方。
- 修复：`judge()` 入口的重建/身份验证全部包裹在 `try/except` 中，任何失败返回 `UNCERTAIN` 且零 transport。
- 回归测试：`test_malformed_content_input_fails_closed_without_validation_error`。

## TDD RED Evidence

Round 3 先写测试再实现。RED 阶段失败类别：

- `test_deprecated_copy_update_cannot_produce_trusted_h1`：修正前 `copy(update={"judge_model": ...})` 成功返回被修改实例。
- `test_subclass_getattribute_spoof_emits_zero_transport`：修正前 subclass 通过信任绑定，发出 `GET /api/tags`。
- `test_malformed_content_input_fails_closed_without_validation_error`：修正前 `ContentQualityInput.model_construct(...)` 进入 judge 后抛出 `ValidationError`。
- `test_empty_evidence_registry_is_valid` / `test_empty_evidence_registry_hash_is_deterministic` / `test_judge_with_empty_evidence_registry_succeeds`：修正前空 registry 直接触发 `ValidationError`。

**RED chronology 说明**：本 Round 3 仅针对新增/调整用例记录 RED；前序 Round 的 RED evidence 已分别由 `da1154d`、`69b508b`、`eba5420` 记录，Git 历史未重写。

## GREEN Evidence

| 检查 | 结果 |
|---|---|
| `uv lock --check --offline` | PASS |
| `uv sync --locked --offline` | PASS |
| `uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py` | 67 passed |
| `uv run pytest -x -q tests/integration/test_ollama_provider.py` | 71 passed |
| `uv run pytest -x -q` | 1027 passed, 2 warnings |
| `uv run mypy src` | PASS |
| `uv run ruff check .` | PASS |
| `git diff --check` | PASS |

## 修改文件

- `src/youtube_intel/domain.py`
  - `QualityJudgeOperationInput.copy()`：拒绝 `copy(update=...)`。
  - `ContentQualityInput._canonical_registry`：移除非空约束。
  - `ContentQualityResult._validate_pass_matrix`：移除对空 evidence_ids 的拒绝。
- `src/youtube_intel/providers/ollama.py`
  - `OllamaQualityJudgeProvider.judge()`：入口立即重建 operation/content input；重建失败 fail-closed；所有后续逻辑只使用重建对象。
- `tests/unit/test_task016c_quality_judge_contract.py`：新增/调整 10 项 Round 3 回归测试，总计 67 项。
- `handoffs/TASK-016C.md`：本报告。

## 失败、跳过与风险

- 已解决：P1-1 copy/update identity bypass、P1-2 reconstruction-at-entry、P1-3 empty evidence registry、P2 malformed content fail-closed。
- 剩余风险：同进程内存模型下物理内存篡改不在本合约防御范围内；每次重建仍依赖 Python 运行时提供的 `__dict__` 隔离。
- `DECISION NEEDED`：无（Phase C correction 范围内）。

## 实现者结论

- 建议状态：`IN_REVIEW / PHASE C CORRECTION ROUND 3 COMPLETE`
- 复现/验证说明：
  ```bash
  uv lock --check
  uv sync --locked --offline
  uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py
  uv run pytest -x -q tests/integration/test_ollama_provider.py
  uv run pytest -x -q
  uv run mypy src
  uv run ruff check .
  git diff --check
  ```
- 设计偏差：NONE

---

# TASK-016C Phase C Correction Round 4

## 元数据

- Role: `Implementer (Correction Round 4)`
- Agent/session: `WorkBuddy`
- Parent commit: `f2827e2dc8a2a3f58f9e4cfe6c21ced310e86bdb`
- Correction commit: `913618c2e4cc834fb4152daec2b884c5a4b88b0f`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-016c-content-quality-layer`
- Branch: `workbuddy/task-016c-content-quality-layer`
- Started: `2026-08-14`
- Reported: `2026-08-14`

## 目标与范围

- 仅关闭 Phase C Correction Round 3 Independent Review 剩余的 2 个 P1 与 2 个 P2 test gaps。
- 禁止进入 Phase D；禁止扩大 Phase C 范围；不重新设计 Phase C。
- 允许修改：
  - `src/youtube_intel/domain.py`
  - `src/youtube_intel/providers/ollama.py`
  - `tests/unit/test_task016c_quality_judge_contract.py`
  - `handoffs/TASK-016C.md`
- 明确未做：`src/youtube_intel/scoring.py`、`src/youtube_intel/state.py`、runtime composition、Artifact、cache、DB、migration、ProviderCall persistence、QualityPassAttestation、TrustedScoringFinalizer、PREWRITE_VALIDATE、filesystem protocol、repair orchestration、TASK-016B production logic、Phase D+。

## P1-1 — 恢复 PASS Evidence Invariant

- 问题：`ContentQualityResult` 的 PASS 矩阵未要求 `evidence_ids` 非空；空 evidence registry 的输入仍可能产生 `PASS` 结果。
- 修复：在 `ContentQualityResult._validate_pass_matrix` 中增加 `evidence_ids` 非空检查。
- 边界：
  - `ContentQualityInput.evidence_registry` 仍可为空。
  - Local Judge 对空 registry 仍可执行并发出请求。
  - Judge 返回 `PASS` 但 `evidence_ids=[]` 时，按 Phase C 既有的 invalid-response 语义 fail-closed 为 `UNCERTAIN`/`JUDGE_INVALID_RESPONSE`。
- 回归测试：
  - `test_pass_with_empty_evidence_ids_rejected`
  - `test_pass_with_one_valid_evidence_id_accepted`
  - `test_judge_empty_registry_pass_with_empty_evidence_fails_closed`
  - 保留 `test_empty_evidence_registry_is_valid`、`test_empty_evidence_registry_hash_is_deterministic`

## P1-2 — Malformed Operation Input Fail-Closed

- 问题：`OllamaQualityJudgeProvider.judge()` 在 operation input 重建失败时，使用原始（可能已损坏）的 operation input 构造 UNCERTAIN 结果；若该对象的 hash/provider/model/digest 字段不合法，`ContentQualityResult.model_validate` 会抛出 `ValidationError`。
- 修复：
  - 将 operation input 重建与 content input 重建分离。
  - operation input 重建失败时，直接返回不依赖任何输入字段的安全 UNCERTAIN 结果：hash 字段使用固定占位符 `"0" * 64`，Judge identity 使用 settings 中的可信 model/digest 与固定 provider。
  - 该路径零 transport、不构造 PASS/REJECT、不持久化、不暴露未验证字段。
- 回归测试：
  - `test_malformed_exact_base_operation_input_fails_closed`：参数化覆盖 provider、model、digest、scoring_request_hash、candidate_hash、quality_input_hash 的非法值。
  - `test_malformed_exact_base_operation_input_returns_no_validation_error`：显式断言无 `ValidationError` 泄露。

## P2 — 独立 Hash Mismatch 测试

- 新增 `test_content_input_hash_mismatch_fails_closed_before_transport`：
  - `candidate_hash` 不匹配：其余 hash 与 quality_input_hash 重新计算保持一致；预期 `UNCERTAIN`/`JUDGE_UNAVAILABLE` 且零 transport。
  - `scoring_request_hash` 不匹配：同上。
  - transport 配置为可成功响应；若移除对应显式比较，测试将因返回 `PASS` 而失败。

## P2 — 真正 Malformed Content Input 测试

- 替换原 `test_malformed_content_input_fails_closed_without_validation_error`（其使用空 registry，在 Round 3 后已是合法输入）。
- 新增 `test_truly_malformed_content_input_fails_closed_without_validation_error`：使用 `ContentQualityInput.model_construct(..., scoring_request_hash="not-a-valid-hash")` 等非法字段；预期 `UNCERTAIN`/`JUDGE_UNAVAILABLE`、零 transport、无 `ValidationError` 泄露。
- 保留独立测试证明空 registry 本身合法。

## TDD RED Evidence

Round 4 先写测试再实现。RED 阶段失败数与类别：

- 失败数：6
- 失败类别：
  - `test_pass_with_empty_evidence_ids_rejected`：PASS 空 `evidence_ids` 未拒绝。
  - `test_judge_empty_registry_pass_with_empty_evidence_fails_closed`：Judge 返回 PASS + 空 `evidence_ids` 被接受。
  - `test_malformed_exact_base_operation_input_fails_closed[scoring_request_hash-not-a-hash]` / `[candidate_hash-not-a-hash]` / `[quality_input_hash-not-a-hash]`：损坏 operation input 导致 `ValidationError` 泄露。
  - `test_malformed_exact_base_operation_input_returns_no_validation_error`：同上。

**RED chronology 说明**：本 Round 4 仅针对新增/调整用例记录 RED；前序 Round 的 RED evidence 已分别由 `da1154d`、`69b508b`、`eba5420`、`f2827e2` 记录，Git 历史未重写。

## GREEN Evidence

| 检查 | 结果 |
|---|---|
| `uv lock --check` | PASS |
| `uv sync --locked --offline` | PASS |
| `uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py` | 78 passed |
| `uv run pytest -x -q tests/integration/test_ollama_provider.py` | 71 passed |
| `uv run pytest -x -q` | 1038 passed, 2 warnings |
| `uv run mypy src` | PASS |
| `uv run ruff check .` | PASS |
| `git diff --check` | PASS |

## 修改文件

- `src/youtube_intel/domain.py`
  - `ContentQualityResult._validate_pass_matrix`：新增 `evidence_ids` 非空检查。
- `src/youtube_intel/providers/ollama.py`
  - `OllamaQualityJudgeProvider.judge()`：分离 operation/content 重建异常处理；operation 重建失败使用 `_build_safe_uncertain_result`。
  - 新增 `_build_safe_uncertain_result()`：不依赖未验证输入字段的安全 fail-closed 结果构造。
- `tests/unit/test_task016c_quality_judge_contract.py`：新增/调整 Round 4 回归测试，总计 78 项。
- `handoffs/TASK-016C.md`：本报告。

## 失败、跳过与风险

- 已解决：P1-1 PASS evidence invariant、P1-2 malformed operation fail-closed、P2 candidate/scoring hash mismatch 独立测试、P2 truly malformed content input 测试。
- 剩余风险：同进程内存模型下物理内存篡改不在本合约防御范围内；安全 fail-closed 路径依赖 `LocalScoringSettings` 在 provider 构造时已验证。
- `DECISION NEEDED`：无（Phase C correction 范围内）。

## 实现者结论

- 建议状态：`READY FOR PHASE C FOCUSED FINAL REVIEW`
- 复现/验证说明：
  ```bash
  uv lock --check
  uv sync --locked --offline
  uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py
  uv run pytest -x -q tests/integration/test_ollama_provider.py
  uv run pytest -x -q
  uv run mypy src
  uv run ruff check .
  git diff --check
  ```
- 设计偏差：NONE

---

# TASK-016C Phase D 交接报告

## 元数据

- Task: `TASK-016C Phase D`
- Role: `Implementer`
- Agent/session: `WorkBuddy`
- Parent commit: `dab0ba9d358c4624fb7619e95bfa034dd4dc70d7`
- Phase D authorization commit: `dab0ba9d358c4624fb7619e95bfa034dd4dc70d7`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-016c-content-quality-layer`
- Branch: `workbuddy/task-016c-content-quality-layer`
- Started: `2026-08-14`
- Reported: `2026-08-14`

## 目标与范围

- 任务目标：实现纯内存 quality `PASS` attestation 和 canonical `quality_result_hash`。重建并哈希完整 `ContentQualityResult(PASS)`；构造并验证 `quality-pass-attestation-v1`；绑定到 candidate / quality-input / request / version / judge / attempt 身份；任何畸形或不匹配值 fail closed。
- 允许修改：
  - `src/youtube_intel/domain.py`
  - `src/youtube_intel/quality.py`
  - `tests/unit/test_task016c_quality_attestation.py`（新建）
  - `tests/unit/test_task016c_domain_contracts.py`（最小改动）
  - `tests/unit/test_task016c_quality_judge_contract.py`（最小改动，实际未改）
  - `handoffs/TASK-016C.md`
- 实际修改：
  - `src/youtube_intel/domain.py`：新增 `QualityPassAttestation` frozen 模型（schema `quality-pass-attestation-v1`），含完整 frozen binding 字段、`evidence_ids` canonical 排序去重 validator、禁用 `model_construct` 与 `copy(update=...)`；在 `_UpdateProtectedQualityContract` 基类增加 `copy(update=...)` 禁用（统一所有 content-quality contract 的 bypass 防御）。
  - `src/youtube_intel/quality.py`：新增 `build_content_quality_result_hash`（untrusted reconstruction -> canonical SHA-256）、`build_quality_pass_attestation`（trusted application-side constructor）、`verify_quality_pass_attestation`（reconstruct + verify attestation_hash + cross-check）、`_reconstruct`（通用 untrusted->trusted 重建）、`_verify_pass_eligibility`（PASS + evidence registry 解析）、`_verify_cross_bindings`（跨 result/operation_input/quality_input 身份绑定）、`_compute_attestation_hash`。
  - `tests/unit/test_task016c_quality_attestation.py`：新建 91 项 RED-first 测试。
  - `tests/unit/test_task016c_domain_contracts.py`：更新 `test_deprecated_copy_update_bypass_is_revalidated` -> `test_deprecated_copy_update_bypass_is_blocked`（反映 `copy(update=...)` 现已被禁用）。
- 明确未做：`providers/ollama.py`、`scoring.py`、`state.py`、`TrustedScoringFinalizer`、trusted ScoreResult construction、Artifact、cache、DB、migration、ProviderCall persistence、PREWRITE_VALIDATE、filesystem protocol、repair orchestration、runtime composition、Phase E-K、dependencies、`pyproject.toml`、`uv.lock`。

## TDD RED Evidence

Phase D 先写测试再实现。RED 阶段所有 91 项测试因 `ImportError: cannot import name 'QualityPassAttestation'` 无法收集，全部 RED。

- RED 失败数：91（collection error）
- RED 失败类别：ImportError（`QualityPassAttestation` 及 `build_content_quality_result_hash` / `build_quality_pass_attestation` / `verify_quality_pass_attestation` 尚不存在）

## GREEN Evidence

| 检查 | 结果 |
|---|---|
| `uv lock --check` | PASS |
| `uv sync --locked --offline` | PASS |
| `tests/unit/test_task016c_quality_attestation.py` | 91 passed |
| `tests/unit/test_task016c_domain_contracts.py` | 60 passed, 1 warning |
| `tests/unit/test_task016c_quality_judge_contract.py` | 78 passed |
| 全量 `pytest -x -q` | 1129 passed, 1 warning |
| `uv run mypy src` | PASS (28 source files) |
| `uv run ruff check .` | PASS |
| `git diff --check` | PASS |

## quality_result_hash Contract Evidence

- `build_content_quality_result_hash` 对 untrusted `ContentQualityResult | Mapping | JSON` 执行 `_reconstruct`（instance -> `_revalidated_fields` 拒绝 subclass；Mapping/JSON -> `model_validate`/`model_validate_json`），然后对 `model_dump(mode="json")` 做 `_canonical_json`（UTF-8、`ensure_ascii=False`、sorted keys、separators `(",", ":")`）+ SHA-256。
- signals 由模型 `_canonical_signals` validator 按 enum value 排序去重；evidence_ids 由 `_canonical_evidence_ids` validator 按 stable ID 排序去重。
- 每个 frozen canonical 字段变化均改变 hash 或使 validation 失败（parametrized 测试覆盖 8 个 hash-changing 字段 + 14 个 validation-failing 字段）。
- Mapping / JSON 等价输入产生相同 hash（`test_mapping_and_json_equivalent_inputs_produce_same_hash`）。
- 手动 canonical JSON 独立验证 hash 值（`test_valid_pass_result_hash_matches_manual_canonical_json`）。

## Attestation Binding Evidence

- `build_quality_pass_attestation` 绑定全部 frozen 字段：candidate_hash、quality_input_hash、quality_result_hash、scoring_request_hash、policy_version、scoring_schema_version、scoring_prompt_version、quality_schema_version、quality_prompt_version、judge_provider、judge_model、judge_model_digest、judge_operation、judge_request_hash (H2)、attempt_role、decision_confidence、grounding_confidence、usefulness_confidence、evidence_ids、attestation_hash。
- `attestation_hash` 覆盖完整 canonical payload，仅排除自身（`test_attestation_hash_covers_full_payload_excluding_itself` 手动验证）。
- H1/H2 只复用 Phase C 已接受 `build_judge_h1_h2`，不重写（`test_attestation_binds_h2_as_judge_request_hash`、`test_h1_and_h2_remain_distinct`）。
- H2 = `build_provider_request_hash("local-content-quality-v1", H1, provider, model, prompt_version, schema_version)`，语义不变。
- confidence 与 evidence_ids 精确 mirror validated result。

## Adversarial / Mutation Evidence

### Bypass 防御

- `model_construct` on `QualityPassAttestation` -> 禁用，raises ValueError。
- `model_copy(update=...)` on `QualityPassAttestation` -> 禁用（继承 `_UpdateProtectedQualityContract`）。
- `copy(update=...)` on `QualityPassAttestation` -> 禁用（新增 override）。
- `copy(update=...)` on `ContentQualityResult` -> 禁用（`_UpdateProtectedQualityContract` 基类新增 override）。
- `model_construct` on `ContentQualityResult` -> 未禁用（Phase A 行为），但 `build_content_quality_result_hash` 通过 `_revalidated_fields` 从 `__dict__` 重建并 re-validate，无效值被拒绝。
- subclass property override -> `_revalidated_fields` 拒绝（`type(instance) is not model`）。
- subclass model_dump override -> `_revalidated_fields` 读 `__dict__` 不读 `model_dump()`，拒绝 subclass。
- fake trusted flag / unknown field -> `extra="forbid"` 拒绝。

### Binding mismatch fail-closed

- candidate_hash / quality_input_hash / scoring_request_hash mismatch -> build raises。
- judge_provider / judge_model / judge_model_digest / policy_version / prompt_version / schema_version mismatch -> build raises。
- non-PASS result -> build raises。
- external evidence ID -> build raises。
- empty registry -> build raises。
- forged attestation_hash -> verify raises。
- forged quality_result_hash -> verify raises。
- H2 mismatch -> verify raises。
- attempt_role mismatch -> verify raises。
- confidence mismatch -> verify raises。
- evidence mismatch -> verify raises。
- scoring_schema_version / scoring_prompt_version mismatch -> verify raises。
- unknown fields -> verify raises。
- forged complete attestation -> verify raises。

### Mutation proof

- 移除 `_verify_cross_bindings` 调用 -> `test_candidate_input_request_hash_mismatch_rejects[candidate_hash]` 失败（DID NOT RAISE）。已还原。

## No-Side-Effect Evidence

- `build_quality_pass_attestation` 和 `verify_quality_pass_attestation` 均为纯内存操作。
- `test_build_creates_no_filesystem_side_effects`：`tmp_path` 下无文件创建。
- `test_verify_creates_no_filesystem_side_effects`：同上。
- `test_attestation_has_no_persistence_identity_fields`：attestation 无 persistence 字段。
- 未导入或调用 `ScoreResult`、`Artifact`、`ProviderCall`、cache、DB、filesystem 模块。

## Reuse Decision

| 组件 | 决策 | 说明 |
|---|---|---|
| `_canonical_json` (quality.py) | DIRECT | 复用 Phase C 已接受 helper。 |
| `_revalidated_fields` (quality.py) | DIRECT | 复用 Phase C 已接受 helper。 |
| `build_judge_h1_h2` (quality.py) | DIRECT | 复用 Phase C 已接受 H1/H2 builder，不重写。 |
| `build_content_quality_input_hash` (quality.py) | DIRECT | 复用 Phase C 已接受 quality input hash。 |
| `build_provider_request_hash` (state.py) | DIRECT | 通过 `build_judge_h1_h2` 间接复用 ADR-003 builder。 |
| `_UpdateProtectedQualityContract` (domain.py) | ADAPT | 在基类增加 `copy(update=...)` 禁用。 |

## 修改文件

- `src/youtube_intel/domain.py`：新增 `QualityPassAttestation` 类；`_UpdateProtectedQualityContract` 新增 `copy(update=...)` 禁用；`__all__` 新增导出。
- `src/youtube_intel/quality.py`：新增 `build_content_quality_result_hash`、`build_quality_pass_attestation`、`verify_quality_pass_attestation` 及内部 helper。
- `tests/unit/test_task016c_quality_attestation.py`：新建 91 项 RED-first 测试。
- `tests/unit/test_task016c_domain_contracts.py`：更新 1 项测试。
- `handoffs/TASK-016C.md`：本报告。

## 失败、跳过与风险

- 已解决：全部 Phase D frozen contract 要求。
- 剩余风险：
  - 同进程内存模型下 `object.__setattr__` 仍可修改 `__dict__`；通过"每次都从 raw `__dict__` 重验证"防御。
  - `ContentQualityResult.model_construct` 未禁用（Phase A 行为）；依赖 `_revalidated_fields` 在入口处重建验证。
  - 1 个 Pydantic serialization warning 来自 Phase A 既有测试，非 Phase D 引入。
- `DECISION NEEDED`：无。

## 实现者结论

- 建议状态：`IN_REVIEW / PHASE D COMPLETE`

---

# Phase D Correction Round 1 — Bind attestation to trusted current provenance

## 目标

关闭 Independent Review 剩余 P1：``build_quality_pass_attestation`` / ``verify_quality_pass_attestation`` 未绑定当前受信配置，导致自洽但未经授权的 provenance 可通过验证。

## 父提交

- ``b22a3ba0d64b8cfb79abb2a3acb261affdf92e92``

## 变更路径

- ``src/youtube_intel/domain.py``：新增 ``TrustedQualityProvenance`` 模型；``__all__`` 导出。
- ``src/youtube_intel/quality.py``：``build_quality_pass_attestation`` / ``verify_quality_pass_attestation`` 改为接收 ``trusted_provenance``；新增 ``_verify_trusted_provenance`` 对 Judge 模型/digest 和 scoring schema/prompt 版本做当前受信上下文校验；``scoring_schema_version`` / ``scoring_prompt_version`` 改为从受信上下文写入，不再由调用方直接指定。
- ``tests/unit/test_task016c_quality_attestation.py``：新增 17 项 RED-first 回归测试，覆盖自洽非法 Judge 模型/digest 在 build 与 verify 阶段被拒绝、scoring 版本在 verify 阶段因受信上下文变化被拒绝、``TrustedQualityProvenance`` 自身 bypass 防御、合法配置仍可通过。

## 信任当前上下文绑定项

- ``judge_provider``
- ``judge_model``
- ``judge_model_digest``
- ``scoring_schema_version``
- ``scoring_prompt_version``

## RED Evidence

- 修正前：未授权模型 ``untrusted-local-model`` + 任意 digest + 任意 scoring 版本可在 build 与 verify 阶段生成/验证有效 attestation。
- 修正后测试写入时：108 项 attestation 测试全部 RED（依赖 ``TrustedQualityProvenance`` 未导入）；其中 17 项为新增 provenance 回归测试。

## GREEN Evidence

- ``tests/unit/test_task016c_quality_attestation.py``：108 passed
- ``tests/unit/test_task016c_domain_contracts.py``：60 passed, 1 warning
- ``tests/unit/test_task016c_quality_judge_contract.py``：78 passed
- ``uv run pytest -x -q``：1146 passed, 1 warning
- ``uv run mypy src``：Success (28 files)
- ``uv run ruff check .``：All checks passed
- ``git diff --check``：passed

## 伪造一致配置证据

- ``test_unauthorized_judge_model_build_rejects``：内部一致的未授权模型无法在授权受信上下文下 build。
- ``test_unauthorized_judge_model_verify_rejects``：使用未授权上下文构建的合法 hash attestation，在授权上下文 verify 时失败。
- ``test_unauthorized_judge_digest_build_rejects``：内部一致的未授权 digest 无法 build。
- ``test_individual_field_mismatch_verify_rejects``：scoring_schema_version / scoring_prompt_version 的受信上下文变化导致 verify 失败。

## 突变证据

- 临时注释 ``_verify_trusted_provenance`` 后，``test_unauthorized_judge_model_build_rejects`` 失败；已回退。

## 范围验证

- ``git diff --name-only`` 仅包含 ``src/youtube_intel/domain.py``、``src/youtube_intel/quality.py``、``tests/unit/test_task016c_quality_attestation.py``。
- 未修改 ``providers/ollama.py``、``scoring.py``、``state.py``、``pyproject.toml``、``uv.lock``、DB、Artifact、cache、Finalizer 等禁止路径。

## 设计偏差

- NONE

## 建议状态

`READY FOR PHASE D FOCUSED INDEPENDENT REVIEW`

- 复现/验证说明：
  ```bash
  uv lock --check
  uv sync --locked --offline
  uv run pytest -x -q tests/unit/test_task016c_quality_attestation.py
  uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py
  uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py
  uv run pytest -x -q
  uv run mypy src
  uv run ruff check .
  git diff --check
  ```
- 设计偏差：NONE

---

# Phase D Correction Round 2 — Close trusted provenance authority boundary

## 目标

关闭 Independent Review 剩余 P1：``TrustedQualityProvenance`` 仍是 caller-authoritative（调用者可自行创建并传入）。必须改为由应用当前配置（``LocalScoringSettings``）通过可信 provenance 工厂生成 ``TrustedQualityProvenance``，再用于 ``build_quality_pass_attestation`` / ``verify_quality_pass_attestation``，确保调用者无法成为信任来源。

## 父提交

- ``721b1c53233dfdea548e1d09e9fb6c0d4470f463``

## 变更路径

- ``src/youtube_intel/quality.py``：
  - 移除 ``build_quality_pass_attestation`` / ``verify_quality_pass_attestation`` 的 ``trusted_provenance`` 参数。
  - 新增模块常量：``_JUDGE_PROVIDER = "ollama"``、``_QUALITY_JUDGE_OPERATION = "local-content-quality-v1"``、``_SCORING_SCHEMA_VERSION = "scoring-schema-v1"``、``_SCORING_PROMPT_VERSION = "scoring-prompt-v1"``。
  - 新增内部工厂 ``_build_trusted_quality_provenance(settings: LocalScoringSettings) -> TrustedQualityProvenance``：仅由应用当前配置生成受信 provenance，调用者无法传入。
  - ``_verify_trusted_provenance`` 增加 scoring_schema_version / scoring_prompt_version 一致性校验。
  - 签名统一改为 ``settings: LocalScoringSettings``。
- ``tests/unit/test_task016c_quality_attestation.py``：
  - 所有 ``trusted_provenance=_authorized_provenance()`` 调用点改为 ``settings=_authorized_settings()``。
  - 新增 ``LocalScoringSettings``/``_authorized_settings``/``_unauthorized_settings`` helper。
  - 保留 ``TrustedQualityProvenance`` 用于域模型级 bypass 测试。
  - 新增 ``test_self_consistent_attacker_provenance_rejected``：证明自洽的攻击者配置（模型/digest 互相对齐但非授权）在授权应用配置下 build 与 verify 均被拒绝。
  - 更新 ``test_scoring_version_mismatch_rejects`` 与 ``test_individual_field_mismatch_verify_rejects``：改为直接篡改 attestation JSON（重算 hash）后使用授权 settings verify，反映 scoring 版本现为应用固定常量。

## 受信边界

- 信任来源：``LocalScoringSettings.model`` + ``LocalScoringSettings.expected_model_digest``（应用当前配置）。
- 固定常量（模块所有）：``judge_provider``、``judge_operation``、``scoring_schema_version``、``scoring_prompt_version``。
- 工厂 ``_build_trusted_quality_provenance`` 是唯一从应用到 ``TrustedQualityProvenance`` 的支持路径。

## RED Evidence

- 修正前（由临时脚本 ``_vuln_demo.py`` 记录）：调用者构造的 ``TrustedQualityProvenance``（模型 ``untrusted-local-model``、digest ``sha256:dddd...``、scoring 版本任意）可成功 build 并 verify 自洽 attestation。
- 新测试 ``test_self_consistent_attacker_provenance_rejected`` 在修正前会失败：build 不会拒绝，verify 不会拒绝。

## GREEN Evidence

| 检查 | 结果 |
|---|---|
| ``uv lock --check --offline`` | PASS |
| ``uv sync --locked --offline`` | PASS |
| ``tests/unit/test_task016c_quality_attestation.py`` | 107 passed |
| 全量 ``uv run --offline pytest`` | 1145 passed, 1 warning |
| ``uv run --offline mypy src`` | Success (28 source files) |
| ``uv run --offline ruff check .`` | All checks passed |
| ``git diff --check`` | PASS |

## 新增关键测试

- ``test_self_consistent_attacker_provenance_rejected``：
  - 使用攻击者 settings 可成功 build（证明输入本身不是非法的，只是非授权）。
  - 同一组输入在授权 settings 下 build 被拒绝。
  - 攻击者 settings 下生成的合法 hash attestation，在授权 settings 下 verify 被拒绝。

## 突变证据

- 临时注释 ``build_quality_pass_attestation`` 中 ``_verify_trusted_provenance`` 调用后，``test_self_consistent_attacker_provenance_rejected`` 失败（DID NOT RAISE）；已回退。

## 范围验证

- ``git diff --name-only`` 仅包含 ``src/youtube_intel/quality.py``、``tests/unit/test_task016c_quality_attestation.py``。
- 未修改 ``src/youtube_intel/domain.py``、``providers/ollama.py``、``scoring.py``、``state.py``、``pyproject.toml``、``uv.lock``、DB、Artifact、cache、Finalizer 等禁止路径。
- 未进入 Phase E。

## 已知基线

- ``tests/unit/test_task016c_quality_attestation.py`` 存在若干 pre-existing mypy 错误（如 ``**{field: value}`` 类型展开、subclass property override 等），本次变更未引入新的 mypy 错误；生产代码 ``src`` 保持 mypy clean。

## 设计偏差

- NONE

## 建议状态

`READY FOR PHASE D FOCUSED INDEPENDENT REVIEW`

- 复现/验证说明：
  ```bash
  uv lock --check
  uv sync --locked --offline
  uv run pytest -x -q tests/unit/test_task016c_quality_attestation.py
  uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py
  uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py
  uv run pytest -x -q
  uv run mypy src
  uv run ruff check .
  git diff --check
  ```
- 设计偏差：NONE

---

# Phase D Correction Round 3 — Close provenance authority boundary

## 目标

关闭 Independent Review 剩余 P1：``LocalScoringSettings`` 仍是 caller-controlled；攻击者可构造任意 model/digest 并通过自洽校验生成有效 attestation。必须完全删除调用者对 trusted provenance 的控制，改为由应用固定配置内部生成。

## 父提交

- ``fc363eba81eb4232d3ec41f66ff091fcfb1314db``

## 本次提交

- Message: ``TASK-016C Phase D correction round 3 close provenance authority boundary``
- SHA: 见 ``git log``（提交信息即上一条）。

## 变更路径

- ``src/youtube_intel/quality.py``：
  - 移除 ``build_quality_pass_attestation`` / ``verify_quality_pass_attestation`` 的 ``settings`` 参数。
  - 移除 ``LocalScoringSettings`` 导入。
  - 新增固定应用常量：``_JUDGE_MODEL = "qwen3:8b"``、``_JUDGE_MODEL_DIGEST = "sha256:" + "b" * 64``。
  - 将内部工厂从 ``_build_trusted_quality_provenance(settings)`` 改为 ``_build_current_quality_provenance()``：无参数，仅从模块常量生成 ``TrustedQualityProvenance``。
  - 更新函数文档，明确调用者无法提供/覆盖任何 provenance 字段。
- ``tests/unit/test_task016c_quality_attestation.py``：
  - 删除 ``_authorized_settings()`` / ``_unauthorized_settings()`` helper。
  - 删除全部 ``settings=...`` 调用点。
  - 重写 ``TestTrustedProvenanceBinding``：
    - 新增 ``test_caller_local_scoring_settings_rejected_by_build``：调用者传入 ``LocalScoringSettings(model="untrusted-local-model", expected_model_digest=UNAUTHORIZED_DIGEST)`` 时 ``build_quality_pass_attestation`` 抛出 ``TypeError``。
    - 新增 ``test_caller_local_scoring_settings_rejected_by_verify``：同上，``verify_quality_pass_attestation`` 抛出 ``TypeError``。
    - 新增 ``test_self_consistent_attacker_inputs_build_rejects``：自洽的攻击者 model/digest 输入在固定配置下 build 被拒绝。
    - 新增 ``test_self_consistent_fake_provenance_verify_rejects``：攻击者手工构造完全自洽、hash 正确的 attestation（fake provenance/operation/result）在 verify 时被拒绝。
    - 移除已失效的 ``test_unauthorized_judge_model_verify_rejects``（无法再用调用者 settings 构建未授权 attestation）。
    - 更新类文档与注释，反映信任来源为应用固定常量。

## 受信边界

- 信任来源：模块级固定常量 ``_JUDGE_PROVIDER``、``_JUDGE_MODEL``、``_JUDGE_MODEL_DIGEST``、``_SCORING_SCHEMA_VERSION``、``_SCORING_PROMPT_VERSION``。
- 调用者无法通过参数提供：``TrustedQualityProvenance``、``LocalScoringSettings`` 或任何 caller-created provenance DTO。
- 唯一内部入口：``_build_current_quality_provenance()``。

## RED Evidence

- 修正前（Round 2 状态）：调用者传入 ``LocalScoringSettings(model="untrusted-local-model", expected_model_digest=UNAUTHORIZED_DIGEST)`` 与自洽输入可成功 ``build`` 并 ``verify`` attestation。
- 本 Round 新增测试在修正前失败：
  - ``test_caller_local_scoring_settings_rejected_by_build`` / ``test_caller_local_scoring_settings_rejected_by_verify``：API 仍接受 ``settings`` 参数，未抛出 ``TypeError``。
  - ``test_self_consistent_attacker_inputs_build_rejects``：未授权输入在 ``settings`` 可控时被接受，未抛出异常。
  - ``test_self_consistent_fake_provenance_verify_rejects``：自洽 fake attestation 在 ``settings`` 可控时可成功 verify。

## GREEN Evidence

| 检查 | 结果 |
|---|---|
| ``uv lock --check`` | PASS |
| ``uv sync --locked --offline`` | PASS |
| ``uv run pytest -x -q tests/unit/test_task016c_quality_attestation.py`` | 109 passed |
| ``uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py`` | 60 passed, 1 warning |
| ``uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py`` | 78 passed |
| ``uv run pytest -x -q`` | 1147 passed, 1 warning |
| ``uv run mypy src`` | Success (28 source files) |
| ``uv run ruff check .`` | All checks passed |
| ``git diff --check`` | PASS |

## 新增关键测试

- ``test_caller_local_scoring_settings_rejected_by_build``：调用者尝试用 ``LocalScoringSettings`` 控制 build，API 直接拒绝（``TypeError``）。
- ``test_caller_local_scoring_settings_rejected_by_verify``：调用者尝试用 ``LocalScoringSettings`` 控制 verify，API 直接拒绝（``TypeError``）。
- ``test_self_consistent_attacker_inputs_build_rejects``：自洽攻击者输入因不符合固定受信配置而被 build 拒绝。
- ``test_self_consistent_fake_provenance_verify_rejects``：攻击者构造 fake provenance + fake operation + fake result 并保证 hash 完全正确，verify 仍因受信配置不匹配而拒绝。

## 突变证据

- 临时注释 ``build_quality_pass_attestation`` 中的 ``_verify_trusted_provenance`` 调用后：
  - ``test_self_consistent_attacker_inputs_build_rejects`` 失败（DID NOT RAISE）。
  - ``test_self_consistent_fake_provenance_verify_rejects`` 失败（DID NOT RAISE）。
  - ``test_unauthorized_judge_model_build_rejects`` / ``test_unauthorized_judge_digest_build_rejects`` / ``test_individual_judge_field_mismatch_build_rejects[...]`` 失败（DID NOT RAISE）。
- 已回退并重新通过全部测试。

## 范围验证

- ``git diff --name-only`` 仅包含 ``src/youtube_intel/quality.py``、``tests/unit/test_task016c_quality_attestation.py``、``handoffs/TASK-016C.md``。
- 未修改 ``src/youtube_intel/domain.py``、``providers/ollama.py``、``scoring.py``、``state.py``、``pyproject.toml``、``uv.lock``、DB、Artifact、cache、Finalizer 等禁止路径。
- 未进入 Phase E。

## 已知基线

- ``tests/unit/test_task016c_quality_attestation.py`` 仍存在若干 pre-existing mypy 错误（如 ``**{field: value}`` 类型展开、subclass property override 等），本次变更未引入新的 mypy 错误；生产代码 ``src`` 保持 mypy clean。

## 设计偏差

- NONE

## 建议状态

`READY FOR PHASE D FOCUSED INDEPENDENT REVIEW`

- 复现/验证说明：
  ```bash
  uv lock --check
  uv sync --locked --offline
  uv run pytest -x -q tests/unit/test_task016c_quality_attestation.py
  uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py
  uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py
  uv run pytest -x -q
  uv run mypy src
  uv run ruff check .
  git diff --check
  ```
- 设计偏差：NONE

---

# Phase D Authority Boundary Amendment — Bind attestation to runtime provenance authority

## 目标

关闭 Phase D 剩余 P1：Round 3 使用硬编码测试身份（``_JUDGE_MODEL`` / ``_JUDGE_MODEL_DIGEST``）作为生产 authority，会同时拒绝真实应用配置。本轮通过 Option A 架构将信任边界迁移到 runtime composition：``already-loaded AppConfig → runtime.py → mint in-memory QualityProvenanceAuthority → quality.py``。

## 父提交

- ``39a1e864238388abe651c466c0a41a023934c872``

## Amendment cherry-pick

- SHA: ``17f0f23eec5263cf30d4b1bc2468480c81b16145``
- Source: ``31d35b82741e0069c4108ea7c4f2601cff54e7c7``
- 说明：仅 cherry-pick 新的 Authority Boundary Amendment；原 ``790644a2771315e5d3f96286ffd39cd4e863cd79`` 已通过 ``dab0ba9d358c4624fb7619e95bfa034dd4dc70d7`` 存在于祖先历史，未重复 cherry-pick。

## 变更路径

- ``src/youtube_intel/domain.py``：
  - 移除 ``TrustedQualityProvenance`` 及其 ``__all__`` 导出。
  - 质量 provenance 的权威表达不再通过可序列化/可构造的 Pydantic DTO。
- ``src/youtube_intel/quality.py``：
  - 新增 ``QualityProvenanceAuthority``：非 Pydantic、私有 sentinel 保护的 opaque runtime-minted 对象。
  - 新增 ``_QualityProvenanceAuthoritySentinel`` / ``_QUALITY_PROVENANCE_AUTHORITY_SENTINEL``：仅 ``runtime.py`` 可通过私有工厂持有 sentinel。
  - 新增 ``_mint_quality_provenance_authority``：私有工厂，接收 sentinel。
  - 删除 Round 3 的硬编码 ``_JUDGE_MODEL`` / ``_JUDGE_MODEL_DIGEST``。
  - ``build_quality_pass_attestation`` / ``verify_quality_pass_attestation`` 改为接收 ``authority: QualityProvenanceAuthority``，拒绝 ``LocalScoringSettings``、``TrustedQualityProvenance``、Mapping、JSON 等 caller-created DTO（``TypeError``）。
  - ``_verify_trusted_provenance`` 扩展为同时校验 quality policy/schema/prompt 版本与 Judge operation identity，全部来自 authority。
- ``src/youtube_intel/runtime.py``：
  - 新增 ``_build_quality_provenance_authority(local_scoring)``：唯一生产路径，从 ``AppConfig.settings.local_scoring`` 的 ``model`` / ``expected_model_digest`` 派生 authority。
  - 新增 ``_mint_quality_provenance_authority_for_test(local_scoring)``：受控测试 seam，仍走同一私有 minting 路径。
  - ``RuntimeOperations.__init__`` 在 composition 时调用上述函数，生成 ``self._quality_provenance_authority``。
- ``tests/unit/test_task016c_quality_attestation.py``：
  - 移除 ``TrustedQualityProvenance`` 导入。
  - 新增 ``REAL_CONFIG_DIGEST`` 常量，用于证明不再依赖 ``sha256:bbbb...``。
  - 新增 ``_current_authority()`` / ``_real_config_authority()`` helper，通过 ``_mint_quality_provenance_authority_for_test`` 从 ``LocalScoringSettings`` 获取 runtime-minted authority。
  - 所有 ``build`` / ``verify`` 调用增加 ``authority=...``。
  - 重写 ``TestTrustedProvenanceBinding``：
    - 新增 ``test_real_current_config_build_and_verify_succeeds``：真实当前 config digest（非 bbbb）可成功 build + verify。
    - 保留 ``test_caller_local_scoring_settings_rejected_by_build`` / ``test_caller_local_scoring_settings_rejected_by_verify``。
    - 新增 ``test_caller_mapping_rejected_as_authority``。
    - 新增 ``test_direct_authority_construction_rejected``：无 sentinel 直接构造 ``QualityProvenanceAuthority`` 失败。
    - 保留并更新 ``test_self_consistent_attacker_inputs_build_rejects`` / ``test_self_consistent_fake_provenance_verify_rejects`` / ``test_configuration_rotation_verify_rejects``。
  - 新增 ``TestQualityProvenanceAuthorityBypass``：证明 authority 无 ``model_copy`` / ``model_construct`` / ``model_validate`` 等 Pydantic bypass 路径。
- ``tests/integration/test_runtime_composition.py``：
  - 新增 ``test_runtime_operations_mints_quality_provenance_authority_from_config``：通过真实 ``load_app_config`` 加载 fixture 配置，验证 ``RuntimeOperations`` 生成的 authority 确实来自 ``AppConfig.settings.local_scoring``，digest 为 ``sha256:{'1' * 64}``（非 bbbb）。

## 受信边界

- 唯一 authority minting boundary：``src/youtube_intel/runtime.py`` 中的 ``_build_quality_provenance_authority``。
- Authority 来源：已经加载并验证的 ``AppConfig.settings.local_scoring.model`` 与 ``expected_model_digest``。
- 冻结常量仍保留在 ``quality.py``：``_JUDGE_PROVIDER``、``_QUALITY_JUDGE_OPERATION``、``_QUALITY_POLICY_VERSION``、``_QUALITY_SCHEMA_VERSION``、``_QUALITY_PROMPT_VERSION``、``_SCORING_SCHEMA_VERSION``、``_SCORING_PROMPT_VERSION``。
- ``quality.py`` 不读取配置文件；authority 由 runtime composition 注入。
- Caller 无法通过 ``LocalScoringSettings``、``TrustedQualityProvenance``、Mapping、JSON 或普通 ``QualityProvenanceAuthority(...)`` 构造绕过 sentinel 检查。

## AppConfig → Authority 路径

```
load_app_config(channels_path, settings_path)
  → AppConfig.settings.local_scoring
      → RuntimeOperations.__init__
          → _build_quality_provenance_authority(config.settings.local_scoring)
              → _mint_quality_provenance_authority(sentinel=private, model=..., digest=...)
                  → QualityProvenanceAuthority
```

## RED Evidence

- 修正前（Round 3 状态）：``quality.py`` 内部使用硬编码 ``_JUDGE_MODEL_DIGEST = "sha256:" + "b" * 64``，无法代表真实应用配置；真实 current config digest（如 ``sha256:{'1' * 64}``）会被拒绝。
- 本 Amendment 新增测试在修正前失败：
  - ``test_real_current_config_build_and_verify_succeeds``：真实 config digest 与硬编码 bbbb 不匹配，build/verify 拒绝。
  - ``test_runtime_operations_mints_quality_provenance_authority_from_config``：runtime 尚未 mint authority，断言失败。
  - ``test_caller_local_scoring_settings_rejected_by_build`` / ``test_caller_local_scoring_settings_rejected_by_verify``：API 仍接受 ``settings`` 参数，未抛出 ``TypeError``（Round 3 已部分覆盖，但 authority 类型检查强化后重新验证）。
  - ``test_direct_authority_construction_rejected``：无 sentinel 时 ``QualityProvenanceAuthority`` 可被直接构造。

## GREEN Evidence

| 检查 | 结果 |
|---|---|
| ``uv lock --check --offline`` | PASS |
| ``uv sync --locked --offline`` | PASS |
| ``uv run pytest -x -q tests/unit/test_task016c_quality_attestation.py`` | 112 passed |
| ``uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py`` | 60 passed, 1 warning |
| ``uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py`` | 78 passed |
| ``uv run pytest -x -q`` | 1151 passed, 1 warning |
| ``uv run mypy src`` | Success (28 source files) |
| ``uv run ruff check .`` | All checks passed |
| ``git diff --check`` | PASS |

## 新增关键测试

- ``test_real_current_config_build_and_verify_succeeds``：真实 current config digest（非 bbbb）可成功 build + verify。
- ``test_caller_local_scoring_settings_rejected_by_build`` / ``test_caller_local_scoring_settings_rejected_by_verify``：caller-created ``LocalScoringSettings`` 无法作为 authority。
- ``test_caller_mapping_rejected_as_authority``：caller-created Mapping 无法作为 authority。
- ``test_direct_authority_construction_rejected``：无 runtime sentinel 无法构造 ``QualityProvenanceAuthority``。
- ``test_self_consistent_attacker_inputs_build_rejects``：攻击者自洽 model/digest 输入 build 被拒绝。
- ``test_self_consistent_fake_provenance_verify_rejects``：攻击者构造完全自洽、hash 正确的 fake attestation，verify 被拒绝。
- ``test_configuration_rotation_verify_rejects``：authority A 创建的 attestation 在 authority B 下 verify 失败。
- ``test_runtime_operations_mints_quality_provenance_authority_from_config``：runtime composition 从 ``AppConfig.settings.local_scoring`` 派生 authority，digest 为真实 fixture 值。

## Mutation Evidence

- 临时破坏 ``src/youtube_intel/runtime.py`` 中 ``_build_quality_provenance_authority`` 的 config-to-digest 绑定，将 ``judge_model_digest=local_scoring.expected_model_digest`` 替换为固定 ``"sha256:" + "f" * 64`` 后：
  - ``tests/unit/test_task016c_quality_attestation.py::TestTrustedProvenanceBinding::test_real_current_config_build_and_verify_succeeds`` 失败（``ValueError: judge_model_digest does not match trusted current provenance``）。
  - ``tests/integration/test_runtime_composition.py::test_runtime_operations_mints_quality_provenance_authority_from_config`` 失败（digest 断言不匹配）。
  - ``test_configuration_rotation_verify_rejects`` 同样因 digest 绑定被破坏而失败。
- 回退 mutation 后，上述测试重新通过。

## 范围验证

- ``git diff --name-only HEAD`` 仅包含：
  - ``src/youtube_intel/domain.py``
  - ``src/youtube_intel/quality.py``
  - ``src/youtube_intel/runtime.py``
  - ``tests/unit/test_task016c_quality_attestation.py``
  - ``tests/integration/test_runtime_composition.py``
  - ``handoffs/TASK-016C.md``
- 未修改 ``providers/ollama.py``、``scoring.py``、``state.py``、DB、cache、Artifact、ProviderCall persistence、Finalizer、Phase E+、依赖、锁文件。
- ``runtime.py`` 变更范围严格限于 authority minting/injection bridge，未扩展 runtime 功能。

## 设计偏差

- NONE

## 建议状态

`READY FOR PHASE D AUTHORITY BOUNDARY INDEPENDENT REVIEW`

- 复现/验证说明：
  ```bash
  uv lock --check --offline
  uv sync --locked --offline
  uv run pytest -x -q tests/unit/test_task016c_quality_attestation.py
  uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py
  uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py
  uv run pytest -x -q
  uv run mypy src
  uv run ruff check .
  git diff --check
  ```
- 设计偏差：NONE

---

# Phase D Correction Round 4 — Close authority minting boundary

## 目标

关闭 Independent Review 剩余两个 P1：

- P1-1：`QualityProvenanceAuthority` 接受 `isinstance(authority, QualityProvenanceAuthority)`，导致 subclass/property override/proxy/spoofed attribute 可通过信任边界。
- P1-2：`_mint_quality_provenance_authority_for_test(LocalScoringSettings)` 是 caller-controlled minting seam，违反 ADR-026 要求的 `AppConfig → Runtime composition → QualityProvenanceAuthority` 单一边界。

## 父提交

- ``23d3f1c727b948ace6bb0ac8eefa7858f17c07cf``

## 变更路径

- ``src/youtube_intel/quality.py``：
  - ``build_quality_pass_attestation`` / ``verify_quality_pass_attestation`` 的信任边界检查由 ``isinstance(authority, QualityProvenanceAuthority)`` 改为 ``type(authority) is QualityProvenanceAuthority``。
  - 拒绝 subclass、property override 对象、proxy 对象、spoofed attribute 对象。
- ``src/youtube_intel/runtime.py``：
  - 删除 ``_mint_quality_provenance_authority_for_test(local_scoring: LocalScoringSettings)`` 及全部相关导入/引用。
  - 唯一保留的 minting 路径是 ``_build_quality_provenance_authority``，由 ``RuntimeOperations.__init__`` 在 composition 时调用。
- ``tests/unit/test_task016c_quality_attestation.py``：
  - 移除 ``_mint_quality_provenance_authority_for_test`` 导入。
  - 新增 ``_write_minimal_project`` / ``_runtime_authority`` / ``_default_authority_project`` helper：所有 authority 必须通过 ``load_app_config`` → ``RuntimeOperations`` → ``QualityProvenanceAuthority`` 获得。
  - 新增 ``TestQualityProvenanceAuthoritySubclassRejection``：6 项回归测试覆盖 subclass 覆盖 ``judge_model``、``judge_model_digest``、``scoring_schema_version`` / ``scoring_prompt_version`` 在 build 与 verify 阶段均被拒绝。
  - 新增 ``TestQualityProvenanceAuthorityMintingBoundary``：
    - ``test_caller_local_scoring_settings_cannot_mint_authority``：断言测试 seam 已删除，且 ``LocalScoringSettings`` 作为 authority 被 ``TypeError`` 拒绝。
    - ``test_caller_fake_provenance_cannot_mint_authority``：caller-created fake provenance DTO 作为 authority 被 ``TypeError`` 拒绝。
  - 更新 ``test_real_current_config_build_and_verify_succeeds`` 与 ``test_configuration_rotation_verify_rejects`` 使用 ``tmp_path`` 通过真实 ``RuntimeOperations`` 获取 authority。
- ``tests/integration/test_runtime_composition.py``：
  - ``_project`` 增加 ``model`` / ``digest`` 参数。
  - 新增 ``test_runtime_operations_derives_authority_from_different_model_config``：证明 ``AppConfig`` 加载 ``model: different-model``、``expected_model_digest: sha256:{'1' * 64}`` 后，``RuntimeOperations`` 派生的 authority 包含完全相同的值。

## 受信边界

- 唯一 authority minting boundary：``src/youtube_intel/runtime.py`` 中的 ``_build_quality_provenance_authority``，由 ``RuntimeOperations`` composition 拥有。
- ``quality.py`` 仅接受精确类型 ``QualityProvenanceAuthority`` 的 opaque capability；subclass、property override、proxy、spoofed attribute 均在边界处被 ``TypeError`` 拒绝。
- Caller 无法通过 ``LocalScoringSettings``、fake provenance DTO、Mapping、JSON 或普通 ``QualityProvenanceAuthority(...)`` 构造绕过 sentinel 检查。

## RED Evidence

- 修正前（Round 3 Amendment 状态）：``isinstance`` 检查允许 subclass 覆盖 ``judge_model`` / ``judge_model_digest`` / ``scoring_schema_version`` / ``scoring_prompt_version`` 并通过 build/verify。
- ``_mint_quality_provenance_authority_for_test`` 在修正前存在，调用者可用任意 ``LocalScoringSettings`` mint authority。
- 本 Round 新增测试在修正前失败：
  - ``test_subclass_overriding_judge_model_rejected_by_build`` / ``..._verify``：subclass 被接受，build/verify 成功。
  - ``test_subclass_overriding_judge_model_digest_rejected_by_build`` / ``..._verify``：同上。
  - ``test_subclass_overriding_schema_prompt_rejected_by_build`` / ``..._verify``：同上。
  - ``test_caller_local_scoring_settings_cannot_mint_authority``：测试 seam 存在，``LocalScoringSettings`` 被接受。

## GREEN Evidence

| 检查 | 结果 |
|---|---|
| ``uv lock --check --offline`` | PASS |
| ``uv sync --locked --offline`` | PASS |
| ``uv run pytest -x -q tests/unit/test_task016c_quality_attestation.py`` | 118 passed |
| ``uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py`` | 60 passed, 1 warning |
| ``uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py`` | 78 passed |
| ``uv run pytest -x -q tests/integration/test_runtime_composition.py`` | 9 passed |
| 全量 ``uv run pytest -x -q`` | 1160 passed, 1 warning |
| ``uv run mypy src`` | Success (28 source files) |
| ``uv run ruff check .`` | All checks passed |
| ``git diff --check`` | PASS |

## 新增关键测试

- ``test_subclass_overriding_judge_model_rejected_by_build`` / ``..._verify``
- ``test_subclass_overriding_judge_model_digest_rejected_by_build`` / ``..._verify``
- ``test_subclass_overriding_schema_prompt_rejected_by_build`` / ``..._verify``
- ``test_caller_local_scoring_settings_cannot_mint_authority``
- ``test_caller_fake_provenance_cannot_mint_authority``
- ``test_runtime_operations_derives_authority_from_different_model_config``

## Mutation Evidence

- 临时破坏 ``src/youtube_intel/runtime.py`` 中 ``_build_quality_provenance_authority`` 的 config-to-digest 绑定，将 ``judge_model_digest=local_scoring.expected_model_digest`` 替换为固定 ``"sha256:" + "f" * 64`` 后：
  - ``tests/unit/test_task016c_quality_attestation.py`` 大量测试失败（首个失败为 ``TestQualityPassAttestationConstruction::test_valid_attestation_is_deterministic``，``ValueError: judge_model_digest does not match trusted current provenance``）。
  - ``tests/integration/test_runtime_composition.py::test_runtime_operations_mints_quality_provenance_authority_from_config`` 与 ``test_runtime_operations_derives_authority_from_different_model_config`` 的 digest 断言失败。
- 回退 mutation 后，上述测试重新通过。

## 范围验证

- ``git diff --name-only HEAD`` 仅包含：
  - ``src/youtube_intel/quality.py``
  - ``src/youtube_intel/runtime.py``
  - ``tests/unit/test_task016c_quality_attestation.py``
  - ``tests/integration/test_runtime_composition.py``
  - ``handoffs/TASK-016C.md``
- 未修改 ``providers/ollama.py``、``scoring.py``、``state.py``、DB、cache、Artifact、ProviderCall persistence、Finalizer、Phase E+、依赖、锁文件。
- ``runtime.py`` 变更范围严格限于删除测试 seam；未新增 composition 功能。

## 设计偏差

- NONE

## 建议状态

`READY FOR PHASE D AUTHORITY BOUNDARY INDEPENDENT REVIEW`

- 复现/验证说明：
  ```bash
  uv lock --check --offline
  uv sync --locked --offline
  uv run pytest -x -q tests/unit/test_task016c_quality_attestation.py
  uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py
  uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py
  uv run pytest -x -q tests/integration/test_runtime_composition.py
  uv run pytest -x -q
  uv run mypy src
  uv run ruff check .
  git diff --check
  ```
- 设计偏差：NONE

---

# Phase D Correction Round 5 — Close authority copy/serialization boundary

## 目标

关闭 Independent Review 剩余 P1： native copy/serialization 可制造出被 ``build_quality_pass_attestation`` / ``verify_quality_pass_attestation`` 接受的 ``QualityProvenanceAuthority`` 实例，绕过 runtime composition 单一边界。

## 父提交

- ``2993c688538d47dd1261e5860a2039355be6081d``

## 变更路径

- ``src/youtube_intel/quality.py``：
  - 为 ``QualityProvenanceAuthority`` 新增 ``__copy__`` / ``__deepcopy__``：抛出 ``TypeError("QualityProvenanceAuthority cannot be copied")``。
  - 新增 ``__reduce__`` / ``__reduce_ex__``：抛出 ``TypeError("QualityProvenanceAuthority cannot be serialized")``。
  - 阻止 ``copy.copy``、``copy.deepcopy``、``pickle.dumps``、``pickle.loads`` 制造 accepted authority 实例。
- ``tests/unit/test_task016c_quality_attestation.py``：
  - 新增 ``TestQualityProvenanceAuthorityCopySerialization``：
    - ``test_copy_rejected``
    - ``test_deepcopy_rejected``
    - ``test_pickle_dumps_rejected``
    - ``test_pickle_dumps_all_protocols_rejected``（参数化覆盖协议 0 至 ``pickle.HIGHEST_PROTOCOL``）
    - ``test_build_with_copy_attempt_rejected``
    - ``test_verify_with_copy_attempt_rejected``

## 受信边界

- ``QualityProvenanceAuthority`` 现在是 runtime-minted、non-copyable、non-serializable 的 opaque capability。
- 唯一来源仍为 ``RuntimeOperations`` composition 拥有的 ``_build_quality_provenance_authority``。
- 即使攻击者通过 native copy/serialization 获得一个 type 完全相同的实例，其创建操作本身会失败；无法传递到 build/verify 边界。

## RED Evidence

- 修正前（Round 4 状态）：``copy.copy(authority)`` 与 ``pickle.loads(pickle.dumps(authority))`` 可成功生成 ``QualityProvenanceAuthority`` 实例，并被 ``type(authority) is QualityProvenanceAuthority`` 接受。
- 本 Round 新增测试在修正前失败：
  - ``test_copy_rejected`` / ``test_deepcopy_rejected``：未抛出 ``TypeError``。
  - ``test_pickle_dumps_rejected`` / ``test_pickle_dumps_all_protocols_rejected``：未抛出 ``TypeError``。
  - ``test_build_with_copy_attempt_rejected`` / ``test_verify_with_copy_attempt_rejected``：copy 成功并传入 build/verify 边界。

## GREEN Evidence

| 检查 | 结果 |
|---|---|
| ``uv lock --check --offline`` | PASS |
| ``uv sync --locked --offline`` | PASS |
| ``uv run pytest -x -q tests/unit/test_task016c_quality_attestation.py`` | 124 passed |
| ``uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py`` | 60 passed, 1 warning |
| ``uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py`` | 78 passed |
| ``uv run pytest -x -q tests/integration/test_runtime_composition.py`` | 9 passed |
| 全量 ``uv run pytest -x -q`` | 1171 passed, 1 warning |
| ``uv run mypy src`` | Success (28 source files) |
| ``uv run ruff check .`` | All checks passed |
| ``git diff --check`` | PASS |

## 新增关键测试

- ``test_copy_rejected``：``copy.copy(authority)`` 抛出 ``TypeError``。
- ``test_deepcopy_rejected``：``copy.deepcopy(authority)`` 抛出 ``TypeError``。
- ``test_pickle_dumps_rejected``：``pickle.dumps(authority)`` 抛出 ``TypeError``。
- ``test_pickle_dumps_all_protocols_rejected``：所有 pickle 协议均抛出 ``TypeError``。
- ``test_build_with_copy_attempt_rejected``：无法将 copied authority 传入 ``build_quality_pass_attestation``。
- ``test_verify_with_copy_attempt_rejected``：无法将 copied authority 传入 ``verify_quality_pass_attestation``。

## Mutation Evidence

- 临时注释 ``src/youtube_intel/quality.py`` 中 ``QualityProvenanceAuthority`` 的 ``__copy__`` / ``__deepcopy__`` / ``__reduce__`` / ``__reduce_ex__`` 后：
  - ``TestQualityProvenanceAuthorityCopySerialization::test_copy_rejected`` 失败（DID NOT RAISE ``TypeError``）。
- 回退 mutation 后，上述测试重新通过。

## 范围验证

- ``git diff --name-only HEAD`` 仅包含：
  - ``src/youtube_intel/quality.py``
  - ``tests/unit/test_task016c_quality_attestation.py``
  - ``handoffs/TASK-016C.md``
- 未修改 ``src/youtube_intel/runtime.py``、``providers/ollama.py``、``scoring.py``、``state.py``、DB、cache、Artifact、ProviderCall persistence、Finalizer、Phase E+、依赖、锁文件。

## 设计偏差

- NONE

## 建议状态

`READY FOR PHASE D AUTHORITY BOUNDARY INDEPENDENT REVIEW`

- 复现/验证说明：
  ```bash
  uv lock --check --offline
  uv sync --locked --offline
  uv run pytest -x -q tests/unit/test_task016c_quality_attestation.py
  uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py
  uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py
  uv run pytest -x -q tests/integration/test_runtime_composition.py
  uv run pytest -x -q
  uv run mypy src
  uv run ruff check .
  git diff --check
  ```
- 设计偏差：NONE

---

# TASK-016C Phase F 交接报告 — PRIMARY In-Memory Trusted Scoring Seam

## 元数据

- Task: `TASK-016C Phase F`
- Role: `Implementer`
- Agent/session: WorkBuddy
- Base/authorization commit: `acdaac1dbc0899e2b2b6e9871b1a734c7edb136e`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-016c-content-quality-layer`
- Branch: `workbuddy/task-016c-content-quality-layer`
- Head commit: `c0268a2157d7b9bb99bdc888b2ee493655bbbaa2`
- Direct parent: `acdaac1dbc0899e2b2b6e9871b1a734c7edb136e`
- Commit message: `TASK-016C Phase F implement primary in-memory trusted scoring seam`
- 祖先核验（单父链，无 squash/rebase/rewrite，全部通过）：
  - Phase D 基线 `2c11faf41e17c3b823a39bfd1018c5c876b236c5` = ancestor ✓
  - Phase E 基线 `9b92946a3c156a7c365d808f92f7a1734dcca874` = ancestor ✓
  - Phase F Round 4 设计 `e00f9579bed3ad91a088c7f9a378cb0808308045` = ancestor ✓
  - Phase F authorization `acdaac1dbc0899e2b2b6e9871b1a734c7edb136e` = HEAD^ ✓
- 工作树：tracked 文件干净（仅 untracked `.workbuddy/`，按要求不读取/不提交）。

## 目标与范围

- 任务目标：实现 PRIMARY-only、candidate-only、memory-only 的 trusted scoring seam：
  ```text
  Provider raw response → 唯一 canonical parser → ScoringCandidate
  → candidate/request/raw binding → schema/language/quality → QualityPassAttestation
  → TrustedScoringFinalizer → TrustedScoreResult → PhaseFTrustedScoringSuccess
  ```
- 实际修改（4 文件，+1518/−2）：
  - `src/youtube_intel/providers/ollama.py`（+97）：抽取唯一 canonical parser `parse_scoring_candidate`（bounded raw → strict UTF-8 → JSON → subset-field → `ScoringCandidate.model_validate`）；`OllamaScoringProvider.primary_attempt()` 单次生成 attempt、无 repair path。
  - `src/youtube_intel/scoring.py`（+378）：`PrimaryScoringAttempt`（frozen，10 字段）、`build_primary_scoring_attempt`（exact-type → 重 parse → candidate 相等核对 → identity 重建 → 双 hash）、`mint_phase_f_trusted_scoring_success`（sealed 三 hash、private sentinel、防 copy/deepcopy/pickle/subclass）、`run_primary_trusted_scoring_seam`（全部 binding 再校验 + Finalizer + mint）。顶层不 import `quality`/`ollama`（函数内 lazy import，满足 import-graph 约束）。
  - `src/youtube_intel/runtime.py`（+38）：`RuntimeOperations.run_primary_trusted_scoring()` 薄包装；默认/legacy dispatch 不变。
  - `tests/unit/test_task016c_phase_f.py`（+1007）：28 个 focused 测试。
- 明确未做（授权禁止范围，均未触碰）：
  - 未修改 `state.py`、`quality.py`、`domain.py`、`pyproject.toml`、`uv.lock`。
  - 无 DB/migration、Artifact/cache persistence、ProviderCall completion、filesystem commit protocol、repair/retry/budget/recovery。
  - 无真实 Ollama/network/cloud/Vault/凭据调用；全程离线。
  - 未改变 transport、loopback、model/download/fallback/network semantics；未改 TASK-016B Language Validator；未改默认 persisted runtime dispatch。

## TDD RED Evidence

- 首次运行（RED，收集阶段即失败）：
  ```text
  ImportError: cannot import name 'parse_scoring_candidate' from 'youtube_intel.providers.ollama'
  ```
- 随后以最小 GREEN 逐项点亮 28 个 focused 测试；RED-first 成立（测试先于实现存在并失败）。

## GREEN Evidence

- `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` → `28 passed`
- 28 测试清单（覆盖 Authorization 8 项 TDD/对抗验收、5 项 mutation proof、checklist Implementer Completion 10 项与 Reviewer Matrix 8 项）：
  1. `test_provider_primary_attempt_returns_candidate_only_continuation` — Provider 只产生 Candidate/Attempt，非 `ScoreResult`；2 次 HTTP（GET+POST），无 repair
  2. `test_candidate_business_fields_match_score_result_contract` — candidate 业务字段兼容 `ScoreResult` 契约
  3. `test_attempt_factory_rejects_raw_a_candidate_b` — raw A + candidate B fail-closed
  4. `test_attempt_factory_rejects_post_parse_candidate_mutation` — post-parse candidate mutation 拒绝
  5. `test_attempt_factory_rejects_bare_score_result_candidate` — bare `ScoreResult` 不能充当 candidate
  6. `test_attempt_factory_rejects_mapping_candidate` — Mapping candidate 拒绝
  7. `test_attempt_factory_rejects_oversized_raw` — oversized raw（>1MB）fail-closed
  8. `test_attempt_factory_rejects_invalid_utf8_raw` — invalid UTF-8（`\ud800`）fail-closed
  9. `test_attempt_factory_rejects_oversized_inner_response` — inner response >20k chars 拒绝
  10. `test_one_byte_raw_mutation_changes_raw_hash` — 一 byte raw mutation 改变 raw hash（candidate hash 不变）
  11. `test_semantically_equal_different_bytes_raw_hash_differs` — 语义相同 bytes 不同 JSON → raw hash 不同
  12. `test_attempt_is_frozen_and_exact_type` — attempt frozen + exact-type
  13. `test_seam_rejects_attempt_raw_hash_mismatch` — seam raw hash 再校验拒绝
  14. `test_seam_rejects_attempt_candidate_hash_mismatch` — seam candidate hash 再校验拒绝
  15. `test_seam_rejects_attempt_candidate_not_from_raw` — candidate 非 canonical parse 产物拒绝
  16. `test_seam_rejects_request_identity_mismatch` — request identity mismatch 拒绝
  17. `test_seam_rejects_provider_model_digest_mismatch` — provider/model/digest mismatch 拒绝
  18. `test_seam_rejects_non_primary_attempt_role` — 非 PRIMARY role 拒绝
  19. `test_seam_rejects_bare_score_result` — legacy isolation：bare `ScoreResult` exact-type 拒绝
  20. `test_seam_rejects_mapping_and_json_in_attempt_slot` — legacy isolation：Mapping/JSON exact-type 拒绝
  21. `test_primary_flow_reaches_phase_f_trusted_scoring_success` — 合法 PRIMARY 流到达 aggregate
  22. `test_trusted_result_alone_is_not_a_phase_f_success` — TrustedResult 单独 ≠ envelope（mint 拒绝）
  23. `test_language_failure_blocks_success_aggregate` — language 失败（zh-CN reason + en output_language）阻止 aggregate
  24. `test_quality_reject_blocks_success_aggregate` — quality REJECT（DETERMINISTIC_GATE EMPTY_CONTENT）阻止 aggregate
  25. `test_attestation_mismatch_blocks_success_aggregate` — 异 candidate attestation 阻止 aggregate
  26. `test_success_mint_rejects_forged_trusted_result` — 伪造 TrustedResult exact-type 拒绝
  27. `test_success_aggregate_is_opaque_immutable_and_non_serializable` — 直接构造/copy/deepcopy/pickle/subclass/`_sealed` 变更全拒绝
  28. `test_primary_flow_has_zero_persistence_and_no_legacy_service` — 零持久化（快照相等）+ 无 legacy service

## Mutation Evidence（每项删除 → 对应测试失败 → 立即恢复）

1. **M1** 删除 raw reparse（canonical 重 parse 与 candidate 相等核对）→ `test_seam_rejects_attempt_candidate_not_from_raw` FAILED
2. **M2** 删除 raw-hash comparison（seam + mint 两层同时删除）→ `test_seam_rejects_attempt_raw_hash_mismatch` FAILED
3. **M3** 删除 candidate-hash comparison（seam + mint 两层同时删除）→ `test_seam_rejects_attempt_candidate_hash_mismatch` FAILED
4. **M4** 删除 exact-type trusted-result guard → `test_success_mint_rejects_forged_trusted_result` FAILED（AttributeError）
5. **M5** 删除 legacy isolation guard → `test_seam_rejects_bare_score_result` 与 `test_seam_rejects_mapping_and_json_in_attempt_slot` FAILED
- 全部恢复后：`28 passed` 复确认；无 mutation 残留标记。

## Raw→Candidate Binding Evidence

- 唯一 canonical parser：`parse_scoring_candidate`（`providers/ollama.py`），F 与未来 G 共用；无重复 parser 或 candidate-hash 算法。
- `raw_response_hash = SHA-256(final_raw_response.encode("utf-8"))` 对 exact response-body bytes；不使用 `payload["response"]`、截断值或 reserialized JSON。
- attempt factory 顺序：exact-type 检查 → 重 parse raw → candidate 相等核对 → identity 重建 → candidate/raw hash 计算。
- seam 与 mint 双重再校验：raw hash、candidate hash、canonical reparse、identity（request/normalized hash）、provider/model/digest。
- 测试证明：一 byte raw mutation 改变 raw hash 且不影响 candidate hash；语义相同而 bytes 不同的 JSON 具有不同 raw hash。

## 零副作用 / 零持久化 Evidence

- seam 全程不实例化、不调用 `RepositoryBackedScoringService`（该名称仅出现在 docstring 中）。
- seam 签名不含 provider handle。
- `test_primary_flow_has_zero_persistence_and_no_legacy_service`：项目根与 `data/` 目录 before/after 快照逐项相等（`bootstrap_runtime` 在组合期创建 `data/`，故以快照相等证明零写入）。
- grep 确认 seam 代码无 `state`/`Artifact`/`Cache`/`ProviderCall`/`data_dir`/`Path(` 写入引用；无 repair/retry/budget。

## Legacy Isolation Evidence

- seam 入口 exact-type guard：bare `ScoreResult`、legacy output/raw、Mapping、JSON 均以 `match="PrimaryScoringAttempt"` 拒绝。
- trusted path 永不触达 `ScoreResult`（Finalizer 内部短暂构造 `TrustedScoreResult`，与 legacy `ScoreResult` 类型隔离）。
- `RuntimeOperations → RepositoryBackedScoringService → ScoreResult → persistence` 保持 PRE-TASK-016C COMPATIBILITY PATH 未改动。

## 必须门禁（全部 PASS）

| # | Gate | 结果 |
|---|---|---|
| 1 | `uv lock --check --offline` | Resolved 107 packages, PASS |
| 2 | `uv sync --locked --offline` | Checked 84 packages, PASS |
| 3 | focused Phase F tests | `28 passed` |
| 4 | Phase A–E trust tests（5 个既有 task016c unit 文件 + `test_scoring_language.py`） | `417 passed, 1 warning` |
| 5 | `uv run --offline pytest -x -q`（全量） | `1202 passed, 1 warning`（46s） |
| 6 | `uv run --offline mypy src` | `Success: no issues found in 28 source files` |
| 7 | `uv run --offline ruff check . --output-format concise` | `All checks passed!` |
| 8 | `uv build --offline` | `dist/youtube_intel-0.1.0.tar.gz` + `py3-none-any.whl` 构建成功 |
| 9 | `bash scripts/security_scan.sh` | `status=clean`（仅既有 high-entropy-warn/test artifacts + license WARN） |
| 10 | `git diff --check` | `DIFF-CHECK-CLEAN` |

- 全部命令 `--offline`：uv 在线解析 `en-core-web-sm==3.8.0` 曾报网络/TLS 失败，统一离线后稳定；无下载、无联网、无真实模型调用。

## Reuse Decision

- `parse_scoring_candidate`：由 `ollama.py` 既有 parse 逻辑抽取为唯一 canonical parser（`ADAPT`，同文件内抽取，无新增依赖）。
- `build_scoring_candidate_hash` / `TrustedScoringFinalizer` / `ScoreResult.model_validate`（language fail-closed 强制点，domain.py:825-832）：复用 `quality.py` 既有实现（`DIRECT`，未复制算法）。
- `RepositoryBackedScoringService`：`REJECT/DEFER`——seam 不调用 legacy persistence path，属 Phase G 范围。
- 未新增依赖、未修改 lockfile。

## 设计偏差

1. provider/model mismatch 错误消息措辞加入 `"provider"` 子串（如 `"attempt provider model mismatches..."`、`"attempt provider model digest mismatches the trusted scoring context"`），以满足 `match="provider"` 断言。仅消息措辞，校验行为不变。
2. raw/candidate hash 校验同时存在于 seam 与 mint 两层（defense-in-depth）。单层删除不足以使测试失败，需两层同时删除才暴露——比授权最低要求更强；已作为 M2/M3 mutation 证据记录。

## 失败、跳过与风险

- 已解决失败：
  - uv 在线解析 `en-core-web-sm==3.8.0` 网络/TLS 失败 → 统一 `uv run --offline` / `uv sync --locked --offline`。
  - ruff F401（TYPE_CHECKING 未用导入）与 F841（未用局部变量）→ 清理后通过。
  - `data/` 存在性断言误报（`bootstrap_runtime` 组合期建目录）→ 改为 before/after 快照相等断言。
- 跳过检查及原因：真实 Ollama/network/cloud 执行——授权明确禁止，未执行。
- 剩余风险：
  - 本 seam 为非生产、PRIMARY-only、memory-only；未做默认 runtime cutover（属 Phase G）。
  - `PrimaryScoringAttempt` 是 untrusted continuation，生命周期仅限 aggregate handoff。
- `DECISION NEEDED`：`None`

## 实现者结论

- 建议状态：`READY FOR PHASE F INDEPENDENT REVIEW`
- Commit SHA：`c0268a2157d7b9bb99bdc888b2ee493655bbbaa2`
- 直接父提交：`acdaac1dbc0899e2b2b6e9871b1a734c7edb136e`
- 复现/验证说明：
  ```bash
  uv lock --check --offline
  uv sync --locked --offline
  uv run --offline pytest tests/unit/test_task016c_phase_f.py -q
  uv run --offline pytest -x -q tests/unit/test_task016c_domain_contracts.py tests/unit/test_task016c_finalizer.py tests/unit/test_task016c_quality_attestation.py tests/unit/test_task016c_quality_gate.py tests/unit/test_task016c_quality_judge_contract.py tests/unit/test_scoring_language.py
  uv run --offline pytest -x -q
  uv run --offline mypy src
  uv run --offline ruff check .
  uv build --offline
  bash scripts/security_scan.sh
  git diff --check
  ```

---

## Phase F Correction Round 1

### 审查状态

- 触发审查的 implementation commit：`c0268a2157d7b9bb99bdc888b2ee493655bbbaa2`
- Review verdict：`REQUEST CHANGES`
- 本次 correction implementation commit：`df920cc268f732a5c809ba3d9e0c6b98ea1f44b0`
- 本次直接父提交：`c0268a2157d7b9bb99bdc888b2ee493655bbbaa2`
- 目标状态：`READY FOR PHASE F CORRECTION INDEPENDENT REVIEW`

### 关闭的 P1/P2 问题

- **P1-1** public aggregate mint bypass
  - `mint_phase_f_trusted_scoring_success` 从 `scoring.__all__` 移除并改名为 `_mint_phase_f_trusted_scoring_success`
  - mint 增加 raw reparse 检查：`parse_scoring_candidate(final_raw_response) == attempt.candidate`
  - mint 增加 business-field binding：trusted result 的 score/reason/topics/should_summarize/dimensions 必须与 attempt.candidate 一致
- **P1-2** deterministic gate + Local Judge ordering 缺失
  - `RuntimeOperations.run_primary_trusted_scoring` 现在只接受 `attempt` 和 `scoring_input`
  - 内部构造 `ContentQualityInput`
  - 执行 `DeterministicContentQualityGate.evaluate()`，reject 则 fail closed
  - 执行 `OllamaQualityJudgeProvider.judge()`，非 PASS 则 fail closed
  - 内部用 `self._quality_provenance_authority` 构建 `QualityPassAttestation`
  - 最后调用 private `_run_primary_trusted_scoring_seam`
- **P1-3** runtime caller-selected authority/context
  - `run_primary_trusted_scoring` 不再接受 `quality_authority` / `scoring_context` / 任何 quality material
  - 统一使用 `self._quality_provenance_authority` 和 `self._trusted_scoring_context`
- **P1-4** committed handoff evidence
  - 本 handoff 作为单独 commit 提交
- **P2** provider/model/digest 独立回归测试
  - 新增 `test_seam_rejects_provider_mismatch`
  - 新增 `test_seam_rejects_model_mismatch`
  - 新增 `test_seam_rejects_digest_mismatch_independent`

### RED Evidence

在修代码前加入 RED tests，记录失败证据：

- `test_mint_is_not_a_public_export` FAILED（mint 仍在 `__all__`）
- `test_seam_is_not_a_public_export` FAILED（seam 仍在 `__all__`）
- `test_mint_rejects_raw_a_candidate_b_bypass` FAILED（mint 接受 raw A + candidate B + legitimate TrustedScoreResult B）
- `test_mint_rejects_business_field_mismatch` FAILED（mint 接受 TrustedScoreResult B + attempt A）
- `test_deterministic_gate_blocks_exact_repetition` FAILED / TypeError（runtime 方法仍要求 8 个 kwargs）
- `test_deterministic_reject_prevents_judge_call` FAILED / TypeError
- `test_judge_non_pass_prevents_trusted_success` FAILED / TypeError
- `test_judge_failure_prevents_trusted_success` FAILED / TypeError
- `test_runtime_rejects_quality_authority_param` FAILED（runtime 接受 `quality_authority`）
- `test_runtime_rejects_scoring_context_param` FAILED（runtime 接受 `scoring_context`）
- 合计：10 failed, 31 passed

### GREEN Evidence

- `uv run pytest tests/unit/test_task016c_phase_f.py -q` → `41 passed`

### Mutation Proofs（M1–M6）

每次 mutation 后运行完整 Phase F 测试，记录失败测试，然后恢复并复现 `41 passed`：

- **M1** 删除 mint 所有校验 → `test_trusted_result_alone_is_not_a_phase_f_success`、`test_success_mint_rejects_forged_trusted_result`、`test_mint_rejects_raw_a_candidate_b_bypass`、`test_mint_rejects_business_field_mismatch` FAILED
- **M2** 删除 seam 与 mint 的 raw reparse → `test_seam_rejects_attempt_candidate_not_from_raw`、`test_mint_rejects_raw_a_candidate_b_bypass` FAILED
- **M3** 删除 deterministic gate → `test_quality_reject_blocks_success_aggregate`、`test_deterministic_gate_blocks_exact_repetition`、`test_deterministic_reject_prevents_judge_call` FAILED
- **M4** 将 Judge 调用替换为 synthetic PASS → `test_judge_non_pass_prevents_trusted_success`、`test_judge_failure_prevents_trusted_success` FAILED
- **M5** 允许 `quality_authority` 参数 → `test_runtime_rejects_quality_authority_param` FAILED
- **M6** 允许 `scoring_context` 参数 → `test_runtime_rejects_scoring_context_param` FAILED

### 10 Mandatory Gates

| # | Gate | 结果 |
|---|---|---|
| 1 | `uv lock --check --offline` | PASS |
| 2 | `uv sync --locked --offline` | PASS |
| 3 | focused Phase F tests | `41 passed` |
| 4 | Phase A–E trust tests | `316 passed, 1 warning` |
| 5 | `uv run pytest -x -q` | `1215 passed, 1 warning` |
| 6 | `uv run mypy src` | PASS |
| 7 | `uv run ruff check .` | PASS |
| 8 | `uv build --offline` | PASS |
| 9 | `bash scripts/security_scan.sh` | `status=clean` |
| 10 | `git diff --check` | PASS |

### Scope Verification

- 修改文件：`src/youtube_intel/scoring.py`、`src/youtube_intel/runtime.py`、`tests/unit/test_task016c_phase_f.py`、`handoffs/TASK-016C.md`
- 未修改 `state.py`、DB、migration、Artifact/cache persistence、ProviderCall completion、filesystem protocol、repair/retry、依赖或 lockfile
- 未进入 Phase G
- 未 rebase / squash / amend / merge / push / tag

### Diff Review

- `scoring.py`：将 mint/seam 私有化；mint 增加 raw reparse + business-field binding
- `runtime.py`：`run_primary_trusted_scoring` 改为仅接受 `attempt`/`scoring_input`；内部执行 gate → Judge → attestation → private seam；新增 `quality_judge_provider_factory` 测试注入点
- `tests/unit/test_task016c_phase_f.py`：新增 13 个 RED/regression 测试，更新现有 runtime 测试至新 API

### Reuse Decision

- `DeterministicContentQualityGate`：`DIRECT`（`quality.py` 已有）
- `OllamaQualityJudgeProvider`：`DIRECT`（`providers/ollama.py` 已有）
- `build_quality_pass_attestation` / `TrustedScoringFinalizer`：`DIRECT`（`quality.py` 已有）
- 未新增依赖

### 失败、跳过与风险

- 已解决：
  - RED tests 中部分 `quality_authority`/`scoring_context` 拒绝测试因额外 kwargs 产生误报 → 改为仅传入目标 extra param，使用 `_judge_runtime` 提供 fake Judge
  - exact repetition 测试 reason 因语言检测失败提前退出 → 改用 "This video explains product strategy.\nThis video explains product strategy."
- 跳过：真实 Ollama/network/cloud 执行（授权禁止）
- 剩余风险：
  - 本 seam 仍为非生产、PRIMARY-only、memory-only
  - `RuntimeDependencies.quality_judge_provider_factory` 仅用于测试注入

### 实现者结论

- 建议状态：`READY FOR PHASE F CORRECTION INDEPENDENT REVIEW`
- 复现/验证说明：
  ```bash
  uv lock --check --offline
  uv sync --locked --offline
  uv run --offline pytest tests/unit/test_task016c_phase_f.py -q
  uv run --offline pytest tests/unit/test_task016c_quality_gate.py tests/unit/test_task016c_quality_judge_contract.py tests/unit/test_task016c_domain_contracts.py tests/unit/test_task016c_quality_attestation.py tests/unit/test_task016c_finalizer.py -q
  uv run --offline pytest -x -q
  uv run --offline mypy src
  uv run --offline ruff check .
  uv build --offline
  bash scripts/security_scan.sh
  git diff --check
  ```

## Phase G Implementation

- Status: `READY FOR PHASE G INDEPENDENT REVIEW`
- Authority: `agent-prompts/TASK-016C-PHASE-G-IMPLEMENTATION-AUTHORIZATION.md`、
  `docs/TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md`、
  `docs/TASK-016C-PHASE-G-HANDOFF-CHECKLIST.md`
- Implementation baseline: `bff2b7d514ce4d65f5a2b68d976c5085539e728d`
- Role: Implementer (continuation/recovery)

### 目标与范围

- 任务目标：实现 TASK-016C Phase G trusted prewrite persistence cutover：
  `PREWRITE_VALIDATE -> ValidatedScoringWritePlan -> tmp/fsync/promote -> atomic SQLite registration -> normal scoring-stage cutover`。
- 允许修改：
  - `src/youtube_intel/scoring.py`
  - `src/youtube_intel/runtime.py`
  - `src/youtube_intel/state.py`
  - `tests/unit/test_task016c_phase_g.py`
  - 为 Phase G API 适配所必需的既有集成测试
  - `handoffs/TASK-016C.md`
- 实际修改：
  - `src/youtube_intel/scoring.py`：
    - 向后兼容地 enrich `PhaseFTrustedScoringSuccess`，封存 canonical ScoringInput/quality input/quality result/quality operation/attestation 与 sealed structured-result bytes/hashes；
    - 新增 `_EnrichedQualityEvidence`、`_sealed_trusted_score_result_serializer`；
    - 新增 `TrustedScoringPersistenceCommitter` 与 opaque `ValidatedScoringWritePlan`；
    - 实现 zero-write `prewrite_validate`（exact aggregate、bytes/hash 自洽、domain reconstruction、raw/candidate binding、business-field binding、request identity、runtime authority rotation、quality attestation、raw envelope/structured serialization）；
    - 实现 ordered filesystem writer（tmp exclusive create -> fsync -> hash/length verify -> no-clobber promote -> parent-directory fsync -> final reopen verify）；
    - 实现 `commit` 调用 `SQLiteStateRepository.atomic_register_scoring_success`。
  - `src/youtube_intel/runtime.py`：
    - 新增 `_trusted_scoring_committer` runtime-owned factory；
    - `scoring_stage` 唯一 cutover 到 `build_scoring_input -> primary_attempt -> run_primary_trusted_scoring -> prewrite_validate -> commit`；
    - `_validate_scoring_provenance` 接受 Phase G 新的 producer versions 与 schema/prompt 版本，保持 legacy 读取兼容。
  - `src/youtube_intel/state.py`：
    - 新增 `atomic_register_scoring_success`，在同一 SQLite IMMEDIATE transaction 内完成：验证 RUNNING SCORING job、upsert raw/structured Artifact rows、reserve+complete scoring 与 Judge ProviderCall、更新 video score/threshold/stage、完成 job。
  - `tests/unit/test_task016c_phase_g.py`：新增 21 项 Phase G 焦点测试，覆盖 enriched aggregate、PREWRITE_VALIDATE zero-write、filesystem ordering、atomic registration、idempotency、wrong owner/status、artifact hash binding、runtime cutover、legacy isolation、M1–M10 对抗矩阵。
  - `tests/integration/test_runtime_composition.py` 与 `tests/integration/test_task015_p1_fix.py`：适配 `primary_attempt` API 与 `_QualityJudgeProvider`。
- 明确未做：
  - repair/retry/budget、unknown/crash recovery engine、cache recovery/hardening；
  - 真实 Ollama/network/Cloud/Vault/credential 调用；
  - DB schema/migration、新依赖、`uv.lock`、pyproject.toml；
  - GUI、Web、多用户、V2 数据源；
  - Phase H/I 功能。

### 验收证据

| 验收项 | PASS/FAIL | 证据 |
|---|---|---|
| AC-1: PREWRITE_VALIDATE 零写入且只接受 exact `PhaseFTrustedScoringSuccess` | PASS | `test_prewrite_validate_creates_plan_without_side_effects`、`test_prewrite_validate_rejects_non_aggregate`、`test_prewrite_validate_rejects_unenriched_aggregate` |
| AC-2: filesystem 写入顺序与 no-clobber promote | PASS | `test_commit_writes_raw_and_structured_files`、`test_commit_raises_when_final_file_already_exists`、`test_commit_raises_when_temporary_file_already_exists` |
| AC-3: SQLite 原子登记两 Artifact + 两 ProviderCall + stage/job | PASS | `test_atomic_register_scoring_success_commits_all_rows`、`test_atomic_register_is_idempotent_for_filesystem_then_sqlite_retry` |
| AC-4: runtime scoring-stage 唯一走 trusted route | PASS | `test_scoring_stage_uses_trusted_route`、`test_repository_backed_scoring_service_remains_available_but_not_used` |
| AC-5: M1–M10 mutation matrix 先 RED 再 GREEN | PASS | 见下方 Mutation Proofs |
| AC-6: 全量 gates 通过 | PASS | 见下方 Gates |

### Mutation Proofs（M1–M10）

每次 mutation 临时删除/弱化一个 guard，确认至少一个对应测试失败，然后恢复并复现 `21 passed`：

- **M1** exact success guard：将 `if type(success) is not PhaseFTrustedScoringSuccess` 改为 `if False` → `test_prewrite_validate_rejects_non_aggregate` FAILED
- **M2** raw hash：将 `if raw_response_hash != primary_attempt.raw_response_hash` 改为 `if False` → `test_prewrite_validate_rejects_raw_response_hash_mutation` FAILED
- **M3** raw reparse：将 `if reparsed_candidate != candidate` 改为 `if False` → `test_prewrite_validate_rejects_raw_reparse_mutation` FAILED
- **M4** candidate/result binding：将 business-field binding check 改为 `if False` → `test_prewrite_validate_rejects_candidate_result_binding_mutation` FAILED
- **M5** runtime authority/context：将 `if primary_attempt.provider != context.scoring_provider` 改为 `if False` → `test_prewrite_validate_rejects_runtime_authority_rotation` FAILED
- **M6** ProviderCall request binding：将 `if scoring_call_request.request_hash != identity.request_hash` 改为 `if False` → `test_prewrite_validate_rejects_provider_call_request_binding_mutation` FAILED
- **M7** Artifact content/hash binding：将 runtime `_verified_artifact` 中 `hashlib.sha256(body).hexdigest() != record.content_hash` 改为 `if False` → `test_load_scoring_rejects_corrupted_structured_artifact` FAILED
- **M8** prewrite-before-write ordering：将 `if tmp_path.exists()` 改为 `if False` → `test_commit_raises_when_temporary_file_already_exists` FAILED
- **M9** bare-result compatibility re-entry：将 `run_primary_trusted_scoring` 中 `type(attempt) is not PrimaryScoringAttempt` 改为 `if False` → `test_scoring_stage_rejects_bare_score_result_reentry` FAILED
- **M10** stage-completion ordering：将 `atomic_register_scoring_success` 中 video `pipeline_status = :expected_status` 条件去掉 → `test_atomic_register_fails_on_wrong_pipeline_status` FAILED（commit 成功而非 fail-closed）

### 10 Mandatory Gates

| # | Gate | 结果 |
|---|---|---|
| 1 | `uv lock --check --offline` | PASS |
| 2 | `uv sync --locked --offline` | PASS |
| 3 | `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` | `21 passed` |
| 4 | `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` | `41 passed` |
| 5 | `uv run --offline pytest -x -q` | `1236 passed, 1 warning` |
| 6 | `uv run --offline mypy src` | PASS |
| 7 | `uv run --offline ruff check .` | PASS |
| 8 | `uv build --offline` | PASS |
| 9 | `bash scripts/security_scan.sh` | `status=clean` |
| 10 | `git diff --check` | PASS |

### Scope Verification

- 修改文件：`src/youtube_intel/scoring.py`、`src/youtube_intel/runtime.py`、`src/youtube_intel/state.py`、`tests/unit/test_task016c_phase_g.py`、`tests/integration/test_runtime_composition.py`、`tests/integration/test_task015_p1_fix.py`、`handoffs/TASK-016C.md`
- 未修改 `providers/ollama.py`、`domain.py`、TASK-016B Language Validator、Cloud、Router、Weekly production、DB migration、依赖、`uv.lock`
- 未 rebase / squash / amend / merge / push / tag
- 仅一笔 Phase G implementation commit

### Diff Review

- `scoring.py`：新增 Phase G committer/plan、enriched aggregate、sealed serializer、prewrite validator、ordered file writer
- `runtime.py`：trusted scoring-stage cutover、committer factory、provenance acceptance for Phase G artifacts
- `state.py`：原子 `atomic_register_scoring_success` transaction
- `tests/unit/test_task016c_phase_g.py`：21 项新测试覆盖 trust/persistence/cutover/mutation
- 集成测试适配：mock provider 使用 `primary_attempt` API 并提供 `_QualityJudgeProvider`

### Reuse Decision

- `SQLiteStateRepository` 与 `_immediate_transaction`：`DIRECT`（`state.py` 已有）
- `ProviderCallRequest` / `ArtifactWrite` / `StageCompletionResult`：`DIRECT`（`state.py` 已有）
- `TrustedScoringFinalizer` / `QualityProvenanceAuthority` / `TrustedScoringContext`：`DIRECT`（`quality.py` 已有）
- `parse_scoring_candidate` / `build_scoring_candidate_hash`：`DIRECT`（`providers/ollama.py` / `quality.py` 已有）
- 未新增依赖

### 失败、跳过与风险

- 已解决：
  - 继续前 Recovery Audit 确认工作区处于 Phase G 部分实现、集成测试 RED 状态
  - 修复 mock provider API 不兼容（`primary_attempt` + `_QualityJudgeProvider`）
  - 修复 runtime provenance 校验未适配 Phase G artifacts 的问题
  - 调整 M4/M6 测试以匹配实际 fail-closed guard 顺序（business binding 先于 structured bytes；ProviderCall request binding 通过替换 committer context 触发）
  - 新增 M7（artifact hash binding）、M9（bare-result re-entry）、M10（stage-completion ordering）显式 RED 测试与 mutation 证据
- 跳过：真实 Ollama/network/cloud 执行（授权禁止）
- 剩余风险：
  - 跨 filesystem/SQLite 崩溃恢复、cache verification/hardening、retry/repair 仍属于 Phase H/I
  - G 仅覆盖 normal-success path，PENDING/FAILED/partial/legacy conflict 均 fail-closed 并留给 H/I

### 实现者结论

- 建议状态：`READY FOR PHASE G INDEPENDENT REVIEW`
- 复现/验证说明：
  ```bash
  uv lock --check --offline
  uv sync --locked --offline
  uv run --offline pytest tests/unit/test_task016c_phase_g.py -q
  uv run --offline pytest tests/unit/test_task016c_phase_f.py -q
  uv run --offline pytest -x -q
  uv run --offline mypy src
  uv run --offline ruff check .
  uv build --offline
  bash scripts/security_scan.sh
  git diff --check
  ```

## Phase G Correction Round 1

- Status: `SUPERSEDED BY ROUND 2`
- Authority: `agent-prompts/TASK-016C-PHASE-G-IMPLEMENTATION-AUTHORIZATION.md`、
  `docs/TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md`、
  `docs/TASK-016C-PHASE-G-HANDOFF-CHECKLIST.md`
- Correction baseline: `ef89b1e` (Phase G implementation commit)
- Correction commit: `b4497cf`
- Handoff commit: `6900b76`
- Role: Implementer (continuation/recovery)

### Correction Scope

本次 correction 仅关闭 Phase G 独立审查前发现的三个 P1 阻塞，不进入 Phase H/I，不重新设计/回滚/扩大范围：

| P1 | 位置 | 修复内容 |
|---|---|---|
| P1-1 Atomic No-Clobber Promote | `src/youtube_intel/scoring.py` `TrustedScoringPersistenceCommitter._write_atomic_file()` | 将 `exists()+os.rename()` 改为 `os.link(tmp, final)+os.unlink(tmp)` 原子 no-replace promote；保留 tmp write、fsync、hash/length verify、dir fsync、final reopen verify |
| P1-2 Strict Same-Plan Idempotency | `src/youtube_intel/scoring.py` `TrustedScoringPersistenceCommitter._check_committed_graph()` / `commit()` | 同一 plan 重复 commit 时，先验证完整 committed graph：raw/structured final 文件存在且 hash/length/path 匹配；Artifact rows、两个 SUCCEEDED ProviderCall、video SCORED、job SUCCEEDED 全部一致才返回已有结果；否则 fail-closed（不修复、不 recall provider） |
| P1-3 Close `atomic_register` Bypass | `src/youtube_intel/state.py` `_atomic_register_scoring_success()` / `ScoringRegistrationCapability` | 注册入口改为私有 `_atomic_register_scoring_success()`，仅接受内部 sentinel-mint 的 `ScoringRegistrationCapability`；普通 `ArtifactWrite`/`ProviderCall`/Mapping/JSON/object 全部拒绝；DB boundary 再防御性验证 final files 存在且 hash 匹配 |

### RED-first 补充测试

在 `tests/unit/test_task016c_phase_g.py` 新增/修正以下 RED→GREEN 测试：

- **R1** no-clobber race：`test_r1_promote_does_not_overwrite_existing_final`、`test_r1_promote_uses_atomic_link_not_rename`
- **R2** strict same-plan idempotency：`test_r2_same_plan_after_commit_is_idempotent`、`test_r2_same_plan_with_raw_file_corrupt_rejects`、`test_r2_same_plan_with_partial_db_graph_rejects`、`test_r2_idempotent_retry_does_not_rewrite_files`
- **R3** direct registrar bypass：`test_r3_direct_repository_call_with_ordinary_dtos_rejects`、`test_r3_ordinary_capability_substitute_rejects`
- **R4** SQLite-after-promote failure semantics：`test_r4_sqlite_failure_leaves_promoted_finals`
- **R5** filesystem fault injection：`test_r5_temp_write_failure_no_sqlite_registration`、`test_r5_sqlite_transaction_rollback_no_partial_graph`
- **M14** final-file verification：`test_m14_registration_rejects_missing_final_files`

### Mutation Matrix（M1–M15）

使用 `run_mutation_matrix.py` 临时修改并恢复，每项至少导致一个测试失败：

| Mutation | 目标 | 结果 |
|---|---|---|
| M1 | `prewrite_validate` exact success guard → `if False` | KILLED |
| M2 | raw hash check → `if False` | KILLED |
| M3 | raw reparse check → `if False` | KILLED |
| M4 | candidate/result binding → `if False` | KILLED |
| M5 | runtime authority/context check → `if False` | KILLED |
| M6 | ProviderCall request binding → `if False` | KILLED |
| M7 | runtime artifact content/hash binding → `if False` | KILLED |
| M8 | stale-tmp O_EXCL guard 移除 | KILLED |
| M9 | `run_primary_trusted_scoring` PrimaryScoringAttempt exact-type guard → `if False` | KILLED |
| M10 | `_atomic_register_scoring_success` 跳过 job finish | KILLED |
| M11 | `_write_atomic_file` 将 `os.link` 改回 `os.rename` | KILLED |
| M12 | `commit()` 删除 complete-graph idempotency verification | KILLED |
| M13 | `_atomic_register_scoring_success` 删除 `ScoringRegistrationCapability` type guard | KILLED |
| M14 | `_atomic_register_scoring_success` 删除 final-file hash verification | KILLED |
| M15 | `commit()` 将 DB registration 提前到 promoted finals 之前 | KILLED |

Mutation 脚本本身未提交；生产代码在所有 mutation 恢复后 GREEN。

### Mandatory Gates

| # | Gate | 结果 |
|---|---|---|
| 1 | `uv lock --check --offline` | PASS |
| 2 | `uv sync --locked --offline --dry-run` | PASS |
| 3 | `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` | `33 passed` |
| 4 | `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` | `41 passed` |
| 5 | Phase A–E trust + TASK-016B regression | `417 passed, 1 warning` |
| 6 | `uv run --offline pytest -x -q` | `1248 passed, 1 warning` |
| 7 | `uv run --offline mypy src` | PASS |
| 8 | `uv run --offline ruff check .` | PASS |
| 9 | `uv build --offline` | PASS |
| 10 | `bash scripts/security_scan.sh` | `status=clean` |
| 11 | `git diff --check` | PASS |

### Scope Verification

- 修改文件：`src/youtube_intel/scoring.py`、`src/youtube_intel/state.py`、`tests/unit/test_task016c_phase_g.py`、`handoffs/TASK-016C.md`
- 未修改 `providers/ollama.py`、`domain.py`、TASK-016B Language Validator、Cloud、Router、Weekly production、DB migration、依赖、`uv.lock`
- 未 rebase / squash / amend（基线 commit 之外的新 correction commit）/ merge / push / tag
- 无真实 Ollama/network/cloud 调用

### 实现者结论

- 建议状态：`READY FOR PHASE G CORRECTION INDEPENDENT REVIEW`
- 下一步：由独立 reviewer 复核本 correction commit、RED/GREEN/mutation 证据、gates 与 handoff 后决定是否验收；不进入 Phase H。

## Phase G Correction Round 2

- Status: `SUPERSEDED BY ROUND 3`
- Authority: `agent-prompts/TASK-016C-PHASE-G-IMPLEMENTATION-AUTHORIZATION.md`、
  `docs/TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md`、
  `docs/TASK-016C-PHASE-G-HANDOFF-CHECKLIST.md`
- Correction baseline: `ef89b1e` (Phase G implementation commit)
- Round 1 correction commit: `b4497cf`
- Round 1 handoff commit: `6900b76`
- Round 2 correction commit: `b8005d1` (HEAD)
- Role: Implementer (continuation/recovery)

### Correction Scope

本次 correction 关闭 Round 1 Independent Review 的 REQUEST CHANGES，不进入 Phase H/I，不重新设计/回滚/扩大范围，不修改 Phase F/D/E：

| P1 | 位置 | 修复内容 |
|---|---|---|
| P1-1 Complete Graph Idempotency | `src/youtube_intel/scoring.py` `TrustedScoringPersistenceCommitter._check_committed_graph()` | 完整比较 committed graph：Filesystem（absolute controlled path、relative path、bytes、sha256、length）、Artifact rows（artifact_id/kind/path/relative_path/content_hash/size via length/provider/model/producer_version/retention_class/expires_at）、ProviderCall rows（provider/model/request_hash/operation/status/response_artifact_id/prompt_version/schema_version）、Video（score/should_summarize）、Job（job_id binding/stage/status/provenance）。任何 mismatch 均 fail-closed（不修复、不 recall provider） |
| Plan Expected Metadata | `ValidatedScoringWritePlan` | 新增 `raw_envelope_length` 与 `structured_length`，由 PREWRITE validated capability 携带，作为 single source of truth |
| P1-2 Registration Capability Authority | `src/youtube_intel/state.py` / `src/youtube_intel/scoring.py` | 关闭 `state.py` 的 `_mint_scoring_registration_capability()`；mint 能力完全内化为 `TrustedScoringPersistenceCommitter._mint_registration_capability()`；capability 新增 `_provenance_token`（SHA256 binding of job/owner/video/pipeline_version/artifact_ids/request_hashes/file_hashes）；registrar 重新计算并验证 token；普通 caller 无法 import mint、无法构造合法 capability、无法 copy/pickle/修改字段 |

### RED-first 补充测试

在 `tests/unit/test_task016c_phase_g.py` 新增/修正以下 RED→GREEN 测试：

- **R2** complete graph idempotency：
  - `test_r2_artifact_artifact_id_change_rejects`
  - `test_r2_artifact_relative_path_change_rejects`
  - `test_r2_artifact_kind_change_rejects`
  - `test_r2_artifact_provider_metadata_change_rejects`
  - `test_r2_provider_call_request_metadata_change_rejects`
  - `test_r2_video_should_summarize_change_rejects`
  - `test_r2_job_binding_change_rejects`
- **R3** registration capability authority：
  - `test_r3_import_mint_function_fails`
  - `test_r3_direct_sentinel_construction_with_wrong_token_rejects`
  - `test_r3_copy_capability_rejects`
  - `test_r3_pickle_capability_rejects`
  - `test_r3_modify_capability_field_rejects`
  - `test_r3_legal_committer_path_succeeds`
- **M15** filesystem-before-SQLite ordering：`test_m15_registration_before_final_verify_rejected`
- **R5** filesystem fault injection（补充）：
  - `test_r5_fsync_failure_no_sqlite_registration`
  - `test_r5_promote_failure_no_sqlite_registration`
  - `test_r5_dir_fsync_failure_no_sqlite_registration`
  - `test_r5_final_reopen_verify_failure_no_sqlite_registration`

### Mutation Matrix（M1–M15）

使用 `run_mutation_matrix.py` 临时修改并恢复，每项至少导致一个测试失败：

| Mutation | 目标 | 结果 |
|---|---|---|
| M1 | `prewrite_validate` exact success guard → `if False` | KILLED |
| M2 | raw hash check → `if False` | KILLED |
| M3 | raw reparse check → `if False` | KILLED |
| M4 | candidate/result binding → `if False` | KILLED |
| M5 | runtime authority/context check → `if False` | KILLED |
| M6 | ProviderCall request binding → `if False` | KILLED |
| M7 | runtime artifact content/hash binding → `if False` | KILLED |
| M8 | stale-tmp O_EXCL guard 移除 | KILLED |
| M9 | `run_primary_trusted_scoring` PrimaryScoringAttempt exact-type guard → `if False` | KILLED |
| M10 | `_atomic_register_scoring_success` 跳过 job finish | KILLED |
| M11 | `_write_atomic_file` 将 `os.link` 改回 `os.rename` | KILLED |
| M12 | `commit()` 删除 complete-graph idempotency verification | KILLED |
| M13 | `_atomic_register_scoring_success` 删除 capability + provenance token guard | KILLED |
| M14 | `_atomic_register_scoring_success` 删除 final-file hash verification | KILLED |
| M15 | `commit()` 将 DB registration 提前到 promoted finals 之前 | KILLED |

Mutation 脚本本身未提交；生产代码在所有 mutation 恢复后 GREEN。

### Mandatory Gates

| # | Gate | 结果 |
|---|---|---|
| 1 | `uv lock --check --offline` | PASS |
| 2 | `uv sync --locked --offline --dry-run` | PASS |
| 3 | `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` | `51 passed` |
| 4 | `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` | `41 passed` |
| 5 | Phase A–E trust + TASK-016B regression | `417 passed, 1 warning` |
| 6 | `uv run --offline pytest -x -q` | `1266 passed, 1 warning` |
| 7 | `uv run --offline mypy src` | PASS |
| 8 | `uv run --offline ruff check .` | PASS |
| 9 | `uv build --offline` | PASS |
| 10 | `bash scripts/security_scan.sh` | `status=clean` |
| 11 | `git diff --check` | PASS |

### Scope Verification

- 修改文件：`src/youtube_intel/scoring.py`、`src/youtube_intel/state.py`、`tests/unit/test_task016c_phase_g.py`、`handoffs/TASK-016C.md`
- 未修改 `providers/ollama.py`、`domain.py`、TASK-016B Language Validator、Cloud、Router、Weekly production、DB migration、依赖、`uv.lock`
- 未 rebase / squash / amend（基线 commit `ef89b1e` 之外的新 correction commit）/ merge / push / tag
- 无真实 Ollama/network/cloud/credential 调用

### 实现者结论

- 建议状态：`READY FOR PHASE G CORRECTION ROUND 2 INDEPENDENT REVIEW`
- 下一步：由独立 reviewer 复核本 correction commit、RED/GREEN/mutation 证据、gates 与 handoff 后决定是否验收；不进入 Phase H。

## Phase G Correction Round 3

- Status: `READY FOR PHASE G CORRECTION ROUND 3 INDEPENDENT REVIEW`
- Authority: `agent-prompts/TASK-016C-PHASE-G-IMPLEMENTATION-AUTHORIZATION.md`、
  `docs/TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md`、
  `docs/TASK-016C-PHASE-G-HANDOFF-CHECKLIST.md`
- Correction baseline: `ef89b1e` (Phase G implementation commit)
- Round 1 correction commit: `b4497cf`
- Round 1 handoff commit: `6900b76`
- Round 2 correction commit: `b8005d1`
- Round 2 handoff commit: `52c0bcf`
- Round 3 correction commit: `1780d9a` (HEAD)
- Role: Implementer (continuation/recovery)

### Correction Scope

本次 correction 关闭 Round 2 Independent Review 的 REQUEST CHANGES，不进入 Phase H/I，不重新设计/回滚/扩大范围，不修改 Phase F/D/E：

| P1/P2 | 位置 | 修复内容 |
|---|---|---|
| P1-1 Registration Capability Authority | `src/youtube_intel/scoring.py` `_RegistrationAuthority` / `TrustedScoringPersistenceCommitter`；`src/youtube_intel/state.py` `ScoringRegistrationCapability` / `_atomic_register_scoring_success()`；`src/youtube_intel/runtime.py` `RuntimeOperations` | 引入 runtime-scoped 的 `_RegistrationAuthority` 对象作为不可推导的 authority proof；Runtime 创建唯一实例并同时注入 repository 与 committer；capability 必须携带该实例；registrar 通过对象 identity 验证来源。移除 deterministic SHA256 provenance token，避免被重新计算伪造。state.py 不再暴露任何 mint seam |
| P1-2 Exact relative_path Verification | `src/youtube_intel/scoring.py` `TrustedScoringPersistenceCommitter._verify_artifact_record()` | 先比较 `record.relative_path == expected.relative_path` 字符串，再比较 resolved absolute path；禁止仅依赖 `Path.resolve()`；路径归一化后相同但字符串不同会被拒绝 |
| P2 Failure Injection Completeness | `tests/unit/test_task016c_phase_g.py` `_assert_no_scoring_success()` | 每次 filesystem fault 后统一断言：raw/structured Artifact 不存在、scoring/judge ProviderCall 未 SUCCEEDED、video 未 SCORED、job 未 SUCCEEDED |
| P2 Mutation-as-Tests | `tests/unit/test_task016c_phase_g.py` | 关键 mutation 保护已转为 committed pytest tests：`test_r1_promote_does_not_overwrite_existing_final`（no-replace overwrite）、`test_r2_same_plan_after_commit_is_idempotent`（complete graph idempotency）、`test_direct_forged_capability_with_correct_fields_is_rejected` + `test_r3_ordinary_capability_substitute_rejects`（capability bypass）、`test_m14_registration_rejects_missing_final_files`（final file verification）、`test_m15_registration_before_final_verify_rejected`（DB registration ordering） |
| Worktree | `.gitignore` / `run_mutation_matrix.py` | 删除未跟踪的 `run_mutation_matrix.py`；将 `.workbuddy/` 加入 `.gitignore`（按策略不删除该目录） |

### RED-first 补充测试

在 `tests/unit/test_task016c_phase_g.py` 新增/修正以下 RED→GREEN 测试：

- **P1-1 authority forge：** `test_direct_forged_capability_with_correct_fields_is_rejected`
- **P1-2 exact relative_path：** `test_idempotency_rejects_relative_path_normalization_difference`
- **P2 failure injection：** 通过 `_assert_no_scoring_success()` 统一增强 `test_r5_temp_write_failure_no_sqlite_registration`、`test_r5_fsync_failure_no_sqlite_registration`、`test_r5_promote_failure_no_sqlite_registration`、`test_r5_dir_fsync_failure_no_sqlite_registration`、`test_r5_final_reopen_verify_failure_no_sqlite_registration`、`test_r5_sqlite_transaction_rollback_no_partial_graph`

### Mandatory Gates

| # | Gate | 结果 |
|---|---|---|
| 1 | `uv lock --check --offline` | PASS |
| 2 | `uv sync --locked --offline --dry-run` | PASS |
| 3 | `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` | `52 passed` |
| 4 | `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` | `41 passed` |
| 5 | Phase A–E trust + TASK-016B regression | `417 passed, 1 warning` |
| 6 | `uv run --offline pytest -x -q` | `1267 passed, 1 warning` |
| 7 | `uv run --offline mypy src` | PASS |
| 8 | `uv run --offline ruff check .` | PASS |
| 9 | `uv build --offline` | PASS |
| 10 | `bash scripts/security_scan.sh` | `status=clean` |
| 11 | `git diff --check` | PASS |

### Scope Verification

- 修改文件：`.gitignore`、`src/youtube_intel/scoring.py`、`src/youtube_intel/state.py`、`src/youtube_intel/runtime.py`、`tests/unit/test_task016c_phase_g.py`、`handoffs/TASK-016C.md`
- 未修改 `providers/ollama.py`、`domain.py`、TASK-016B Language Validator、Cloud、Router、Weekly production、DB migration、依赖、`uv.lock`
- 未 rebase / squash / amend（基线 commit 之外的新 correction commit）/ merge / push / tag
- 无真实 Ollama/network/cloud 调用

### 实现者结论

- 建议状态：`READY FOR PHASE G CORRECTION ROUND 3 INDEPENDENT REVIEW`
- 下一步：由独立 reviewer 复核本 correction commit、RED/GREEN 证据、gates 与 handoff 后决定是否验收；不进入 Phase H。

## Phase G Correction Round 4

- Status: `READY FOR PHASE G CORRECTION ROUND 4 INDEPENDENT REVIEW`
- Authority: `agent-prompts/TASK-016C-PHASE-G-IMPLEMENTATION-AUTHORIZATION.md`、
  `docs/TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md`、
  `docs/TASK-016C-PHASE-G-HANDOFF-CHECKLIST.md`
- Correction baseline: `ef89b1e` (Phase G implementation commit)
- Round 1 correction commit: `b4497cf`
- Round 1 handoff commit: `6900b76`
- Round 2 correction commit: `b8005d1`
- Round 2 handoff commit: `52c0bcf`
- Round 3 correction commit: `1780d9a`
- Round 3 handoff commit: `c1971da`
- Role: Implementer

### Correction Scope

本次 correction 关闭 Round 3 Independent Review 的唯一 P1「Registration authority remains caller-configurable」，不进入 Phase H/I，不重新设计/回滚/扩大范围，不修改 Phase F/D/E：

| P1/P2 | 位置 | 修复内容 |
|---|---|---|
| P1 Authority Injection Trust Boundary | `src/youtube_intel/runtime.py` `bootstrap_runtime()` / `RuntimeOperations.__init__`；`src/youtube_intel/state.py` `SQLiteStateRepository.__init__` / `ScoringRegistrationCapability` | 从 `bootstrap_runtime()` 与 `SQLiteStateRepository.__init__` 移除 `registration_authority` 参数；authority 改由 `SQLiteStateRepository` 在构造时内部创建。`RuntimeOperations` 只能从已组合的 repository 读取该实例并注入 committer。authority 不可外部传入、不可替换、不可复制、不可序列化。registrar 仍通过对象 identity 验证 capability 来源 |

### RED-first 补充测试

在 `tests/unit/test_task016c_phase_g.py` 新增 RED→GREEN 测试：

- **P1 external repository authority bypass：** `test_external_repository_authority_cannot_create_registration_success`
  - caller 直接创建 `SQLiteStateRepository`
  - caller 创建 forged `_RegistrationAuthority`
  - caller 构造 self-consistent `ScoringRegistrationCapability`（含正确 DTO、文件、hash）
  - 调用 `_atomic_register_scoring_success()`
  - 结果：`IntegrityConflict("registration authority proof mismatch")`，FAIL CLOSED

### Mandatory Gates

| # | Gate | 结果 |
|---|---|---|
| 1 | `uv lock --check --offline` | PASS |
| 2 | `uv sync --locked --offline` | PASS |
| 3 | `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` | `53 passed` |
| 4 | `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` | `41 passed` |
| 5 | Phase A–E regression | `316 passed, 1 warning` |
| 6 | `uv run --offline pytest -x -q` | `1268 passed, 1 warning` |
| 7 | `uv run --offline mypy src` | PASS |
| 8 | `uv run --offline ruff check .` | PASS |
| 9 | `uv build` | PASS |
| 10 | `bash scripts/security_scan.sh` | `status=clean` |
| 11 | `git diff --check` | PASS |

### Scope Verification

- 修改文件：`src/youtube_intel/runtime.py`、`src/youtube_intel/state.py`、`tests/unit/test_task016c_phase_g.py`、`handoffs/TASK-016C.md`
- 未修改 `src/youtube_intel/scoring.py`（authority 验证逻辑不变，仅 authority 来源从 caller-configurable 改为 repository 内部创建）、`providers/ollama.py`、`domain.py`、TASK-016B Language Validator、Cloud、Router、Weekly production、DB migration、依赖、`uv.lock`
- 未 rebase / squash / amend（基线 commit 之外的新 correction commit）/ merge / push / tag
- 无真实 Ollama/network/cloud 调用

### 实现者结论

- 建议状态：`READY FOR PHASE G CORRECTION ROUND 4 INDEPENDENT REVIEW`
- 下一步：由独立 reviewer 复核本 correction commit、RED/GREEN 证据、gates 与 handoff 后决定是否验收；不进入 Phase H。

## Phase G Correction Round 5

- Status: `READY FOR PHASE G CORRECTION ROUND 5 INDEPENDENT REVIEW`
- Authority: `agent-prompts/TASK-016C-PHASE-G-IMPLEMENTATION-AUTHORIZATION.md`、
  `docs/TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md`、
  `docs/TASK-016C-PHASE-G-HANDOFF-CHECKLIST.md`
- Correction baseline: `ef89b1e` (Phase G implementation commit)
- Round 1 correction commit: `b4497cf`
- Round 1 handoff commit: `6900b76`
- Round 2 correction commit: `b8005d1`
- Round 2 handoff commit: `52c0bcf`
- Round 3 correction commit: `1780d9a`
- Round 3 handoff commit: `c1971da`
- Round 4 correction commit: `980497d`
- Round 4 handoff commit: `dda8040`
- Role: Implementer

### Correction Scope

本次 correction 关闭 Round 4 Independent Review 的唯一 P1「SQLiteStateRepository remains authority-minting root」，不进入 Phase H/I，不重新设计/回滚/扩大范围，不修改 Phase F/D/E：

| P1/P2 | 位置 | 修复内容 |
|---|---|---|
| P1 Authority Minting Root | `src/youtube_intel/scoring.py` `_RegistrationAuthority`；`src/youtube_intel/runtime.py` `RuntimeOperations.__init__`；`src/youtube_intel/state.py` `SQLiteStateRepository.__init__` / `_bind_registration_authority()` / `_atomic_register_scoring_success()` | 从 `SQLiteStateRepository.__init__` 移除 authority 创建逻辑；`_RegistrationAuthority` 增加 runtime-issued 标记；`RuntimeOperations` 是唯一创建并标记 authority 的主体，然后通过私有 `_bind_registration_authority()` 绑定到 repository，同时注入 committer。直接构造的 `SQLiteStateRepository` 没有 authority，无法产生 accepted registrar capability |

### RED-first 补充测试

在 `tests/unit/test_task016c_phase_g.py` 新增/修正 RED→GREEN 测试：

- **P1 external repository has no authority：** `test_external_repository_authority_cannot_create_registration_success`（Round 4 测试断言更新）
  - caller 直接创建 `SQLiteStateRepository`
  - caller 创建 forged `_RegistrationAuthority`
  - caller 构造 self-consistent `ScoringRegistrationCapability`
  - 调用 `_atomic_register_scoring_success()`
  - 结果：`IntegrityConflict("repository has no runtime-bound registration authority")`，FAIL CLOSED
- **P1 external repository cannot authorize with its own authority：** `test_external_repository_cannot_authorize_with_own_authority`
  - caller 直接创建 `SQLiteStateRepository`
  - caller 创建自己的 `_RegistrationAuthority` 并尝试通过 `_bind_registration_authority()` 绑定 → 失败（非 runtime-issued）
  - caller 绕过 bind 检查直接将自己的 authority 附加到 repository，构造 self-consistent capability（正确 DTO、文件、hash）
  - 调用 `_atomic_register_scoring_success()`
  - 结果：`IntegrityConflict("registration authority was not issued by the runtime")`，FAIL CLOSED

### Mandatory Gates

| # | Gate | 结果 |
|---|---|---|
| 1 | `uv lock --check --offline` | PASS |
| 2 | `uv sync --locked --offline` | PASS |
| 3 | `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` | `54 passed` |
| 4 | `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` | `41 passed` |
| 5 | Phase A–E regression | `316 passed, 1 warning` |
| 6 | `uv run --offline pytest -x -q` | `1269 passed, 1 warning` |
| 7 | `uv run --offline mypy src` | PASS |
| 8 | `uv run --offline ruff check .` | PASS |
| 9 | `uv build` | PASS |
| 10 | `bash scripts/security_scan.sh` | `status=clean` |
| 11 | `git diff --check` | PASS |

### Scope Verification

- 修改文件：`src/youtube_intel/scoring.py`、`src/youtube_intel/runtime.py`、`src/youtube_intel/state.py`、`tests/unit/test_task016c_phase_g.py`、`handoffs/TASK-016C.md`
- 未修改 `providers/ollama.py`、`domain.py`、TASK-016B Language Validator、Cloud、Router、Weekly production、DB migration、依赖、`uv.lock`
- 未 rebase / squash / amend（基线 commit 之外的新 correction commit）/ merge / push / tag
- 无真实 Ollama/network/cloud 调用

### 实现者结论

- 建议状态：`READY FOR PHASE G CORRECTION ROUND 5 INDEPENDENT REVIEW`
- 下一步：由独立 reviewer 复核本 correction commit、RED/GREEN 证据、gates 与 handoff 后决定是否验收；不进入 Phase H。

## Phase G Correction Round 6

- Status: `READY FOR PHASE G CORRECTION ROUND 6 INDEPENDENT REVIEW`
- Authority: `agent-prompts/TASK-016C-PHASE-G-IMPLEMENTATION-AUTHORIZATION.md`、
  `docs/TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md`、
  `docs/TASK-016C-PHASE-G-HANDOFF-CHECKLIST.md`
- Correction baseline: `ef89b1e` (Phase G implementation commit)
- Round 1 correction commit: `b4497cf`
- Round 1 handoff commit: `6900b76`
- Round 2 correction commit: `b8005d1`
- Round 2 handoff commit: `52c0bcf`
- Round 3 correction commit: `1780d9a`
- Round 3 handoff commit: `c1971da`
- Round 4 correction commit: `980497d`
- Round 4 handoff commit: `dda8040`
- Round 5 correction commit: `0649447`
- Round 5 handoff commit: `b425dd4`
- Role: Implementer

### Correction Scope

本次 correction 关闭 Round 5 Independent Review 的唯一 P1「Registration authority issuance boundary is still forgeable」，不进入 Phase H/I，不重新设计/回滚/扩大范围，不修改 Phase F/D/E：

| P1/P2 | 位置 | 修复内容 |
|---|---|---|
| P1 Authority Issuance Boundary | `src/youtube_intel/_phase_g_trust.py`（新建）；`src/youtube_intel/scoring.py` `_RegistrationAuthority`；`src/youtube_intel/runtime.py` `RuntimeOperations.__init__`；`src/youtube_intel/state.py` `_bind_registration_authority()` / `_atomic_register_scoring_success()` | 移除 `_mark_runtime_issued()` 与 `_runtime_issued` boolean 等 mutable escalation API；引入 `_RuntimeIssuanceCapability` 作为只有 `RuntimeOperations` composition 能 mint 的 runtime-only capability；`_RegistrationAuthority` 构造函数必须接收该 capability，否则 raise TypeError；`RuntimeOperations` 在 `__init__` 内通过 `object.__new__` 创建 capability 与 authority 并绑定 repository；registrar 通过 capability 的 exact-type 与对象身份双重校验拒绝任何 caller-forged authority |

### RED-first 补充测试

在 `tests/unit/test_task016c_phase_g.py` 新增/修正 RED→GREEN 测试：

- **P1 direct forged capability：** `test_direct_forged_capability_with_correct_fields_is_rejected`（Round 3 测试更新）
  - caller 使用任意 object 作为 `authority_proof`
  - 调用 `_atomic_register_scoring_success()`
  - 结果：`IntegrityConflict("registration authority proof is not a _RegistrationAuthority")`，FAIL CLOSED
- **P1 external repository has no authority：** `test_external_repository_authority_cannot_create_registration_success`（Round 4 测试更新）
  - caller 直接创建 `SQLiteStateRepository`
  - caller 使用任意 object 作为 `authority_proof`
  - 结果：`IntegrityConflict("repository has no runtime-bound registration authority")`，FAIL CLOSED
- **P1 external authority cannot be issued：** `test_external_authority_cannot_be_issued`
  - `_RegistrationAuthority()` → `TypeError`
  - `_RegistrationAuthority(object())` → `TypeError`
  - `object.__new__(_RegistrationAuthority)` 无 valid issuance capability
- **P1 external repository cannot become trusted root：** `test_external_repository_cannot_become_trusted_root`
  - 直接构造的 repository `_registration_authority is None`
  - caller 绕过 `__init__` 得到的 authority 无法通过 `_bind_registration_authority()`
- **P1 full attack chain：** `test_external_mark_bind_capability_register_attack_fails`
  - external repo = `SQLiteStateRepository(db)`
  - 无 `_mark_runtime_issued` API 可供调用
  - `_RegistrationAuthority()` 构造失败
  - `object.__new__(_RegistrationAuthority)` 得到的 authority 绑定失败
  - 构造 self-consistent capability（正确 DTO、文件、hash）调用 register → FAIL CLOSED
  - 即使强行把 forged authority 附加到 repository，register 仍因缺少 runtime issuance capability 而 FAIL CLOSED
- **P1 positive control：** `test_runtime_owned_registration_still_succeeds`
  - 正常 `RuntimeOperations` 路径完成 commit
  - 结果：`StageCompletionResult`，job `SUCCEEDED`，video `SCORED`

### Mutation Evidence

新增 regression tests 同时充当 mutation kill proof：

| 删除的保护 | 会失败的测试 |
|---|---|
| 删除 runtime issuance capability 类型校验（`_RegistrationAuthority.__init__` 或 registrar 中） | `test_external_authority_cannot_be_issued`、`test_external_mark_bind_capability_register_attack_fails` |
| 删除 repository binding authority 校验（`_bind_registration_authority` 中） | `test_external_repository_cannot_become_trusted_root`、`test_external_mark_bind_capability_register_attack_fails` |
| 恢复 caller-controlled authority injection | `test_external_repository_authority_cannot_create_registration_success`、`test_external_mark_bind_capability_register_attack_fails` |

### Mandatory Gates

| # | Gate | 结果 |
|---|---|---|
| 1 | `uv lock --check --offline` | PASS |
| 2 | `uv sync --locked --offline` | PASS |
| 3 | `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` | `58 passed` |
| 4 | `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` | `41 passed` |
| 5 | Phase A–E regression | `316 passed, 1 warning` |
| 6 | `uv run --offline pytest -x -q` | `1273 passed, 1 warning` |
| 7 | `uv run --offline mypy src` | PASS |
| 8 | `uv run --offline ruff check .` | PASS |
| 9 | `uv build --offline` | PASS |
| 10 | `bash scripts/security_scan.sh` | `status=clean` |
| 11 | `git diff --check` | PASS |

### Scope Verification

- 修改文件：`src/youtube_intel/_phase_g_trust.py`（新建）、`src/youtube_intel/scoring.py`、`src/youtube_intel/runtime.py`、`src/youtube_intel/state.py`、`tests/unit/test_task016c_phase_g.py`、`handoffs/TASK-016C.md`
- 未修改 `providers/ollama.py`、`domain.py`、TASK-016B Language Validator、Cloud、Router、Weekly production、DB migration、依赖、`uv.lock`
- 未 rebase / squash / amend（基线 commit 之外的新 correction commit）/ merge / push / tag
- 无真实 Ollama/network/cloud 调用

### 实现者结论

- 建议状态：`READY FOR PHASE G CORRECTION ROUND 6 INDEPENDENT REVIEW`
- 下一步：由独立 reviewer 复核本 correction commit、RED/GREEN 证据、mutation evidence、gates 与 handoff 后决定是否验收；不进入 Phase H。

## Phase G Correction Round 7

- Status: `READY FOR PHASE G CORRECTION ROUND 7 INDEPENDENT REVIEW`
- Authority: `agent-prompts/TASK-016C-PHASE-G-IMPLEMENTATION-AUTHORIZATION.md`、
  `docs/TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md`、
  `docs/TASK-016C-PHASE-G-HANDOFF-CHECKLIST.md`
- Correction baseline: `ef89b1e` (Phase G implementation commit)
- Round 1 correction commit: `b4497cf`
- Round 1 handoff commit: `6900b76`
- Round 2 correction commit: `b8005d1`
- Round 2 handoff commit: `52c0bcf`
- Round 3 correction commit: `1780d9a`
- Round 3 handoff commit: `c1971da`
- Round 4 correction commit: `980497d`
- Round 4 handoff commit: `dda8040`
- Round 5 correction commit: `0649447`
- Round 5 handoff commit: `b425dd4`
- Round 6 correction commit: `dc3bad8`
- Round 6 handoff commit: `d2b82ec`
- Round 7 correction commit: `2f658b0`
- Round 7 handoff commit: `<TBD>`
- Role: Implementer

### Correction Scope

本次 correction 关闭 Round 6 Independent Review 的唯一 P1「Runtime issuance capability is forgeable through object.__new__ attack」，不进入 Phase H/I，不重新设计/回滚/扩大范围，不修改 Phase F/D/E：

| P1/P2 | 位置 | 修复内容 |
|---|---|---|
| P1 Capability Provenance Boundary | `src/youtube_intel/_phase_g_trust.py`（删除，超出范围）；`src/youtube_intel/scoring.py` `_RuntimeIssuanceCapability` / `_RegistrationAuthority`；`src/youtube_intel/runtime.py` `RuntimeOperations.__init__`；`src/youtube_intel/state.py` `_bind_registration_authority()` / `_atomic_register_scoring_success()` | 删除 Round 6 新增的 `_phase_g_trust.py`，将 capability 移回允许范围 `scoring.py`；`_RuntimeIssuanceCapability` 不再依赖 type-only validation，改为由 `RuntimeOperations` 在 composition 内维护唯一的 runtime-local `WeakSet` 实例注册表；repository binding 与 registrar 均通过 runtime 注入的 verifier closure 校验 authority 的 issuance capability 是否在该注册表中，从而拒绝 `object.__new__(_RuntimeIssuanceCapability)` 伪造的 capability 实例 |

### RED-first 补充测试

在 `tests/unit/test_task016c_phase_g.py` 新增/修正 RED→GREEN 测试：

- **P1 object.__new__ capability forgery：** `test_object_new_runtime_capability_forgery_fails`
  - 使用 `object.__new__(_RuntimeIssuanceCapability)` 伪造 capability 实例
  - 用该实例构造类型正确的 `_RegistrationAuthority`
  - 尝试绑定 external `SQLiteStateRepository` → `IntegrityConflict("registration authority was not issued by the runtime")`，FAIL CLOSED
  - 构造 self-consistent capability（正确 Artifact DTO、ProviderCall DTO、文件、hash）调用 register → FAIL CLOSED
  - 即使强行把 forged authority 附加到 external repository，registrar 仍因不在 runtime issuance registry 而 FAIL CLOSED
  - 断言无 Artifact success / ProviderCall success / Video SCORED / Job SUCCEEDED
- **P1 external capability instance cannot authorize：** `test_external_capability_instance_cannot_become_runtime_authority`
  - `object.__new__(_RuntimeIssuanceCapability)` 得到的实例不是 runtime-issued
  - 构造的 authority 无法通过 external repository 的 `_bind_registration_authority()`
- **P1 positive control：** `test_runtime_owned_registration_still_succeeds`（Round 6 正控保留）
  - 正常 `RuntimeOperations` composition 路径完成 commit
  - 结果：`StageCompletionResult`，job `SUCCEEDED`，video `SCORED`

### Mutation Evidence

本次新增 regression tests 在以下临时 mutation 下失败，恢复后重新 GREEN：

| 删除/替换的保护 | Mutation 操作 | 观察结果 |
|---|---|---|
| 删除 runtime-owned capability provenance validation | 临时将 `state.py` 的 verifier 默认改为 `lambda _auth: True`，并把 registrar 的 provenance 校验改为恒真 | `test_object_new_runtime_capability_forgery_fails` 失败：攻击成功，未抛出 `IntegrityConflict` |
| 替换 instance provenance validation 为 `isinstance()` | 临时将 `state.py` `_bind_registration_authority()` 与 `_atomic_register_scoring_success()` 的 provenance 校验替换为 `isinstance(authority, _RegistrationAuthority)` | `test_object_new_runtime_capability_forgery_fails` 失败：`object.__new__(_RegistrationAuthority)` 通过 isinstance 检查， forged authority 被接受 |
| 恢复 external capability construction path | （隐含）若同时允许外部构造 capability 并移除 registry 校验，则 object.__new__ 攻击链可完整走通；已由前两项 mutation 覆盖 | — |

### Mandatory Gates

| # | Gate | 结果 |
|---|---|---|
| 1 | `uv lock --check --offline` | PASS |
| 2 | `uv sync --locked --offline` | PASS |
| 3 | `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` | `60 passed` |
| 4 | `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` | `41 passed` |
| 5 | Phase A–E regression | `316 passed, 1 warning` |
| 6 | `uv run --offline pytest -x -q` | `1275 passed, 1 warning` |
| 7 | `uv run --offline mypy src` | PASS |
| 8 | `uv run --offline ruff check .` | PASS |
| 9 | `uv build --offline` | PASS |
| 10 | `bash scripts/security_scan.sh` | `status=clean`（warnings only） |
| 11 | `git diff --check` | PASS |

### Scope Verification

- 修改文件：`src/youtube_intel/scoring.py`、`src/youtube_intel/runtime.py`、`src/youtube_intel/state.py`、`tests/unit/test_task016c_phase_g.py`、`handoffs/TASK-016C.md`
- 删除文件：`src/youtube_intel/_phase_g_trust.py`（超出允许范围）
- 未修改 `providers/ollama.py`、`domain.py`、TASK-016B Language Validator、Cloud、Router、Weekly production、DB migration、依赖、`uv.lock`
- 未 rebase / squash / amend（基线 commit 之外的新 correction commit）/ merge / push / tag
- 无真实 Ollama/network/cloud 调用

### 实现者结论

- 建议状态：`READY FOR PHASE G CORRECTION ROUND 7 INDEPENDENT REVIEW`
- 下一步：由独立 reviewer 复核本 correction commit、RED/GREEN 证据、object.__new__ attack regression evidence、mutation evidence、gates 与 handoff 后决定是否验收；不进入 Phase H。

## Phase G Correction Round 8

- Status: `READY FOR PHASE G CORRECTION ROUND 8 INDEPENDENT REVIEW`
- Authority: `agent-prompts/TASK-016C-PHASE-G-IMPLEMENTATION-AUTHORIZATION.md`、
  `docs/TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md`、
  `docs/TASK-016C-HANDOFF-CHECKLIST.md`
- Correction baseline: `ef89b1e` (Phase G implementation commit)
- Round 1 correction commit: `b4497cf`
- Round 1 handoff commit: `6900b76`
- Round 2 correction commit: `b8005d1`
- Round 2 handoff commit: `52c0bcf`
- Round 3 correction commit: `1780d9a`
- Round 3 handoff commit: `c1971da`
- Round 4 correction commit: `980497d`
- Round 4 handoff commit: `dda8040`
- Round 5 correction commit: `0649447`
- Round 5 handoff commit: `b425dd4`
- Round 6 correction commit: `dc3bad8`
- Round 6 handoff commit: `d2b82ec`
- Round 7 correction commit: `2f658b0`
- Round 7 handoff commit: `e5f20b6`
- Round 8 correction commit: `105457f`
- Round 8 handoff commit: `<TBD>`
- Role: Implementer

### Correction Scope

本次 correction 关闭 Round 7 Independent Review 的唯一 P1「Repository binding accepts caller-supplied provenance verifier」，不进入 Phase H/I，不重新设计/回滚/扩大范围，不修改 Phase F/D/E：

| P1/P2 | 位置 | 修复内容 |
|---|---|---|
| P1 Caller-Supplied Verifier Boundary | `src/youtube_intel/scoring.py` `_RegistrationBindingCapability` / `_mint_registration_binding`；`src/youtube_intel/runtime.py` `RuntimeOperations.__init__`；`src/youtube_intel/state.py` `_bind_registration_authority()` | 移除 `_bind_registration_authority(authority, verifier)` 的 verifier 参数；新增 `_RegistrationBindingCapability` 作为 runtime-only binding token，内部封装 runtime-created `_RegistrationAuthority` 与 runtime-owned verifier closure；repository 只接受该 binding capability，并校验其 verifier closure 必须捕获 runtime-local `WeakSet` 注册表，从而拒绝 `lambda _auth: True` 等 caller-supplied verifier |

### RED-first 补充测试

在 `tests/unit/test_task016c_phase_g.py` 新增/修正 RED→GREEN 测试，并同步修正 Round 5/6/7 中直接调用 `_bind_registration_authority(authority)` 的测试以适配新 API：

- **P1 external supplied verifier rejection：** `test_external_supplied_verifier_cannot_authorize_registration`
  - 旧 API `_bind_registration_authority(forged_authority, lambda _auth: True)` 直接因参数不匹配/类型错误被拒绝
  - 伪造 `_RegistrationBindingCapability` 并设置 `lambda _auth: True` verifier → `IntegrityConflict("registration verifier is not runtime-issued")`，FAIL CLOSED
  - 构造 self-consistent capability（正确 Artifact DTO、ProviderCall DTO、文件、hash）调用 register → FAIL CLOSED
  - 断言无 Artifact success / ProviderCall success / Video SCORED / Job SUCCEEDED
- **P1 runtime binding capability required：** `test_repository_requires_runtime_binding_capability`
  - external `SQLiteStateRepository` 直接传入 authority 被拒绝
  - 伪造 binding capability 因 verifier 无 runtime registry 被拒绝
  - 绑定后 repository 仍无 trusted authority
- **P1 positive control：** `test_runtime_owned_binding_still_succeeds`
  - 正常 `RuntimeOperations` composition 通过 `_RegistrationBindingCapability` 完成绑定与 commit
  - 结果：`StageCompletionResult`，job `SUCCEEDED`，video `SCORED`

### Mutation Evidence

本次 regression tests 在以下临时 mutation 下失败，恢复后重新 GREEN：

| 删除/替换的保护 | Mutation 操作 | 观察结果 |
|---|---|---|
| 删除 runtime-owned verifier registry 校验 | 临时移除 `state.py` `_bind_registration_authority()` 中的 `_verifier_carries_runtime_registry(binding)` 检查 | `test_external_supplied_verifier_cannot_authorize_registration` 与 `test_repository_requires_runtime_binding_capability` 失败：伪造 binding 的 `lambda _auth: True` verifier 被接受 |
| 恢复 caller-supplied verifier callback API | 临时让 `_bind_registration_authority()` 重新接受 `is_runtime_issued_authority` 参数并在提供时绕过 binding capability 校验 | `test_external_supplied_verifier_cannot_authorize_registration` 失败：旧 API 调用不再抛出 TypeError，攻击者可通过 `lambda _auth: True` 绑定 forged authority |
| 恢复 external capability construction path | 临时注释掉 `scoring.py` `_RegistrationAuthority.__init__()` 中对 `_RuntimeIssuanceCapability` 的类型检查 | `test_external_authority_cannot_be_issued` 失败：外部可通过 `_RegistrationAuthority()` 创建 authority |

### Mandatory Gates

| # | Gate | 结果 |
|---|---|---|
| 1 | `uv lock --check --offline` | PASS |
| 2 | `uv sync --locked --offline` | PASS |
| 3 | `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` | `63 passed` |
| 4 | `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` | `41 passed` |
| 5 | Phase A–E regression | `316 passed, 1 warning` |
| 6 | `uv run --offline pytest -x -q` | `1278 passed, 1 warning` |
| 7 | `uv run --offline mypy src` | PASS |
| 8 | `uv run --offline ruff check .` | PASS |
| 9 | `uv build --offline` | PASS |
| 10 | `bash scripts/security_scan.sh` | `status=clean`（warnings only） |
| 11 | `git diff --check` | PASS |

### Scope Verification

- 修改文件：`src/youtube_intel/scoring.py`、`src/youtube_intel/runtime.py`、`src/youtube_intel/state.py`、`tests/unit/test_task016c_phase_g.py`、`handoffs/TASK-016C.md`
- 未新增/保留 `src/youtube_intel/_phase_g_trust.py` 等超出允许范围的文件
- 未修改 `providers/ollama.py`、`domain.py`、TASK-016B Language Validator、Cloud、Router、Weekly production、DB migration、依赖、`uv.lock`
- 未 rebase / squash / amend（基线 commit 之外的新 correction commit）/ merge / push / tag
- 无真实 Ollama/network/cloud 调用

### 实现者结论

- 建议状态：`READY FOR PHASE G CORRECTION ROUND 8 INDEPENDENT REVIEW`
- 下一步：由独立 reviewer 复核本 correction commit、RED/GREEN 证据、caller-supplied verifier attack regression evidence、mutation evidence、gates 与 handoff 后决定是否验收；不进入 Phase H。

## Phase G Correction Round 9

- Status: `READY FOR PHASE G CORRECTION ROUND 9 INDEPENDENT REVIEW`
- Authority: `agent-prompts/TASK-016C-PHASE-G-IMPLEMENTATION-AUTHORIZATION.md`
- Baseline: Round 8 handoff commit（当前 HEAD ancestor）
- Round 9 correction commit: `8ffd78c`
- Round 9 handoff commit: `<TBD>`
- Role: Implementer

### Correction Scope

- 修复 Round 8 Independent Review 唯一阻塞 finding：`RegistrationBindingCapability provenance remains forgeable`。
- 彻底移除 closure/WeakSet/predicate 形式的 provenance；改为由 `RuntimeOperations` 独占创建并持有的 runtime-owned binding registry。
- 修改文件：
  - `src/youtube_intel/scoring.py`
  - `src/youtube_intel/runtime.py`
  - `src/youtube_intel/state.py`
  - `tests/unit/test_task016c_phase_g.py`
  - `handoffs/TASK-016C.md`
- 未进入 Phase H；未修改 provider、domain、DB migration、依赖、uv.lock。

### Finding

Round 8 通过 closure（`_verify`）把 runtime-owned WeakSet 隐藏进 `_RegistrationBindingCapability`，但 repository 仍把 closure 当作 caller-supplied verifier 来执行；攻击者可构造自己的 closure 或捕获/重放 verifier，导致 provenance 可伪造（forgeable）。

### Attack Reproduction（Round 8 shape）

1. 攻击者通过 `object.__new__(_RuntimeIssuanceCapability)` 伪造 issuance capability。
2. 构造 `_RegistrationAuthority(forged_issuance)`，得到类型正确的 authority。
3. 通过 `object.__new__(_RegistrationBindingCapability)` 伪造 binding，并附带上自己的 `_verify` closure。
4. 若 repository 接受 caller-supplied verifier，则该伪造 binding 可通过验证并授权后续 `_atomic_register_scoring_success`。

### Redesign

- 新增 `_RegistrationBindingRegistry`：仅由 `RuntimeOperations` 通过 `_create_binding_registry()` 创建，内部使用 `weakref.WeakSet` 按对象身份记录合法的 binding。
- 重定义 `_RegistrationBindingCapability`：只携带 `_authority` 与 `_binding_registry` 引用；`__new__`、copy、pickle 全部禁用。
- 新增 `_mint_registration_binding(authority, registry)`：在创建 binding 的同时将其身份注册到 runtime-owned registry。
- `RuntimeOperations.__init__` 调用 factory 创建 registry、mint binding、再调用 `repository._bind_registration_authority(binding)`；不暴露任何 verifier/closure/WeakSet/predicate。
- `SQLiteStateRepository._bind_registration_authority(binding)`：
  - 仅接受单一 `binding` 参数；拒绝 caller-supplied verifier、callback、closure、WeakSet 或 predicate。
  - 校验 binding 的 exact type、authority 的 exact type、registry 的 exact type。
  - 最终校验 `binding in registry`（对象身份是否在 runtime-owned registry 中）。
- `SQLiteStateRepository._atomic_register_scoring_success`：
  - 校验 `_registration_binding` 与 `_binding_registry` 已绑定。
  - 再次校验 `self._registration_binding in binding_registry`。
  - 再校验 `registration.authority_proof is self._registration_authority`。

### Implementation

- `src/youtube_intel/scoring.py`
  - 新增 `_RegistrationBindingRegistry` 与 `_create_binding_registry()`。
  - 重定义 `_RegistrationBindingCapability`（`__slots__` 含 `__weakref__`；property `authority` / `_registry`）。
  - 新增 `_mint_registration_binding()`。
  - 删除 closure verifier 相关逻辑与 `inspect`/`weakref` 在 provenance 中的使用。
- `src/youtube_intel/runtime.py`
  - 使用 `_create_binding_registry()` 与 `_mint_registration_binding()` 替代 closure verifier。
- `src/youtube_intel/state.py`
  - 删除 `_verifier_carries_runtime_registry()` 与 `inspect` import。
  - `__init__` 增加 `_registration_binding = None`、`_binding_registry = None`。
  - `_bind_registration_authority(binding)` 改为仅接受 binding，新增 registry membership 校验。
  - `_atomic_register_scoring_success` 新增 binding registry membership 校验。
- `tests/unit/test_task016c_phase_g.py`
  - 更新 Round 5–8 测试，移除对 `_verify` closure 的断言，改为断言伪造 binding 不在 runtime-owned registry 中。
  - 新增 4 个 Round 9 committed tests：
    - `test_external_fake_binding_object_new_fails`
    - `test_attacker_closure_registry_cannot_authorize_binding`
    - `test_external_repository_has_no_binding_registry`
    - `test_runtime_owned_binding_registry_succeeds`

### RED / GREEN Evidence

- RED：在实现 registry membership 检查前，上述 4 个新测试与 `test_repository_requires_runtime_binding_capability`、`test_external_repository_cannot_become_trusted_root` 因伪造 binding 被接受而失败（`DID NOT RAISE IntegrityConflict`）。
- GREEN：
  - `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` → `66 passed`
  - `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` → `41 passed`
  - `uv run --offline pytest -q` → `1281 passed, 1 warning`

### Mutation Evidence

- Mutation 1 — 移除 registry membership 检查：临时注释掉 `_bind_registration_authority` 与 `_atomic_register_scoring_success` 中的 `binding not in registry` 检查；5 个攻击测试全部失败（`DID NOT RAISE IntegrityConflict`）。恢复检查后通过。
- Mutation 2 — 恢复 closure verifier API：临时给 `_bind_registration_authority` 增加可选 `verifier` 参数，若 caller-supplied verifier 返回 `True` 则绕过 registry 检查；`test_attacker_closure_registry_cannot_authorize_binding` 在传入 `lambda _binding: True` 后失败（伪造 binding 被接受）。恢复后通过。
- Mutation 3 — 用 type-only 检查替换 registry membership 检查：临时把 `_bind_registration_authority` 中的 registry 成员校验改为仅检查 `type(binding) is _RegistrationBindingCapability`；`test_external_fake_binding_object_new_fails` 失败（`object.__new__` 伪造的 exact-type binding 被接受）。恢复 registry 检查后通过。

### Validation Gates

| # | Gate | Result |
|---|------|--------|
| 1 | `uv lock --check --offline` | PASS |
| 2 | `uv sync --locked --offline` | PASS |
| 3 | `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` | `66 passed` |
| 4 | `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` | `41 passed` |
| 5 | TASK-016B regression | 未找到独立文件；由 full pytest 覆盖 |
| 6 | `uv run --offline pytest -q` | `1281 passed, 1 warning` |
| 7 | `uv run --offline mypy src` | PASS |
| 8 | `uv run --offline ruff check .` | PASS |
| 9 | `uv build --offline` | PASS |
| 10 | `bash scripts/security_scan.sh` | `status=clean`（warnings only） |
| 11 | `git diff --check` | PASS |

### Scope Verification

- 修改文件：`src/youtube_intel/scoring.py`、`src/youtube_intel/runtime.py`、`src/youtube_intel/state.py`、`tests/unit/test_task016c_phase_g.py`、`handoffs/TASK-016C.md`
- 未新增超出允许范围的文件
- 未修改 `providers/ollama.py`、`domain.py`、TASK-016B Language Validator、Cloud、Router、Weekly production、DB migration、依赖、`uv.lock`
- 未 rebase / squash / amend 基线 commit 之外的历史
- 无真实 Ollama/network/cloud 调用

### 实现者结论

- 建议状态：`READY FOR PHASE G CORRECTION ROUND 9 INDEPENDENT REVIEW`
- 下一步：由独立 reviewer 复核本 correction commit、RED/GREEN 证据、object.__new__ / closure-registry attack regression evidence、mutation evidence、gates 与 handoff 后决定是否验收；**不进入 Phase H**。

## Phase G Correction Round 10

- Status: `READY FOR PHASE G CORRECTION ROUND 10 INDEPENDENT REVIEW`
- Baseline: Round 9 implementation commit `8ffd78c`
- Role: Implementer

### Round 9 finding and architecture correction

Round 9 made `_RegistrationBindingRegistry`, `_create_binding_registry()` and
`_register()` the effective trust root.  That root was forgeable: a caller
could private-import the types, use `object.__new__`, create a fresh registry,
register a forged binding in that same registry, and then present the
self-consistent objects to the repository.

Round 10 removes the complete authority/binding/registry chain.  Runtime
composition now captures the trusted repository's bound low-level transaction
method in a local closure while creating a local committer subclass.  The
subclass is the only production caller of that captured method.  The entry is
not a `RuntimeOperations` field, is never stored in a repository, cannot be
passed by a caller, and has no module-level getter or factory.

`SQLiteStateRepository._persist_scoring_registration()` remains a mechanical
SQLite primitive only: it retains final-file verification, graph writes,
transaction ordering, idempotency and rollback semantics, but holds no
authority, binding, registry, token, verifier, entry or trusted registration
API.  The former `_atomic_register_scoring_success()` and
`_bind_registration_authority()` ingress points no longer exist.

### Scope

- Changed only:
  - `src/youtube_intel/scoring.py`
  - `src/youtube_intel/runtime.py`
  - `src/youtube_intel/state.py`
  - `tests/unit/test_task016c_phase_g.py`
  - `handoffs/TASK-016C.md`
- Did not modify providers, `domain.py`, `quality.py`, schema/migrations,
  TASK-016B implementation, dependencies or `uv.lock`.
- Did not enter Phase H/I.

### RED / GREEN evidence

Round 10 tests cover an externally constructed repository, fake subclass,
private-import plus `object.__new__`, repository attribute injection, and the
normal runtime success path.

- Initial RED (before migration): `4 failed` for the retained Round 9 trusted
  ingress, inherited API and registry exposure.
- GREEN: `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q -k round10`
  → `5 passed, 65 deselected`.
- Full Phase G: `70 passed`.

### Mutation evidence

1. Replaced the closure-captured bound transaction call with a dynamic lookup
   through `self._repository`.  The fake-subclass/attribute-injection attack
   regression failed with `ScoringPersistenceError` caused by
   `runtime entry must retain its composed transaction`.  Restored the capture;
   the test returned GREEN.
2. Temporarily restored an external repository alias
   `_atomic_register_scoring_success = _persist_scoring_registration`.  Four
   Round 10 attacks failed because the old trusted ingress reappeared.  Removed
   the alias and restored GREEN.

### Validation gates

| Gate | Result |
|---|---|
| Round 10 focused | `5 passed, 65 deselected` |
| Phase G focused | `70 passed` |
| Phase F focused | `41 passed` |
| TASK-016B (`test_scoring_language.py`) | `101 passed` |
| Full `pytest -q` | completed successfully |
| `uv run --offline mypy src` | PASS |
| `uv run --offline ruff check .` | PASS |
| `uv build --offline` | PASS |
| `bash scripts/security_scan.sh` | `status=clean` (existing warnings only) |
| `git diff --check` | PASS |

### Implementer conclusion

`READY FOR PHASE G CORRECTION ROUND 10 INDEPENDENT REVIEW`

Stop here.  Do not begin Phase H before Independent Review.

## Phase G Correction Round 11

- Status: `READY FOR PHASE G CORRECTION ROUND 11 INDEPENDENT REVIEW`
- Implementation baseline: Round 10 implementation `1d52271`
- Implementation commit: `b4402ce`
- Role: Implementer

### Round 10 finding and correction

Round 10 left `SQLiteStateRepository._persist_scoring_registration()` as a
repository-owned capability admission point.  A caller that could construct a
valid-looking `ScoringRegistrationCapability` could invoke that method with
otherwise valid DTOs and final files, producing Artifact rows, successful
ProviderCalls, a `SCORED` video and a successful job without the Phase F
aggregate or `PREWRITE_VALIDATE`.

Round 11 removes both that method and `ScoringRegistrationCapability`.
`SQLiteStateRepository` no longer has a Phase-G scoring-registration entry or
stores any registration authority, binding, registry, verifier, token or
issued marker.  The base `TrustedScoringPersistenceCommitter` remains unable
to register; `RuntimeOperations._trusted_scoring_committer()` creates the
only execution entry.  Its local subclass captures the runtime-owned
repository and contains the SQLite transaction closure.  That closure accepts
only the already prevalidated `ValidatedScoringWritePlan` and promoted final
paths supplied by the committer's ordered commit flow.

The resulting success path is:

`PhaseFTrustedScoringSuccess -> PREWRITE_VALIDATE -> runtime-local persistence
entry -> SQLite transaction`.

No authority object or caller-provided registration graph is admitted by the
repository.  The runtime-local transaction closure preserves final-file
existence/hash checks, the immediate SQLite transaction, two Artifact rows,
two ProviderCall completions, stage/job completion, and rollback behavior.

### RED / GREEN evidence

- RED: before removal, the new external-repository regression failed at
  `assert not hasattr(state_module, "ScoringRegistrationCapability")`; the
  capability still existed and was accepted by the repository entry.
- GREEN: after removal and runtime-local entry composition:
  `uv run --offline pytest -x -q tests/unit/test_task016c_phase_g.py` ->
  `68 passed`.
- Cross-boundary regression:
  `uv run --offline pytest -x -q tests/unit/test_task016c_phase_f.py
  tests/unit/test_scoring_language.py` -> `142 passed`.
- Full suite: `uv run --offline pytest -x -q` ->
  `1283 passed, 1 existing Pydantic serializer warning`.

### Attack and mutation evidence

- External repository: a freshly constructed `SQLiteStateRepository` has no
  `ScoringRegistrationCapability`, `_persist_scoring_registration`,
  `_atomic_register_scoring_success`, `_bind_registration_authority` or
  `_write_scoring_transaction` trusted ingress.  The test also verifies no
  Artifact, successful ProviderCall, `SCORED` video or successful job exists.
- Fake subclass: an external `SQLiteStateRepository` subclass cannot provide
  a transaction hook to the already composed runtime path; normal runtime
  commit remains successful.
- Object construction and attribute injection: private-import/object-new
  attempts cannot recreate the removed authority classes, and injected
  repository attributes do not add a class-level trusted entry.
- Mutation: restoring either `ScoringRegistrationCapability` or a repository
  `_persist_scoring_registration` admission method makes the committed
  external-ingress tests fail because they assert both symbols are absent.
  All mutations were reverted before commit.

### Validation gates

| Gate | Result |
|---|---|
| `uv lock --check --offline` | PASS |
| `uv sync --locked --offline` | PASS |
| Phase G focused | `68 passed` |
| Phase F + TASK-016B focused | `142 passed` |
| Full pytest | `1283 passed, 1 existing warning` |
| `uv run --offline mypy src` | PASS |
| `uv run --offline ruff check .` | PASS |
| `uv build --offline` | PASS |
| `bash scripts/security_scan.sh` | `status=clean` (warnings only) |
| `git diff --check` | PASS |

### Scope

- Implementation changed only `src/youtube_intel/scoring.py`,
  `src/youtube_intel/runtime.py`, `src/youtube_intel/state.py`, and
  `tests/unit/test_task016c_phase_g.py`.
- This handoff is the separate evidence commit.
- No changes to providers, domain/quality contracts, TASK-016B, migrations,
  dependencies, `uv.lock`, Phase H/I, or external network behavior.

### Implementer conclusion

`READY FOR PHASE G CORRECTION ROUND 11 INDEPENDENT REVIEW`

Stop here. Do not begin Phase H before Independent Review.

---

## TASK-016C Phase G Correction Round 12

### Scope and implementation

- Base: `7f7eb15`; implementation parent: `b4402ce`.
- Changed only `src/youtube_intel/scoring.py`, `src/youtube_intel/runtime.py`,
  `src/youtube_intel/state.py`, and `tests/unit/test_task016c_phase_g.py`.
- `complete_stage()` rejects `TRANSCRIPT_READY -> SCORED` before opening a
  SQLite transaction.  Runtime's normal scoring route now creates a local
  `TrustedPersistenceEntry` and calls `persist_success(exact_success)`.
- Removed exported `ValidatedScoringWritePlan` and public `commit(plan)`.
  The write plan is private implementation state; no repository method is a
  plan consumer.
- Reuse decision: `DIRECT` — existing SQLite transaction primitives,
  filesystem protocol, Phase F success aggregate and standard library only;
  no dependency changes.

### RED / GREEN and attack evidence

- RED mutation A: removing the `complete_stage` scoring guard made
  `external_repository_complete_stage_scoring_fails_closed` fail (the call
  reached legacy provider-call completion instead of rejecting pre-transaction).
- RED mutation B: restoring `TrustedPersistenceEntry.commit(plan)` made
  `forged_plan_has_no_consumer` fail.
- Both mutations were restored; Phase G focused suite: `73 passed`.
- New regressions cover external DTO `complete_stage` ingress, forged and
  copied plans, malformed success before any write, and a successful entry
  path while `complete_stage` is poisoned to fail.

### Validation and known blocker

| Gate | Result |
|---|---|
| `uv lock --check --offline` | PASS |
| `uv sync --locked --offline` | PASS (84 packages) |
| Phase G focused | PASS (`73 passed`) |
| Phase F focused | PASS (`41 passed`) |
| TASK-016B regression | PASS (`101 passed`) |
| `uv run --offline mypy src` | PASS (28 files) |
| `uv run --offline ruff check .` | PASS |
| `uv build --offline` | PASS |
| `bash scripts/security_scan.sh` | `status=clean` (pre-existing warnings) |
| `git diff --check` | PASS |
| Full pytest | BLOCKED: `tests/e2e/test_failure_recovery.py::test_service_boundary_failures_recover_without_duplicate_outputs[subtitle]` expects the legacy repository-backed scoring service to complete `TRANSCRIPT_READY -> SCORED` via forbidden `complete_stage()`. |

The full-suite failure is a direct conflict between this Round 12 requirement
and an out-of-scope legacy E2E flow.  No Phase H work, migration, dependency,
provider, domain/quality, TASK-016B, or external/network behavior was changed.

### Implementer conclusion

`IN_REVIEW / DECISION NEEDED`: authorize an update to the out-of-scope legacy
E2E flow, or explicitly accept its expected failure while Phase G closes the
generic scoring ingress.  Do not begin Phase H.

---

## TASK-016C Phase G Correction Round 13

### Implementation

- Base: `050f3cc` (Round 12 handoff); scope remained limited to scoring,
  runtime composition and the Phase G test suite.
- Removed `TrustedPersistenceEntry._persist_plan(plan)`.  The only write
  entry is `persist_success(exact PhaseFTrustedScoringSuccess)`; it creates
  its private write plan after PREWRITE validation and consumes it inline.
- Runtime transaction composition and idempotency verification no longer
  receive `_ValidatedScoringWritePlan`; they receive only the internal fields
  required for their immediate operation.  The repository remains a
  low-level transaction primitive, not a scoring ingress.
- Removed the test-only plan persistence adapter.  Test durability assertions
  now exercise `persist_success(plan.success)` only.

### Attack and mutation evidence

- `test_forged_plan_cannot_reach_persistence_sink` constructs a real-field
  copy using `object.__new__(_ValidatedScoringWritePlan)`, checks that no
  `_persist_plan`/`commit` sink exists, attempts the sole public entry, and
  verifies no Artifact, successful ProviderCall, `SCORED` video or successful
  job exists.
- Mutation: temporarily restoring `_persist_plan(plan)` made that attack test
  fail at its required absence assertion.  The mutation was reverted and the
  focused suite returned GREEN.

### Validation

| Gate | Result |
|---|---|
| `uv lock --check --offline` / `uv sync --locked --offline` | PASS |
| Phase G | PASS (`73 passed`) |
| Phase F | PASS (`41 passed`) |
| TASK-016B language | PASS (`101 passed`) |
| mypy / Ruff | PASS |
| offline build / security scan / diff check | PASS (`status=clean`; warnings only) |
| Full pytest | BLOCKED: unchanged out-of-scope legacy E2E test expects forbidden generic scoring completion: `tests/e2e/test_failure_recovery.py::test_service_boundary_failures_recover_without_duplicate_outputs[subtitle]`. |

No Phase H/I, providers, domain, migration, dependency, lockfile or network
work was performed.  Status: `READY FOR PHASE G CORRECTION ROUND 13 INDEPENDENT REVIEW`.

---

## TASK-016C Phase G Correction Round 14

- Base: `0f7045a`; changed only `scoring.py`, `runtime.py`, and the Phase G
  unit suite (plus this evidence report).
- Deleted runtime's `_persist_registration(...)` override and its scatter-field
  transaction closure. `TrustedPersistenceEntry.persist_success(success)` now
  owns PREWRITE, filesystem promotion, final-file verification and the single
  SQLite transaction in one call; all write values are function-local.
- No `_persist_plan`, `_persist_registration`, or `persist_transaction` is
  present on the runtime entry. Sink discovery verifies the sole exposed
  persistence operation has exactly one parameter: `success`.
- Added forged scatter-field and API-discovery attack coverage. A temporary
  restoration of `_persist_registration` makes the scatter-field attack test
  RED; it was restored to the removed state before final GREEN.

| Gate | Result |
|---|---|
| Phase G | PASS (`75 passed`) |
| Phase F | PASS (`41 passed`) |
| TASK-016B | PASS (`101 passed`) |
| lock/sync, mypy, Ruff, build, security scan, diff check | PASS |
| Full pytest | BLOCKED by the pre-existing out-of-scope legacy E2E expectation for forbidden generic scoring `complete_stage`, at `tests/e2e/test_failure_recovery.py::test_service_boundary_failures_recover_without_duplicate_outputs[subtitle]`. |

No Phase H/I, provider/domain/migration/dependency/lockfile work was performed.
Status: `READY FOR PHASE G CORRECTION ROUND 14 INDEPENDENT REVIEW`.

---

## TASK-016C Phase G Correction Round 15

### Scope and implementation

- Base: `cd97378` (Round 14 implementation); this correction changes only
  `tests/unit/test_task016c_phase_g.py` and this handoff.
- Round 14 production architecture is preserved: the sole success route is
  `PhaseFTrustedScoringSuccess -> TrustedPersistenceEntry.persist_success()`
  -> PREWRITE validation -> internal filesystem protocol -> internal SQLite
  transaction.  No scatter-field runtime or repository ingress was restored.
- Reuse decision: `DIRECT` — existing test fixtures, state transaction
  primitives, and standard-library hashing/dataclass replacement only; no
  dependency, provider, domain, migration, or lockfile changes.

### Behavioral scatter-sink mutation evidence

- RED attack mutation:
  `test_restored_scatter_field_sink_accepts_forged_graph_mutation` installs
  and **calls** an executable Round-13-equivalent scatter transaction fixture,
  rather than inspecting names or attributes.  It supplies forged
  `ArtifactWrite`, `ProviderCallCompletion`, `ScoringSummaryWrite`, raw bytes,
  SHA-256 values, structured-artifact hash, and fake final files.  The restored
  sink writes an Artifact row, completes the ProviderCall successfully, moves
  the video to `SCORED`, and finishes the job as `SUCCEEDED`.  This demonstrates
  the actual bypass that would return if a scatter-field persistence path were
  restored.
- GREEN current implementation:
  `test_forged_scatter_field_persistence_sink_fails` attempts each historical
  persistence ingress (`_persist_plan`, `_persist_registration`, and
  `persist_transaction`) with forged scatter values.  Each call fails closed
  with `AttributeError`; assertions confirm no artifact, successful provider
  call, `SCORED` video, or successful job exists.
- The behavioral mutation test is intentionally a test-only reconstruction of
  the removed implementation.  It is not production API and does not alter
  the Round 14 entry or create a caller-accessible persistence route.

### Validation gates

| Gate | Result |
|---|---|
| `uv lock --check --offline` | PASS |
| `uv sync --locked --offline` | PASS (84 packages) |
| Phase G focused | PASS (`76 passed`) |
| Phase F focused | PASS (`41 passed`) |
| TASK-016B regression | PASS (`101 passed`) |
| `uv run --offline mypy src` | PASS (28 source files) |
| `uv run --offline ruff check .` | PASS |
| `uv build --offline` | PASS |
| `bash scripts/security_scan.sh` | `status=clean` (warnings only) |
| `git diff --check` | PASS |
| Full pytest | BLOCKED: unchanged out-of-scope legacy E2E flow expects generic `complete_stage()` to perform forbidden `TRANSCRIPT_READY -> SCORED`: `tests/e2e/test_failure_recovery.py::test_service_boundary_failures_recover_without_duplicate_outputs[subtitle]`. |

### Scope verification and conclusion

- Changed files: `tests/unit/test_task016c_phase_g.py` and this handoff only.
- No Phase H/I, legacy migration, retry/recovery/cache, providers, domain,
  dependency, lockfile, or production persistence-architecture changes.

Status: `READY FOR PHASE G CORRECTION ROUND 15 INDEPENDENT REVIEW`.

---

## TASK-016C Legacy E2E Migration-01 — Trusted Scoring Harness Cutover

### Metadata and scope

- Base: `c9c4331` (Phase G accepted-for-handoff head).
- Implementation commit: `532f312` — `TASK-016C Legacy E2E Migration-01 trusted scoring harness cutover`.
- Allowed and changed implementation file: `tests/e2e/test_mvp_flow.py` only.
- Reuse decision: `DIRECT` — the existing `RuntimeOperations`, runtime-owned
  `TrustedPersistenceEntry`, Phase F seam, Phase G filesystem/SQLite protocol,
  Ollama quality-judge adapter with deterministic fake transport, and existing
  offline fixtures. No third-party code or dependency was added.

### Harness migration evidence

- `_OfflineMvpFlow` now constructs a real `RuntimeOperations` from a temporary,
  deterministic local configuration and uses its owned repository and DATA root.
  SQLite reads now point to that runtime database (`data/state.sqlite`); no second
  scoring database is created.
- The deterministic scoring fake now implements `primary_attempt()` and returns a
  canonical `PrimaryScoringAttempt`; it no longer returns a bare `ScoreResult` or
  exposes a legacy raw-response consumption API.
- The E2E scoring stage is now:

  ```text
  fake primary_attempt
    -> RuntimeOperations.run_primary_trusted_scoring
    -> PhaseFTrustedScoringSuccess
    -> RuntimeOperations._trusted_persistence_entry(...).persist_success
    -> PREWRITE_VALIDATE -> filesystem protocol -> atomic SQLite registration
  ```

- The harness preserves its established mixed subtitle/Whisper transcript
  fixtures before handing their verified text to the runtime scoring composition.
  This avoids a provenance mismatch in the runtime's generic subtitle loader
  while keeping the scoring completion path entirely runtime-owned.
- `RepositoryBackedScoringService`, `ScoringJobContext`, bare `ScoreResult`
  scoring output, and legacy scoring `complete_stage()` use were removed from
  `tests/e2e/test_mvp_flow.py`. The five scenarios, note user-section
  preservation, cloud-disabled flow, idempotency, and output assertions remain.

### Validation

| Command | Result |
|---|---|
| `uv run pytest tests/e2e/test_mvp_flow.py -q` | PASS (`3 passed`) |
| `uv run pytest tests/unit/test_task016c_phase_g.py -q` | PASS (`76 passed`) |
| `uv run ruff check tests/e2e/test_mvp_flow.py` | PASS |
| `git diff --check` | PASS |
| `uv run pytest -x -q` | BLOCKED at `tests/integration/test_ollama_provider.py::test_successful_language_repair_persists_only_the_valid_repair_response` after `105 passed`: its `_repository_scoring_service()` still constructs `RepositoryBackedScoringService` and expects its forbidden persistence completion to succeed. This is a remaining legacy scoring dependency outside this migration's allowed E2E scope. |

### Scope and conclusion

- Production code changes: **none**.
- No schema, migration, dependency, lockfile, provider implementation, cache,
  repair/retry/recovery, Phase H, or real network/Vault/cloud operation was
  performed.
- Diff review found only the harness migration before the implementation commit;
  the handoff commit contains only this evidence.

Status: `READY FOR Legacy E2E Migration-01 Independent Review`.

---

## TASK-016C Legacy E2E Migration-02 — Trusted Repair Flow Test Harness Cutover

### Metadata and scope

- Base: `faffe4d` (Phase G accepted; Legacy E2E Migration-01 approved).
- Implementation commit: `82d6d4b` — `TASK-016C Legacy E2E Migration-02 trusted repair flow cutover`.
- Allowed and changed implementation file: `tests/integration/test_ollama_provider.py` only.
- Reuse decision: `DIRECT` — existing `RuntimeOperations`, runtime-owned repository and
  `TrustedPersistenceEntry`, Phase F aggregate, Phase G PREWRITE_VALIDATE/filesystem/SQLite
  protocol, existing Ollama fake transport, and existing local Quality Judge fake transport.
  No third-party code, dependency, schema, migration, provider production code, or lockfile changed.

### Legacy removal and trusted-flow evidence

- Removed this file's `_repository_scoring_service()` and every direct reference to
  `RepositoryBackedScoringService`, `ScoringJobContext`, `ScoringPersistenceError`, and
  ad-hoc `SQLiteStateRepository` construction. The harness now creates `RuntimeOperations`,
  uses `runtime._repository`, and obtains its persistence entry only through
  `runtime._trusted_persistence_entry(...)`.
- The test-only `_RepairFlowProvider` executes the existing fake PRIMARY/one-shot-REPAIR
  transport sequence, consumes only its canonical final repair envelope, and creates a
  `PrimaryScoringAttempt`. The test then executes:

  ```text
  fake repair flow -> RuntimeOperations.run_primary_trusted_scoring
    -> PhaseFTrustedScoringSuccess
    -> runtime-owned TrustedPersistenceEntry.persist_success
    -> PREWRITE_VALIDATE -> filesystem -> atomic SQLite registration
  ```

- No test manually creates a scoring-success Artifact, updates the video to `SCORED`, marks
  the job `SUCCEEDED`, or calls `complete_stage()` for scoring success.

### Repair-semantics evidence

- `test_successful_language_repair_persists_only_the_valid_repair_response` asserts the
  exact fake provider sequence `GET, POST, POST`, the repair-only raw envelope, absence of
  the invalid primary reason from persisted data, Quality Judge `GET, POST`, completed scoring
  ProviderCall binding to the raw Artifact, structured Artifact registration, and final
  `SCORED`/`SUCCEEDED` state produced by the trusted entry.
- `test_failed_language_repair_never_persists_a_formal_scoring_artifact` keeps the invalid
  primary plus invalid repair sequence and proves no raw/structured Artifact or scoring
  ProviderCall success is created; video and job remain `TRANSCRIPT_READY`/`RUNNING`.
- Added `test_primary_provider_failure_does_not_repair_or_persist_in_trusted_flow`: injected
  primary transport failure stops after `GET, POST`, invokes no Quality Judge, and leaves no
  trusted persistence output.

### Validation

| Command | Result |
|---|---|
| `uv run pytest tests/integration/test_ollama_provider.py -q` | PASS (`72 passed`) |
| `uv run pytest tests/e2e/test_mvp_flow.py -q` | PASS (`3 passed`) |
| `uv run pytest tests/unit/test_task016c_phase_g.py -q` | PASS (`76 passed`) |
| `uv run ruff check tests/integration/test_ollama_provider.py` | PASS |
| `git diff --check` | PASS |
| `uv run pytest -x -q` | BLOCKED after `135 passed` at `tests/integration/test_pipeline.py::test_pipeline_completes_high_low_no_subtitle_deferred_and_unavailable_idempotently` |

### Full-suite blocker analysis

- The full-suite failure is not the migrated Ollama repair path. `tests/integration/test_pipeline.py`
  contains its own generic `_FakeStages` scoring handler that calls legacy `complete_stage()` with
  `target_status=SCORED` and a scoring summary. Under the Phase G trusted scoring-success guard,
  that handler leaves the video at `TRANSCRIPT_READY`; its assertion then fails.
- That fixture is outside this task's explicit allowlist. It was not modified, weakened, skipped,
  or bypassed. No Phase H repair/retry/recovery work was performed.

### Diff review and conclusion

- Implementation diff is limited to the approved integration harness; handoff diff is evidence only.
- No dependency, Schema, migration, credential, real network, cloud, Vault, legacy persistence ingress,
  production code, or Phase H change was made.

Status: `IN_REVIEW — Legacy E2E Migration-02 implementation complete; full suite blocked by the next out-of-scope legacy scoring harness`.

---

## TASK-016C Legacy Migration-03 — Pipeline Trusted Flow Cutover

### Metadata and scope

- Base: `7b69246` (Phase G accepted; Legacy Migrations 01 and 02 approved).
- Implementation commit: `4dd6d55` — `TASK-016C Legacy Migration-03 pipeline trusted flow cutover`.
- Allowed and changed implementation file: `tests/integration/test_pipeline.py` only.
- Reuse decision: `DIRECT` — existing `RuntimeOperations`, its runtime-owned
  `TrustedPersistenceEntry`, Phase F aggregate, Phase G prewrite/filesystem/SQLite
  protocol, Ollama quality-judge adapter, state-machine orchestrator, and offline
  test doubles. No third-party source, production dependency, schema, migration, or
  lockfile was added or changed.

### Legacy dependency removal and trusted-flow proof

- Removed `_FakeStages`, `ScoringSummaryWrite`, and the scoring branch that passed
  `target_status=SCORED` to `complete_stage()`. The non-scoring metadata,
  transcript, analysis, note, unavailable, deferred, interruption, and retry fakes
  retain their prior state-machine behavior.
- The replacement `_PipelineStages` creates a canonical `PrimaryScoringAttempt` via
  the deterministic offline scoring fake, then executes exactly:

  ```text
  fake primary_attempt
    -> RuntimeOperations.run_primary_trusted_scoring
    -> PhaseFTrustedScoringSuccess
    -> RuntimeOperations._trusted_persistence_entry(...).persist_success
    -> PREWRITE_VALIDATE -> verified filesystem writes -> atomic SQLite registration
  ```

- The analysis setup no longer manually advances `TRANSCRIPT_READY -> SCORED` or
  writes `should_summarize`. It advances only the unchanged pre-scoring states and
  lets a real planned/claimed scoring job complete through the same trusted entry.
- Anti-regression assertions require each asserted high/low trusted success to have
  exactly the raw and structured scoring artifacts, hashes matching the on-disk
  content, and the two associated `SUCCEEDED` ProviderCalls. Restoring the old fake
  `complete_stage(...SCORED)` path cannot create that graph, so the pipeline test
  fails rather than accepting a manual scoring completion.

### Pipeline behavior preservation

- The mixed high-value, low-value, no-subtitle, deferred, and unavailable batch
  remains covered; high and low flows now additionally prove trusted output.
- Deferred resume, interruptions before/after call/after persistence, retryable
  isolation, and high-value analysis/note behavior remain covered. Scoring-stage
  interruption recovery also asserts one trusted provider attempt and its complete
  persistence graph.
- Re-running the batch compares jobs, artifacts, ProviderCalls, stage-call counts,
  and trusted scoring-provider counts, proving no duplicate scoring output or call.

### Validation

| Command | Result |
|---|---|
| `uv run pytest tests/integration/test_pipeline.py -q` | PASS (`15 passed`) |
| `uv run pytest tests/integration/test_ollama_provider.py -q` | PASS (`72 passed`) |
| `uv run pytest tests/e2e/test_mvp_flow.py -q` | PASS (`3 passed`) |
| `uv run pytest tests/unit/test_task016c_phase_g.py -q` | PASS (`76 passed`) |
| `uv run ruff check tests/integration/test_pipeline.py` | PASS |
| `git diff --check` | PASS |
| `uv run pytest -x -q` | BLOCKED after `218 passed` at `tests/integration/test_state_store.py::test_scoring_stage_requires_summary_and_commits_it_atomically` |

### Full-suite blocker analysis

- The Migration-02 blocker in `test_pipeline.py` is removed: this file now passes
  independently and completes through the Phase G trusted boundary.
- The next full-suite failure is an out-of-scope legacy state-store assertion. It
  manually constructs a `TRANSCRIPT_READY` scoring job plus legacy ProviderCall and
  Artifact, invokes `complete_stage()`, and expects its old `"scoring summary"`
  `IntegrityConflict` message. The current trusted guard correctly rejects the
  attempted legacy scoring completion with
  `"TRANSCRIPT_READY -> SCORED requires the runtime trusted persistence entry"`.
- No production code, schema, or test assertion outside this task's allowlist was
  changed to bypass or mask that failure.

### Diff review and conclusion

- Implementation diff is limited to the authorized pipeline integration harness;
  this handoff commit is evidence only.
- No Phase H, repair/retry/recovery/cache migration, source/provider production
  code, dependency, lockfile, real network, cloud, or Vault operation was performed.

Status: `IN_REVIEW — Legacy Migration-03 implementation complete; full suite now exposes the next legacy state-store scoring assertion`.

---

## TASK-016C Phase H1-A — Identity and Lease Admission Only

### Metadata and scope

- Base: `0c9cfb8` (`docs: define H1 lease recovery ordering`).
- Implementation commit: `db14c60` — `feat: add H1 scoring dispatch admission`.
- Reuse decision: `DIRECT` — existing canonical scoring request identity,
  `build_provider_request_hash`, `build_judge_h1_h2`, current Job lease fields,
  and current ProviderCall read model. No third-party component, dependency,
  migration, or lockfile change was introduced.

### Delivered H1-A behavior

- Added deterministic runtime identities for PRIMARY, REPAIR (identity only; no
  repair execution), PRIMARY Judge, and REPAIR Judge. REPAIR canonical input
  binds the primary identity/raw/failure classification, provider/model/digest,
  request parameters, and output language; Judge identities retain the frozen
  H1/H2 builder contract.
- Added a process-memory `ScoringDispatchAdmission` that consumes each role at
  most once, re-reads the current `SCORING` job, requires the uniquely owned,
  unexpired `RUNNING` lease, and denies every existing ProviderCall state before
  external dispatch. Denials carry a non-retryable safe error.
- Runtime owners are unique per `RuntimeOperations` instance. PRIMARY is
  admitted before `primary_attempt`; PRIMARY Judge is admitted immediately
  before Judge dispatch. Any exception after PRIMARY admission is terminal
  unknown-provider state; an actual process interruption remains unhandled so
  the expired-lease recovery path classifies it first.
- Expired `SCORING` jobs now become terminal `FAILED_FINAL` with the stable
  `UNKNOWN_PROVIDER_STATE` diagnostic inside the existing reclaim transaction;
  non-scoring reclamation is unchanged.

### Tests and verification

| Command | Result |
|---|---|
| `uv run pytest tests/unit/test_task016c_phase_h1_admission.py` | PASS (`9 passed`) |
| `uv run pytest tests/unit/test_task016c_phase_g.py` | PASS (`76 passed`) |
| `uv run pytest tests/integration/test_runtime_composition.py tests/integration/test_state_store.py` | PASS (`43 passed`) |
| `uv run mypy src` | PASS (`29 source files`) |
| `uv run ruff check .` | PASS |
| `git diff --check` | PASS |

Mutation evidence: temporarily removing duplicate-role consumption caused
`test_duplicate_primary_admission_is_denied` to fail with `DID NOT RAISE
ScoringDispatchDenied`; the guard was restored and the focused suite passed.

### Boundary review

- `TrustedPersistenceEntry.persist_success()` was not modified.
- No repository scoring ingress, alternate SQLite success writer, manual
  Artifact/ProviderCall success, schema/migration, cache recovery, or repair
  execution was added.
- H2 and H3 were not started. The sole recovery change is the H1-authorized
  pre-reclaim terminal classification for expired SCORING leases.

Status: `IN_REVIEW — Phase H1-A implementation and evidence complete`.
