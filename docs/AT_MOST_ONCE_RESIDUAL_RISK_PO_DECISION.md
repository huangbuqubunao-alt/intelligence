# At-Most-Once Residual Crash-Window — Product Owner Decision Package

## Status and scope

**PRODUCT OWNER DECISIONS RECORDED.** The Product Owner rejected Window 1 and
authorized only its remediation; accepted Windows 2 and 3 only for the current
personal/private/proprietary controlled source/wheel/sdist posture. This record
does not qualify a provider, accept real output, authorize TASK-016G, perform
operational validation, broaden distribution, or change the current `NO-GO`.

The authoritative release disclosure lists exactly these three windows in
[`RELEASE_BLOCKERS.md` §2.3](RELEASE_BLOCKERS.md#23-at-most-once-risk-acceptance):

1. Provider success → SQLite commit
2. File atomic replace → SQLite commit
3. Audio cleanup final CAS

They are evaluated separately below. A decision on one does not decide either
of the other two.

### Current release state — unchanged

| Item | State |
| --- | --- |
| Current release | **NO-GO** |
| Live Deep Analysis provider | **UNQUALIFIED** |
| Real Deep Analysis output acceptance | **NOT YET ELIGIBLE** |
| TASK-016G | **UNAUTHORIZED** |
| Operational validation | **UNRUN / REQUIRES PO AUTHORIZATION** |
| Canonical security scanner | **EXIT 1 / exactly 11 finitely accepted intentional-positive fixtures**; not PASS |
| Human governance | **trigger-based / current private controlled posture** |

### Important meaning of “at-most-once best effort”

The implementation prevents ordinary concurrent calls with a deterministic
request-hash reservation and verifies durable artifacts before treating a prior
call as complete. It does **not** make an external provider, a filesystem, and
SQLite one atomic transaction. In particular, it does not prove exactly-once
provider execution after a process crash. A retry can be necessary when the
provider may already have acted but the corresponding durable receipt is absent.

No numerical probability is asserted here. Each window requires the stated
operations to occur and then a process/machine crash or equivalent loss of
execution in the narrow interval stated.

## Window 1 — Provider success → SQLite commit

### Authoritative identity and implementation path

| Field | Evidence |
| --- | --- |
| Authoritative name | **Provider success → SQLite commit** |
| Authoritative source | `RELEASE_BLOCKERS.md` §2.3; [ADR-003 §S-07](decisions/ADR-003-sqlite-state-store-contract.md) states that an external call can succeed before SQLite records it. ADR-008 preserves the same non-exactly-once boundary for cloud analysis. |
| Code path | A provider call is reserved by `SQLiteStateRepository.reserve_provider_call()` in `state.py`; `AnalysisService.analyze()` calls `provider.summarize_with_credential()` and then `complete_stage()` in `analysis.py`. Local transcription similarly calls its adapter and then `complete_stage()` in `transcripts.py`. Scoring uses the same reservation/completion model and its dedicated trusted persistence entry. |
| State transition | A `provider_calls` row is `PENDING` while owned by a lease; successful stage completion records artifacts, marks the provider call `SUCCEEDED`, and advances the pipeline in one SQLite transaction. |
| External side effect | Execution of the configured provider. Depending on the authorized future configuration this can be a cloud request (data/cost/account-visible) or a local provider process. |

### What happens

1. **Normal flow.** The runtime first creates a durable `PENDING` reservation
   keyed by the normalized request. It invokes the provider once, validates its
   response, prepares response artifacts, then commits artifacts, the provider
   receipt/status, and the pipeline transition in SQLite.
2. **Crash point.** The process/machine crashes after the provider has returned
   success but before the SQLite transaction that records the successful call
   and stage has committed.
3. **Already happened.** The provider may have consumed a request. For a cloud
   provider that may mean an account-visible request and possible charge; it
   may also mean the approved input was transmitted once. A local provider may
   have consumed local CPU/model resources.
4. **Not yet recorded.** SQLite may still show `PENDING` (or later a retriable
   failure) rather than `SUCCEEDED`; the response artifact/receipt may be
   absent, unindexed, or not yet verified as a recovery artifact.
5. **Restart behavior.** While its lease remains valid, another worker does not
   acquire the call. After expiry, the repository checks the deterministic
   artifact key. A verified, indexed artifact lets it mark the call succeeded
   without another provider invocation. If no such durable verified artifact
   exists, a later authorized retry can acquire the reservation and invoke the
   provider again. The Phase-G scoring path has additional verified-orphan
   recovery rules; that does not turn every provider path into exactly-once.
6. **User-visible consequence.** The user may see the item remain incomplete
   until recovery/retry. If a retry is required, the final analysis/scoring
   result can be produced later; the external provider may have been asked
   twice even though only one eventual result is committed.
7. **Worst credible consequence.** One logical request can cause two provider
   executions, with a duplicated authorized cloud disclosure/cost where a cloud
   provider is used, and the first response can be unavailable for audit or
   display if it was never durably captured.

### Risk classification

| Question | Answer |
| --- | --- |
| Duplicate possible? | **CONDITIONALLY YES** — only if the first success lacks a verified durable recovery artifact and the expired reservation is retried. |
| Loss/skipped work possible? | **CONDITIONALLY YES** — the first response can be lost; intended processing remains retryable if the provider is available and a retry is authorized. |
| Authoritative data corruption possible? | **NO** — SQLite does not commit a partial stage transaction. A `PENDING` row or non-authoritative orphan is not a committed success. |
| Privacy/security risk created by the crash itself? | **CONDITIONALLY** — the crash creates no new log/cache/template disclosure, but a duplicate cloud retry may resend the same already-authorized payload. |
| Recovery | **PARTIAL.** Automatic only when restart/recovery finds a matching verified indexed (or specifically supported verified-orphan) artifact. Otherwise the normal retry path is required; if the provider/result is no longer available, the original response cannot be reconstructed. |
| Detection | Compare the expired/retryable `provider_calls` reservation with the deterministic artifact key and hash. `SUCCEEDED` with a valid artifact is recoverable; missing/unverified evidence remains a retry/fail-closed condition. Provider-side billing/request history, if supplied by that provider, is separate evidence. |
| Preconditions | A provider must succeed; execution must stop before durable success registration; then the lease must expire and recovery/retry must run. |
| Side-effect class / blast radius | External provider action; **single request/item**, potentially external-account-visible for cloud configuration. |
| Reversibility | Provider execution is generally irreversible; the local stage is recoverable only when the response evidence is durable and valid. |
| Severity if it occurs | **MEDIUM.** It can duplicate cost and an authorized disclosure for one item, but current guards prevent a second committed pipeline success and no qualified live Deep Analysis provider exists today. |

### Why it exists and credible remediation

This is a **fundamental distributed-system boundary**, not merely an omitted
`try` block: a remote provider cannot participate in SQLite's local transaction.
The current request-hash reservation, lease, deterministic artifact key, hash
verification, and Phase-G orphan handling reduce the window but cannot prove
that an already-completed remote request will never be repeated.

| Option | Design and scope | Impact / new failure modes | Complexity |
| --- | --- | --- | --- |
| Provider-supported idempotency key | Send the deterministic request hash as an idempotency key and persist the provider receipt/response identity with the completed call. | Affects provider adapters, `analysis.py`, provider contracts, `state.py`, migration/schema if a receipt is stored, and provider qualification tests. Requires evidence that each selected provider honors the key; unsupported providers retain the residual window. Impacts ADR-008 and the future TASK-016 provider path; does not change ADR-028. | **LARGE** |
| Durable response-first recovery protocol | Extend the generic provider paths to atomically promote and verify a response artifact before final registration, with explicit orphan adoption comparable to the existing specialized Phase-G protocol. | Affects artifact writers, `analysis.py`, `transcripts.py`/`scoring.py`, `state.py`, recovery runtime, and likely a migration/ADR. Adds orphan retention, disk-pressure, and recovery-validation failure modes. It still cannot cover a crash before any response bytes are durably written. Impacts TASK-016/ADR-008 design boundaries; ADR-028 remains unrelated. | **LARGE** |
| Reject a provider lacking idempotency/recovery evidence | Make live qualification require provider-specific idempotency/receipt behavior before that provider can be a reference provider. | Affects qualification policy/tests and may leave no eligible provider. It reduces exposure but does not retrofit exactly-once to all provider types. Impacts TASK-016 qualification; no schema change necessarily. | **MEDIUM** |

**If accepted:** acceptance is limited to one provider execution that may be
unrecorded and conditionally retried in this exact crash interval. It does not
accept future provider regressions, a broader cloud/privacy exception, provider
qualification, TASK-016G, operational validation, or unrelated crash windows.

**If rejected:** current release remains blocked until a PO-authorized design
and implementation changes the selected provider/recovery protocol. A remedy
can reduce duplication materially, but cannot honestly guarantee exactly-once
without selected-provider idempotency/receipt semantics that are independently
verified.

## Window 2 — File atomic replace → SQLite commit

### Authoritative identity and implementation path

| Field | Evidence |
| --- | --- |
| Authoritative name | **File atomic replace → SQLite commit** |
| Authoritative source | `RELEASE_BLOCKERS.md` §2.3; [ADR-009 N-11/N-12](decisions/ADR-009-obsidian-note-contract.md) explicitly documents replace-after-file verification followed by SQLite completion and retry reconciliation. |
| Code path | `ObsidianNoteSink._write_or_verify()` and `_atomic_replace()` in `providers/obsidian.py` write a managed video note; `_upsert_video_note()` then calls `complete_stage()`. `upsert_weekly_report()` uses the same replace pattern then `upsert_report()`. |
| State transition | Video note: `ANALYSIS_READY → NOTE_WRITTEN` plus `VIDEO_NOTE` artifact/job completion. Weekly report: file exists before the report row is upserted as `WRITTEN`. |
| External side effect | A write to the configured runtime Vault filesystem. No shipped template is mutated and no remote provider action occurs in this window. |

### What happens

1. **Normal flow.** The sink validates the anchored Vault directory, writes and
   fsyncs a private temporary file, verifies it, rechecks the target and
   directory identity, atomically replaces the target, fsyncs the directory,
   then records the Artifact/pipeline or weekly-report state in SQLite.
2. **Crash point.** The process/machine crashes after successful `os.replace`
   and directory fsync, but before the corresponding SQLite transaction commits.
3. **Already happened.** The new managed note or weekly file is visible in the
   runtime Vault. Existing video-note user-region bytes are merged into the
   desired file before replacement.
4. **Not yet recorded.** The video may remain `ANALYSIS_READY`, the job may not
   be completed, and the Artifact/report row may be absent or unchanged.
5. **Restart behavior.** A retried note job reopens and validates the managed
   file, preserves the user region, and completes SQLite bookkeeping; it does
   not create a second note path. The documented retry test injects a SQLite
   failure after artifact handling, leaves the note on disk, and then completes
   the same note job. If the file is missing, structurally invalid, or conflicts
   with user changes, recovery fails closed for operator attention rather than
   overwriting it.
6. **User-visible consequence.** A note/report can appear in the Vault while
   the application still reports the item as not yet written. On a successful
   retry, the record catches up. There is no automatic filename multiplication.
7. **Worst credible consequence.** One correctly written managed file remains
   unindexed until recovery, so pipeline progress pauses. If later manual edits
   make the file invalid or conflict with its managed identity, the operator
   must resolve the conflict before the job can be completed; the sink refuses
   to overwrite the conflicting file.

### Risk classification

| Question | Answer |
| --- | --- |
| Duplicate possible? | **NO** for duplicate managed note/report files under the deterministic path and no-clobber/identity checks. A retry may revalidate or update the same file, not create a second logical output. |
| Loss/skipped work possible? | **CONDITIONALLY YES** — bookkeeping/progress can remain pending until retry. The already-replaced file is not intentionally deleted on SQLite failure. |
| Authoritative data corruption possible? | **CONDITIONALLY** — the durable file and SQLite can temporarily disagree, but SQLite transaction rollback prevents a partial authoritative database transition and the sink fails closed on file/identity conflict. |
| Privacy/security risk created by the crash itself? | **NO.** The write is already an authorized runtime-Vault operation; the crash creates no new package, log, error, provider, or credential surface. |
| Recovery | **PARTIAL.** A normal retry can automatically reconcile a valid managed file. Invalid/missing/conflicting files deliberately require manual resolution; the recovery code must not overwrite user content. |
| Detection | Compare pipeline/report state and Artifact row with the deterministic managed file, validate its markers/provenance/hash, and observe a retryable note/report job. The note-retry test demonstrates the valid-file path. |
| Preconditions | The file replacement and directory fsync must succeed; execution must stop before SQLite commits; later recovery must be attempted. |
| Side-effect class / blast radius | Runtime Vault filesystem write; **single note or weekly report**, not the whole Vault. |
| Reversibility | **Recoverable.** The file is retained and valid content can be reconciled. A conflicting user change is intentionally not auto-reversible. |
| Severity if it occurs | **MEDIUM.** It can halt one item and require operator resolution, but preserves the written file and user region, prevents path escape/overwrite, and does not duplicate logical notes. |

### Why it exists and credible remediation

This is a **filesystem/SQLite atomicity boundary**. `os.replace` is atomic for
the filesystem target, while SQLite commits its own transaction; neither can
make the other part of its atomic commit. The current implementation is not a
shortcut: it already fsyncs, validates after replacement, keeps the final file,
and reconciles through a guarded retry.

| Option | Design and scope | Impact / new failure modes | Complexity |
| --- | --- | --- | --- |
| Persist a write-intent/reconciliation record before replace | Add a durable note/report intent state with expected artifact identity/hash; restart scans and either safely completes or fails closed. | Requires `state.py`, a migration, `providers/obsidian.py`, runtime/recovery orchestration, ADR-009 revision, and crash-injection tests. Adds durable intents, cleanup/retention rules, and stale-intent handling. It improves detection/recovery but still cannot make Vault + SQLite a single transaction. | **MEDIUM** |
| Make SQLite the canonical rendered-output source and regenerate the Vault file | Store enough rendered authority in SQLite and make filesystem output a projection. | Requires major domain/retention/privacy redesign, migration, changes to user-region semantics and ADR-009. It risks retaining more user content in SQLite and still leaves a projection crash boundary. TASK-016/ADR-008/ADR-028 are not directly changed, but privacy and Vault architecture are materially affected. | **LARGE** |
| Retain current guarded reconciliation | Keep the present deterministic file identity, fsync, no-overwrite, and retry behavior. | No production change; recovery remains partial for manually modified/invalid files. Existing note/recovery tests remain the applicable evidence. | **SMALL** |

**If accepted:** acceptance is limited to a valid runtime Vault file being
temporarily ahead of its SQLite record after this exact crash interval. It does
not accept overwriting user content, template mutation, real-Vault operation
without separate PO authorization, package privacy leakage, or another window.

**If rejected:** current release remains blocked until a PO-authorized
reconciliation design is implemented and independently tested. It can improve
automatic repair and observability but cannot make two separate durable systems
strictly atomic without changing the architecture and its user-content tradeoffs.

## Window 3 — Audio cleanup final CAS

### Authoritative identity and implementation path

| Field | Evidence |
| --- | --- |
| Authoritative name | **Audio cleanup final CAS** |
| Authoritative source | `RELEASE_BLOCKERS.md` §2.3. The implementation and its residual race are documented by `cleanup_successful_audio()` in `transcription.py`; the final-CAS test is in `tests/integration/test_whisper_provider.py`. |
| Code path | After transcription `complete_stage()` succeeds, `LocalTranscriptionService.transcribe()` calls `cleanup_successful_audio()`. That function validates the DATA-root audio Artifact and hash, calls `unlink()`, then calls `SQLiteStateRepository.mark_artifact_deleted()` to CAS `deleted_at`. |
| State transition | The transcript/provider result is already complete. The cleanup transition is an Artifact index update: `deleted_at IS NULL → deleted_at=<time>` conditioned on Artifact ID and content hash. |
| External side effect | Deletion of one ephemeral audio file under the configured runtime DATA root. |

### What happens

1. **Normal flow.** After a successful transcription is durably registered, the
   cleanup verifies that the audio Artifact is eligible, still matches its
   registered hash, is inside DATA, and is not a symlink. It deletes the file,
   then marks the matching Artifact row deleted with a compare-and-swap update.
2. **Crash point.** The process/machine crashes after `unlink()` succeeds but
   before `mark_artifact_deleted()` commits, or a competing final CAS causes the
   caller to receive `INDEX_CONFLICT` after deletion has already occurred.
3. **Already happened.** The ephemeral audio file is gone. The completed
   transcript and its successful pipeline state were committed before cleanup.
4. **Not yet recorded.** The Artifact row can still have `deleted_at=NULL`, so
   it describes an audio file that no longer exists.
5. **Restart behavior.** The current cleanup function detects a missing file as
   `MISSING`; it does not automatically set `deleted_at` after a missing-file
   result. The final-CAS race test intentionally observes `INDEX_CONFLICT` with
   the file absent.
6. **User-visible consequence.** The user normally sees no audio because it is
   ephemeral cleanup. Diagnostics or an operator inventory can show a stale
   cleanup record; the completed transcript remains available.
7. **Worst credible consequence.** The original audio is unavailable for later
   debugging/retranscription while the database still says it is undeleted.
   The transcript is not rolled back or corrupted; obtaining audio again would
   require a separately authorized acquisition path.

### Risk classification

| Question | Answer |
| --- | --- |
| Duplicate possible? | **NO.** The side effect is deletion, and cleanup never retries deletion after a missing-file result. |
| Loss/skipped work possible? | **CONDITIONALLY.** Intended transcription work is already complete; the ephemeral source audio is intentionally lost and cannot be reused if later debugging/retranscription needs it. |
| Authoritative data corruption possible? | **CONDITIONALLY.** SQLite can retain stale deletion metadata, but the committed transcript/pipeline record is not corrupted. |
| Privacy/security risk created by the crash itself? | **NO.** The missing audio reduces stored sensitive media; stale index metadata does not reveal its content or a credential. |
| Recovery | **MANUAL.** After verifying the completed transcription, Artifact identity/hash, and physical absence under the controlled DATA root, an authorized operator can reconcile `deleted_at` using the repository CAS. If those facts cannot be verified, the index must remain unchanged and the condition is reported rather than guessed. |
| Detection | Find undeleted eligible audio Artifact rows, validate their controlled relative path, and observe that the file is absent or cleanup returns `MISSING`/`INDEX_CONFLICT`. Do not expose an absolute path or audio contents in diagnostics. |
| Preconditions | A completed transcription must reach cleanup; the file/hash checks and `unlink()` must succeed; then execution must stop before the index CAS commits, or a competing index update must race the CAS. |
| Side-effect class / blast radius | Runtime DATA filesystem deletion; **single ephemeral audio item**. |
| Reversibility | **Partially recoverable.** Metadata can be reconciled; the deleted audio cannot be restored by this component. |
| Severity if it occurs | **LOW.** The durable transcript is already complete, the file is deliberately ephemeral, and the residual problem is stale deletion metadata plus loss of a debugging/retranscription input. |

### Why it exists and credible remediation

This is also a **filesystem/SQLite atomicity boundary**. Neither the OS unlink
operation nor SQLite's compare-and-swap can atomically include the other.
The current implementation deliberately chooses fail-closed validation before
deletion and never represents a failed CAS as cleanup success.

| Option | Design and scope | Impact / new failure modes | Complexity |
| --- | --- | --- | --- |
| Add a cleanup-intent/state-machine record | Persist `CLEANUP_PENDING`, unlink only after it commits, and have restart reconciliation either mark deletion or safely report a verified missing file. | Requires `state.py`, a migration, `transcription.py`/`transcripts.py`, recovery runner, retention rules, ADR-012 revision, and injected crash/race tests. Adds stuck-intent and reconciliation authorization paths. It improves observability but cannot make unlink + SQLite exactly atomic. | **MEDIUM** |
| Defer automatic audio deletion | Retain the audio until an explicit authorized cleanup/reconciliation operation. | Changes retention/privacy/disk-pressure behavior and operational procedures; affects transcription policy and ADR-012. Does not affect TASK-016, ADR-008, or ADR-028. | **MEDIUM** |
| Retain current verified best-effort cleanup | Keep hash/root/symlink checks, one unlink attempt, CAS, and conflict diagnostics. | No production change; stale metadata remains possible in the narrow interval. Existing unit/integration race tests remain applicable. | **SMALL** |

**If accepted:** acceptance is limited to the stale `deleted_at` metadata that
can remain after a verified ephemeral-audio deletion in this exact final-CAS
interval. It does not permit deletion outside DATA, unverified deletion,
privacy/security exceptions, or any other cleanup behavior.

**If rejected:** current release remains blocked until a PO-authorized cleanup
state/reconciliation design is implemented and tested. It can make reconciliation
more automatic, but cannot promise strict atomicity between `unlink` and SQLite.

## Independence, evidence, and adversarial review

The windows are independent:

- Window 1 concerns an external/provider action versus local durable receipt.
- Window 2 concerns a rendered runtime filesystem output versus SQLite state.
- Window 3 concerns deletion of an ephemeral local input versus its SQLite
  deletion marker after the transcript is already committed.

An acceptance/rejection may therefore be recorded per window. It must not be an
all-or-nothing decision.

Relevant offline evidence reviewed for this package:

- `tests/integration/test_state_store.py` covers reservation ownership, lease
  expiry, retry, and verified-artifact recovery.
- `tests/integration/test_obsidian_sink.py` injects SQLite failure after a
  note replace and verifies retry reconciliation without losing the note.
- `tests/integration/test_whisper_provider.py` and
  `tests/unit/test_transcription_policy.py` cover the final-CAS conflict after
  deletion and its safe diagnostics.
- `tests/e2e/test_failure_recovery.py` checks restart recovery without duplicate
  outputs/provider calls in the covered offline flows.

Adversarial review conclusions:

- No fourth window was added; the three names and boundaries match the release
  blocker exactly.
- No numerical likelihood, strict exactly-once claim, provider qualification,
  operational authorization, TASK-016G authorization, scanner exception, or
  privacy/security waiver is implied.
- Window 1 explicitly retains conditional duplicate provider execution; it is
  not misdescribed as generic idempotency.
- Windows 2 and 3 retain their recovery burden and do not claim that a
  filesystem and SQLite form one transaction.
- The document does not alter TASK-016, ADR-008, ADR-028, BPE, frozen-task
  semantics, distribution scope, production source, tests, or dependencies.

## Product Owner decision and Window-1 remediation — 2026-08-31

### Finite decisions

- **Window 1 — Provider success → SQLite commit:** **REJECT / REQUIRE
  REMEDIATION.** The rejection applies only to an ambiguous externally visible
  paid/cloud Deep Analysis request; it is not an acceptance of any other crash
  window or a provider qualification.
- **Window 2 — File atomic replace → SQLite commit:** **ACCEPT** for the
  current personal/private/proprietary controlled source/wheel/sdist posture
  only. Its guarded Vault recovery behavior is unchanged.
- **Window 3 — Audio cleanup final CAS:** **ACCEPT** for the current
  personal/private/proprietary controlled posture only. Its unlink/CAS behavior
  is unchanged.

### Window 1 remediation status: COMPLETE

Migration `004_add_provider_dispatch_state.sql` and the repository-backed cloud
analysis path now persist this finite recovery protocol:

1. `NOT_DISPATCHED` — a reservation exists but no cloud dispatch intent is
   durable; expiry can safely be taken over.
2. `DISPATCH_INTENT_DURABLE` — the local transaction authorized one cloud
   dispatch immediately before transport.
3. `DISPATCHED_RESULT_UNKNOWN` — transport returned, but the one atomic SQLite
   transaction that registers artifacts, provider receipt, pipeline transition,
   and job success has not yet completed.
4. `SUCCESS_DURABLY_RECORDED` — that transaction committed; only this state is
   trusted as a completed provider result.
5. `FAILED_KNOWN` — an explicit provider refusal/permission response was
   recorded as a known non-success, distinct from uncertainty.
6. `AMBIGUOUS` — an intent/result-unknown call lost its lease or failed after
   intent. The provider call becomes `FAILED_FINAL` with a redacted,
   operator-visible `PROVIDER_UNAVAILABLE` diagnostic.

On restart, `INTENT`, `RESULT_UNKNOWN`, and legacy pre-protocol `PENDING`
records are never automatically redispatched. The v4 migration conservatively
backfills old `PENDING` rows as `AMBIGUOUS`; it preserves the row but does not
claim that a prior provider operation was absent. A matching cache/artifact
cannot promote `AMBIGUOUS` to success. Credentials are not resolved and the
Provider is not called when the ambiguous state is discovered.

**Exact residual risk after remediation:** one cloud provider operation can
still have succeeded while its local success receipt is absent after a crash.
The consequence is a single terminal, operator-visible incomplete item rather
than automatic duplicate request, repeat charge, or duplicate authorized
payload transmission. The current runtime deliberately offers no automatic
retry or automatic conversion to success; any manual resolution must use
separate operator/PO authorization and independently supplied provider-side
evidence. This is not a claim of global exactly-once semantics.

**New PO decision required for Window 1:** **NO.** The Product Owner rejected
automatic repetition of this exact ambiguity and the implemented protocol now
fails closed. A future live-provider qualification still needs its own
authorization and must validate the selected provider contract; it is not
authorized by this remediation.

## Historical decision-support table

### WINDOW 1

| Field | Decision support |
| --- | --- |
| NAME | Provider success → SQLite commit |
| IN ONE SENTENCE | A provider can finish one request before local SQLite records its receipt, so an expired retry can conditionally execute that request again. |
| CRASH BETWEEN | Provider returns success and SQLite commits artifacts/provider-call success/pipeline transition. |
| USER-VISIBLE RESULT | Processing can remain incomplete and later complete after recovery; a cloud account can have one extra authorized request. |
| DUPLICATE POSSIBLE | CONDITIONALLY YES |
| LOSS POSSIBLE | CONDITIONALLY YES — first response can be unavailable if not durably captured. |
| CORRUPTION POSSIBLE | NO committed SQLite corruption. |
| RECOVERY | PARTIAL — verified durable artifact recovery when available; otherwise authorized retry. |
| SEVERITY | MEDIUM |
| FUNDAMENTAL OR FIXABLE | Fundamental cross-provider/SQLite atomicity boundary; reducible with provider idempotency and stronger durable recovery. |
| COST TO REDUCE | LARGE |
| CODEX TECHNICAL RECOMMENDATION | REMEDIATE before qualifying a live paid/cloud Deep Analysis provider. |
| WHY | This is the only window that can conditionally repeat an external account-visible request and its authorized payload/cost. |
| PRODUCT OWNER DECISION | **REJECT / REQUIRE REMEDIATION — remediation COMPLETE; no automatic redispatch** |

### WINDOW 2

| Field | Decision support |
| --- | --- |
| NAME | File atomic replace → SQLite commit |
| IN ONE SENTENCE | A verified managed note/report can exist in the Vault before SQLite records it, leaving one item pending until guarded reconciliation. |
| CRASH BETWEEN | Successful atomic replace plus directory fsync and SQLite stage/report commit. |
| USER-VISIBLE RESULT | A note/report may appear while the application still says it is unfinished. |
| DUPLICATE POSSIBLE | NO |
| LOSS POSSIBLE | CONDITIONALLY YES — progress/bookkeeping can remain pending, while the final file is retained. |
| CORRUPTION POSSIBLE | CONDITIONALLY — temporary file/DB disagreement only; guarded validation prevents a partial DB transition or user-content overwrite. |
| RECOVERY | PARTIAL — retry reconciles a valid managed file; invalid/conflicting files require manual resolution. |
| SEVERITY | MEDIUM |
| FUNDAMENTAL OR FIXABLE | Fundamental filesystem/SQLite boundary; current guarded reconciliation can be extended but not made one transaction. |
| COST TO REDUCE | MEDIUM |
| CODEX TECHNICAL RECOMMENDATION | ACCEPT for the current controlled posture. |
| WHY | Existing replace/fsync/identity/user-region safeguards and retry evidence retain the file and prevent duplicate logical outputs; a journal adds complexity without strict atomicity. |
| PRODUCT OWNER DECISION | **ACCEPT — current controlled posture only** |

### WINDOW 3

| Field | Decision support |
| --- | --- |
| NAME | Audio cleanup final CAS |
| IN ONE SENTENCE | Ephemeral audio can be deleted before SQLite marks it deleted, leaving stale cleanup metadata after a crash or final-CAS race. |
| CRASH BETWEEN | Verified `unlink()` and SQLite `mark_artifact_deleted()` CAS commit. |
| USER-VISIBLE RESULT | The completed transcript remains; audio is absent as expected for cleanup, while diagnostics can show a stale index record. |
| DUPLICATE POSSIBLE | NO |
| LOSS POSSIBLE | CONDITIONALLY — original ephemeral audio cannot be reused for later debugging/retranscription. |
| CORRUPTION POSSIBLE | CONDITIONALLY — stale deletion metadata only, not transcript/pipeline corruption. |
| RECOVERY | MANUAL — verify completed transcript, identity/hash, and controlled-root absence before CAS reconciliation. |
| SEVERITY | LOW |
| FUNDAMENTAL OR FIXABLE | Fundamental unlink/SQLite boundary; a cleanup journal can improve reconciliation but cannot make it atomic. |
| COST TO REDUCE | MEDIUM |
| CODEX TECHNICAL RECOMMENDATION | ACCEPT for the current controlled posture. |
| WHY | The source audio is explicitly ephemeral, transcription is already committed, and current validation prevents deletion of an unverified or out-of-root file. |
| PRODUCT OWNER DECISION | **ACCEPT — current controlled posture only** |

## Overall technical recommendation

**ACCEPT SOME / REMEDIATE SOME.** Technically, retain the current guarded
filesystem and cleanup semantics for Windows 2 and 3, while requiring a
provider-specific idempotency/receipt and recovery design before any live paid
or cloud Deep Analysis provider is qualified. This is not a Product Owner
decision and does not authorize that remediation or any provider work.

## Completion statement

```text
AT-MOST-ONCE RESIDUAL RISK DECISION PACKAGE COMPLETE
EXACT RESIDUAL WINDOWS: 3
PRODUCT OWNER ACCEPTANCES FABRICATED: 0
PRODUCT OWNER DECISIONS: WINDOW 1 REJECT / REQUIRE REMEDIATION; WINDOWS 2 AND 3 ACCEPTED
WINDOW 1 REMEDIATION: COMPLETE; AMBIGUOUS EXTERNAL SUCCESS MUST NOT AUTO-REDISPATCH
PRODUCTION CHANGE: WINDOW 1 ONLY
CURRENT RELEASE: NO-GO
NEXT ACTION: OBTAIN A SEPARATE PO AUTHORIZATION IF A LIVE-PROVIDER QUALIFICATION PACKAGE IS TO BE RUN
PUSH: NO
TAG: NO
PUBLIC RELEASE: NO
```
