# TASK-016C Phase H2-C — Authoritative Scoring Lineage Authorization, Round 6

## Status, scope, and supersession

Status: **READY FOR H2-C AUTHORITATIVE SCORING LINEAGE AMENDMENT ROUND 6
INDEPENDENT REVIEW**.

This is documentation-only control-plane authorization. It authorizes neither
source/test/schema changes nor a migration, H2-C implementation, scoring rerun,
Phase I, ProviderCall identity changes, Artifact ownership changes, merge,
push, tag, rebase, reset, or squash.

Reuse decision: **DIRECT** — retain the SQLite repository, `jobs`, `videos`,
`artifacts.artifact_key`, global ProviderCall request-hash admission, exact
`get_artifact_by_key`, and standard-library SQLite support. No dependency is
added.

Round 6 supersedes only Round 5's unknown-generation diagnostic detail: it is
the closed `H2C_REPLAY_INVALID:SCORING_LINEAGE_VERSION_INVALID` reason, not a
second top-level diagnostic family. It retains Round 5's supersession of Round
4's generic-reclaim tuple and unknown-generation terminal wording, Round 4's
supersession of Round 3's reclaim
return-value and generation-branch wording, Round 3's supersession of Round 2's over-broad pre-v2
interrupted/unleased recovery wording, Round 2's supersession of the rejected Round 1
NULL-generation/cutover and separate-connection CAS-read-back clauses, and
Round 1's supersession of
the rejected Round 0 rerun/predecessor CAS, cross-job same-G convergence,
non-unique Job artifact pointers, repair-only future lineage, and corresponding
migration shape/tests. It also supersedes inconsistent portions of
`TASK-016C-PHASE-H2C-AUTHORITATIVE-G-SCHEMA-AUTHORIZATION.md` and
`TASK-016C-PHASE-H2C-AUTHORIZATION.md` as stated below. Frozen H1, H2, H2-B,
P/R/J/E/S/G, Artifact ownership, ProviderCall identity, filesystem, stale-lease,
and Phase-G trusted-success contracts remain authoritative.

## 1. Audited executable workflow

| Flow | Durable input | Audited current behavior | Result |
|---|---|---|---|
| SCORING | Job `job_id`, `video_id`, stage/status | `PipelineJobPlanner` produces initial SCORING from `TRANSCRIPT_READY`; trusted completion moves the Video to `SCORED`. | One initial scoring success is the current executable model. |
| ANALYSIS | `video_id` | `ensure_next_job` creates a stage Job using only `video_id` and canonical scope; no predecessor is stored. | It needs a Video-rooted exact lineage. |
| NOTE | `video_id` | `note_stage` calls `_load_scoring(video_id)`, which currently uses `latest_artifact`. | The latest path cannot select repaired results. |
| WEEKLY | Video rows | Candidate selection begins from Videos and `_latest_weekly_artifact`. | It also lacks a scoring Job identity. |

`pipeline.py` re-fetches the Video and compares its current next stage with the
claimed Job target. A fresh SCORING Job after successful scoring does not reach
a new scoring handler: it is stale, or the `SCORED` low-value path advances to
`LOW_VALUE_READY`. `runtime.retry` filters candidates through that same planner
test. A raw repository retry of the *same interrupted Job* remains H0/H1
recovery; it is not a new scoring rerun.

H1 admission and Artifact registration close the purported convergence path:

1. H1 rejects a second PRIMARY dispatch when the global `provider_calls`
   `request_hash` for P is already occupied.
2. `_upsert_artifact_in_transaction` rejects an existing `artifact_key` whose
   `job_id` differs from the registering Job.

Thus two distinct Jobs cannot independently execute PRIMARY → H2-B → H2-C and
converge on the same G under frozen contracts. Multiple independent legitimate
SCORING writers for one active Video are not a supported normal race.

## 2. Selected durable root and final schema

The sole downstream authority root is:

```text
videos.authoritative_scoring_job_id
  -> jobs.job_id
  -> jobs.authoritative_scoring_artifact_key
  -> artifacts.artifact_key
```

The one future migration is exactly:

```text
src/youtube_intel/migrations/002_add_scoring_lineage.sql
```

It adds exactly these nullable columns:

```sql
ALTER TABLE videos ADD COLUMN authoritative_scoring_job_id TEXT NULL
    REFERENCES jobs(job_id) ON DELETE RESTRICT;

ALTER TABLE jobs ADD COLUMN authoritative_scoring_artifact_key TEXT NULL
    REFERENCES artifacts(artifact_key) ON DELETE RESTRICT;
ALTER TABLE jobs ADD COLUMN scoring_success_provenance TEXT NULL
    CHECK (scoring_success_provenance IS NULL
           OR scoring_success_provenance IN ('PRIMARY', 'REPAIR_H2C'));
ALTER TABLE jobs ADD COLUMN scoring_lineage_version TEXT NULL
    CHECK (scoring_lineage_version IS NULL
           OR scoring_lineage_version = 'task016c-scoring-lineage-v1');

CREATE UNIQUE INDEX uq_jobs_authoritative_scoring_artifact_key
    ON jobs(authoritative_scoring_artifact_key)
    WHERE authoritative_scoring_artifact_key IS NOT NULL;
CREATE UNIQUE INDEX uq_videos_authoritative_scoring_job_id
    ON videos(authoritative_scoring_job_id)
    WHERE authoritative_scoring_job_id IS NOT NULL;
```

No `expected_authoritative_scoring_job_id` column is authorized. No index on
provenance or lineage version is authorized: neither is a selector query. The
unique Video-pointer index is a defensive cardinality guard; the transaction
and reader still prove `job.video_id == video.video_id`, which no FK/index can
express. The unique Job-key index mechanically forbids cross-job Artifact
sharing. `artifacts.artifact_key` is already a legal unique FK parent. The
nullable SQLite `ADD COLUMN ... REFERENCES ... ON DELETE RESTRICT` operations
are supported by the audited SQLite versions; insertion order is Artifact,
then Job pointer, then Video pointer, so no deferrable FK is needed.

## 3. Lineage generation, provenance, and legality

The durable generation discriminator is exactly:

```text
jobs.scoring_lineage_version = 'task016c-scoring-lineage-v1'
```

The repository derives it at Job creation solely from a `VIDEO_STAGE` Job with
`target_stage == SCORING`; callers cannot submit a version. Every post-migration
SCORING Job receives v1 at insertion. ANALYSIS, NOTE, WEEKLY, and all other
non-SCORING Jobs receive NULL. A created SCORING Job's value never changes.
Migration leaves all existing rows NULL, meaning PRE-LINEAGE GENERATION whether
the historical Job is terminal or nonterminal; §11 freezes its recovery rules.
A non-NULL unknown version fails closed; it never receives a legacy fallback.

`scoring_success_provenance` has exactly two post-migration success literals:
`PRIMARY` and `REPAIR_H2C`. It is not set at Job creation. The legal matrix is:

| Job category | lineage version | provenance / artifact pointer | Video pointer | Reader result |
|---|---|---|---|---|
| pre-lineage successful PRIMARY | NULL | NULL / NULL | may be NULL | legacy branch allowed |
| pre-lineage live-active SCORING | NULL | NULL / NULL | NULL | may continue under its still-valid lease; no H2-C |
| pre-lineage expired SCORING recovery | NULL | NULL / NULL | NULL | H1 terminal `UNKNOWN_PROVIDER_STATE`; no scoring continuation |
| new RUNNING SCORING | v1 | NULL / NULL | NULL | normal pre-success |
| new FAILED or FAILED_FINAL SCORING | v1 | NULL / NULL | NULL | no scoring result |
| new successful PRIMARY | v1 | `PRIMARY` / `scoring/<P>/structured` | equals Job | valid lineage |
| new successful repair | v1 | `REPAIR_H2C` / `scoring/<P>/repair/<G>/structured` | equals Job | valid lineage |
| invalid | v1 or unknown | any missing/wrong/mismatched combination | any mismatch | fail closed |

In particular, a v1 SUCCEEDED Job with NULL provenance or pointer, a v1
FAILED Job with a result pointer/provenance, an unknown provenance/key grammar,
or a Video mismatch is corrupt. It must fail closed and never masquerade as a
historical row. A historical legacy row may enter the legacy reader only after
its associated scoring Job has been checked to have NULL lineage version.

## 4. PRIMARY and repair persistence

Future post-migration PRIMARY success uses the same additive bookkeeping:

```text
scoring_lineage_version = task016c-scoring-lineage-v1 (at creation)
scoring_success_provenance = PRIMARY
authoritative_scoring_artifact_key = scoring/<P>/structured
video.authoritative_scoring_job_id = current Job
```

Repair success writes `REPAIR_H2C` and the exact G-specific structured key.
Both write the key locally from the trusted Phase-G plan; no caller supplies a
scattered key, P, G, or provenance. This supersedes the Round 0 statement that
Phase F persistence is completely unchanged: frozen Phase-F scoring semantics,
P/request/finalizer bytes, ProviderCall semantics, and PRIMARY Artifact
paths/keys remain unchanged, while shared Phase-G completion gains additive
lineage bookkeeping for v1 PRIMARY Jobs.

## 5. First-success pointer and no scoring rerun

H2-C authorizes only this Video relation transition:

```text
NULL -> current successful initial SCORING job_id
```

There is no J1 → J2 update, expected-predecessor state, rerun transition,
Video invalidation, downstream invalidation, reanalysis, or re-note behavior.
Those require separate state-machine/product authorization. A non-NULL Video
pointer during a current-scope scoring persistence is not an ordinary race or
legitimate rerun; it is stale/duplicate/invariant failure and fails closed.

The conceptual Video CAS is exactly:

```sql
UPDATE videos
SET authoritative_scoring_job_id = :job_id
WHERE video_id = :video_id
  AND authoritative_scoring_job_id IS NULL
  AND pipeline_status = 'TRANSCRIPT_READY'
  AND pipeline_version = :pipeline_version;
```

It occurs before the existing `TRANSCRIPT_READY -> SCORED` Video update in the
same SQLite transaction. Failed work cannot move it. The scheduler/H1
exclusivity remains unchanged; a CAS conflict is defensive integrity handling,
not a normal concurrent winner/loser protocol.

## 6. Job pointer CAS, read-back, and conflict disposition

The Job pointer/provenance CAS is conceptually:

```sql
UPDATE jobs
SET authoritative_scoring_artifact_key = :key,
    scoring_success_provenance = :provenance
WHERE job_id = :job_id
  AND status = 'RUNNING'
  AND target_stage = 'SCORING'
  AND lease_owner = :owner
  AND lease_until > :now
  AND authoritative_scoring_artifact_key IS NULL
  AND scoring_success_provenance IS NULL;
```

Normal active success is NULL → intended key/provenance. Same-key handling is
only an already-committed idempotent/read path: Job is SUCCEEDED, the matching
provenance, Artifact/ProviderCall/Video graph, and success state are complete.
An active RUNNING Job that already contains either value is an invariant error,
not an alternate write. A differing key or provenance is
`H2CAuthoritativeGraphConflict`.

Round 2 §11.3 supersedes the following initial Job zero-row ordering with the
private same-connection tx-reader and complete field validation:

1. missing Job → raise `PipelineInterrupted`, no `fail_job`;
2. owner/lease no longer valid → `H2CStaleScoringLease`, frozen no-mutation
   pipeline return;
3. SUCCEEDED → exact same pointer/provenance/full graph is idempotent read;
   otherwise raise `H2CAuthoritativeGraphConflict` as committed corruption,
   with no mutation;
4. FAILED_FINAL → no persistence attempt; frozen stale/terminal return;
5. active owned Job with non-NULL differing key or provenance → active graph
   conflict;
6. any other Job state → raise `PipelineInterrupted`;
7. active owned NULL/NULL after a zero row → active integrity failure, detail
   `H2C_JOB_LINEAGE_CAS_UNEXPECTED`.

Round 2 §11.3 likewise supersedes this initial Video zero-row ordering with the
private same-connection tx-reader and complete field validation:

1. missing Video → raise `PipelineInterrupted`, no `fail_job`;
2. lost Job owner/lease → `H2CStaleScoringLease`;
3. pointer equals current Job and full committed graph/success agrees →
   idempotent read;
4. non-NULL pointer differs from current Job while ownership remains valid →
   active lineage conflict, detail `H2C_VIDEO_LINEAGE_CAS_CONFLICT`;
5. NULL pointer but non-`TRANSCRIPT_READY` status, mismatched pipeline version,
   or other failed expected-state predicate while ownership remains valid →
   active integrity failure, detail `H2C_VIDEO_LINEAGE_CAS_UNEXPECTED`;
6. otherwise → the same unexpected-state active integrity failure.

For an active owned graph/integrity conflict: roll back the current transaction;
re-prove ownership; perform exactly one `fail_job` with
`ErrorCode.TRUST_INTEGRITY_INVALID`, `retry_at=None`, `FAILED_FINAL`, and the
specified detail (`H2C_AUTHORITATIVE_GRAPH_CONFLICT`,
`H2C_VIDEO_LINEAGE_CAS_CONFLICT`, or `H2C_JOB_LINEAGE_CAS_UNEXPECTED`);
return `StageDisposition.TERMINAL` only after read-back confirms FAILED_FINAL.
If re-proof loses the lease, use `H2CStaleScoringLease` instead. A committed
SUCCEEDED mismatch raises `H2CAuthoritativeGraphConflict` fail-closed with no
`fail_job` and no generic failure handling. `H2CStaleScoringLease` is only
lease/ownership loss, never graph conflict.

## 7. Atomic persistence, ownership, and crash rule

For repaired success the one Phase-G transaction is:

```text
BEGIN IMMEDIATE
-> revalidate Job / owner / RUNNING-SCORING lease and Video initial state
-> validate the intended trusted graph
-> reserve R/J ProviderCalls
-> insert the raw and structured Artifact rows; complete R/J ProviderCalls
-> CAS the Job structured-key pointer and REPAIR_H2C provenance
-> CAS Video NULL -> current Job
-> apply Video score/state and Job SUCCEEDED transition
-> COMMIT
```

PRIMARY uses the identical ordering with its PRIMARY key/provenance. The
relation, Artifact rows, ProviderCalls, Video state, and success commit
together. Before COMMIT, filesystem material may be an orphan but has no
durable lineage and no authority. After COMMIT, all are visible together. A
second Job cannot reuse the R/J evidence, Artifact row, or pointer: H1 and
Artifact ownership reject it, and the unique key index is an additional guard.
This is not Phase-I cache reuse, and H2-C authorizes no cache/search/resume.

## 8. Reader, downstream, and reporting contract

The scoring read layer in `src/youtube_intel/scoring.py` is the only scoring
selector/verifier and returns the single conceptual interface:

```text
VerifiedScoringRead(scoring_outcome, video_id, scoring_job_id,
                    scoring_success_provenance)
```

For a Video with a non-NULL authority pointer, it fetches the exact Job and
classifies **first** on `scoring_lineage_version`: v1 takes the exact lineage
branch, NULL/unknown is malformed for a pointer and fails closed. The v1 branch
requires the legality matrix, exact `get_artifact_by_key(structured_key)`, key
grammar, same Video/Job ownership, exact derived raw key, exact raw lookup,
E/S validation, R/J exact request-hash lookup, and G recomputation from the
frozen identity. No latest, scan, P-only lookup, cache, or heuristic is allowed.

For a Video with no authority pointer, the compatibility branch may use the
existing legacy PRIMARY selection behavior only to identify a pre-lineage
candidate; before parsing it, the selected producing SCORING Job must be read
and must have `scoring_lineage_version IS NULL`. A v1/unknown/malformed row
rejects rather than falling through. Thus classification is version-first once
the exact Job is reached, and no new lineage result can downgrade to legacy.

ANALYSIS and NOTE obtain `Video -> exact scoring Job -> exact Artifact` at
execution through this layer; they do not gain a predecessor column. Weekly
does the same per Video. This is current-at-execution semantics, but H2-C
introduces no pointer replacement, so normal v1 Videos have one authority.
Reporting receives only `VerifiedScoringRead` plus already verified report
inputs. It never queries repaired Artifacts/raw/ProviderCalls, selects G, or
verifies a repaired graph. This remains the sole reporting contract and
supersedes H2-C §12.1's repository-accessor/raw-graph reporting clause and
§13.5 item 5.

## 9. Migration/version compatibility and future implementation scope

Migration 002 advances `PRAGMA user_version` from 1 to 2 under the existing
ordered migration/checksum machinery. `state.py::_load_migrations()` must load
001 then 002. `runtime.py::_database_check` must accept exactly version 2.
The audited production schema-version consumers are those two locations. The
future test fixtures/assertions that name `001_initial.sql`, expected migration
counts/columns, or version 1 (notably state-store and operations integration
tests) must be updated coherently.

Normal business runtime bootstrap calls repository initialization and therefore
migrates an old valid v1 DB to v2 before operation. The read-only doctor
`_database_check` does not migrate: a v1 DB reports the existing sanitized
invalid-database result until a normal initializing startup has upgraded it.
Version 0, greater than 2, or malformed migration history remains fail closed.

After independent approval, exact future implementation scope is:

```text
src/youtube_intel/migrations/002_add_scoring_lineage.sql
src/youtube_intel/state.py
src/youtube_intel/jobs.py
src/youtube_intel/scoring.py
src/youtube_intel/runtime.py  (_database_check and schema consumers included)
src/youtube_intel/pipeline.py
src/youtube_intel/reporting.py
```

`scoring_admission.py` is explicitly excluded: it remains the frozen H1 guard.

## 10. Required future tests and discretion closure

Future tests must prove:

1. v1→v2 upgrade, fresh v2, final columns/FKs/CHECKs/partial unique indexes,
   exact user-version/history, doctor v2 acceptance, and unsupported versions;
2. historical NULL rows, v1-at-new-SCORING creation, NULL for non-SCORING,
   caller non-control, and immutable same-Job recovery;
3. legacy-only NULL branch; v1 SUCCEEDED NULL/missing/wrong lineage rejection;
   unknown version rejection; no v1 downgrade;
4. new PRIMARY `PRIMARY`/P-key/Video lineage and Phase-F bytes/path/request/
   finalizer regression; new repair `REPAIR_H2C`/P-G key/Video lineage;
5. Job and Video NULL→exact-key/Job CAS, all read-back classifications,
   same committed graph idempotency, active and committed conflict paths;
6. planner/pipeline non-authorization of a fresh scored-Video SCORING Job, no
   J1→J2 replacement, and no downstream invalidation;
7. H1 denial of a second same-P Job, immutable Artifact job ownership, unique
   pointer non-sharing, and no ProviderCall/Artifact execution shortcut;
8. exact analysis/note/weekly Video lineage, no repaired latest path, one
   `VerifiedScoringRead` reporting interface, and no reporting graph selection;
   and
9. pre-commit orphan invisibility and post-commit complete lineage visibility.

The implementation executor has no discretion about reruns, predecessor state,
cross-job sharing, generation/version literal, legacy discrimination, PRIMARY
bookkeeping, pointer CAS/read-back, terminal details, migration filename/v2
consumers, index uniqueness, reader root, reporting interface, or Phase-I
boundary. Any departure is **DECISION NEEDED**.

## 11. Round 2 — migration cutover and transaction-local CAS diagnosis

### 11.1 Pre-lineage generation is a lifetime property

At the v1→v2 migration, every existing row retains
`scoring_lineage_version IS NULL`. NULL means **PRE-LINEAGE GENERATION**, not
merely a completed historical legacy result. Migration performs no data UPDATE,
and no historical Job may be changed to
`task016c-scoring-lineage-v1` later. The v1 marker is assigned only by
post-migration SCORING Job creation and remains immutable.

The complete cutover matrix is:

| Pre-v2 SCORING durable state | Post-migration classification and rule |
|---|---|
| SUCCEEDED PRIMARY | NULL version/provenance/key; valid pre-lineage legacy success and legacy reader candidate. |
| FAILED_FINAL or other terminal | NULL version/provenance/key; remains terminal under existing recovery rules. |
| live-active RUNNING with valid owner and `lease_until > now` | NULL version/provenance/key; **LIVE CONTINUATION** of existing execution is allowed, never H2-C. |
| H1 expired-SCORING predicate: `RUNNING AND lease_until <= now` | NULL version/provenance/key; **EXPIRED/INTERRUPTED H1 RECOVERY** terminalizes it, never H2-C. |
| malformed or unknown historical state | NULL version is not an upgrade capability; existing recovery fails closed. |

If a pre-v2 live-active Job continues under its still-valid lease and completes
through already-authorized PRIMARY, it uses the pre-lineage Phase-F/Phase-G
persistence contract: P-only Artifact behavior and existing ProviderCalls, with
no provenance, Job Artifact pointer, Video pointer, or version mutation. Its
later SUCCEEDED row remains a valid pre-lineage legacy reader candidate. An H1
expired-SCORING recovery writes no lineage fields and cannot complete PRIMARY.

After H2-B PASS, runtime reaches the **generation decision point** before the
v1-only H2-C entry gate: exact v1 may continue toward H2-C; NULL is
pre-lineage and takes the compatibility terminal; an unknown non-NULL version
terminalizes as §14 freezes. NULL therefore never enters H2-C; no migration-time, recovery-
time, or caller opt-in upgrade exists. A NULL **live-active** pre-v2 Job at
that decision point takes the frozen build-without-H2-C terminal route:
`ErrorCode.CAPABILITY_UNAVAILABLE`, detail `H2B_PASS_AWAITING_H2C`,
`retry_at=None`, exactly one `fail_job`, `FAILED_FINAL`, and
`StageDisposition.TERMINAL`. It performs no H2-C replay, persistence, or
additional external contact; any REPAIR/REPAIR_JUDGE admission and contact was
already consumed inside the frozen H2-B PASS path. An unknown non-NULL version
uses the §14 integrity terminal and also cannot enter H2-C.

This supersedes any earlier phrase that equated every NULL-version row with an
already-completed historical success. New v2 SCORING Jobs still receive v1 at
creation and must satisfy all v1 lineage rules.

### 11.2 Exact transaction-local readers

`get_job()` and `get_video()` open new connections and are expressly forbidden
between a failed lineage CAS and its classification. Future `state.py` adds
only these private repository helpers, which reuse the existing row decoders:

```python
def _read_job_in_transaction(
    self, connection: sqlite3.Connection, job_id: str
) -> JobRecord | None:
    row = connection.execute(
        "SELECT * FROM jobs WHERE job_id = :job_id", {"job_id": job_id}
    ).fetchone()
    return None if row is None else self._job_from_row(row)

def _read_video_in_transaction(
    self, connection: sqlite3.Connection, video_id: str
) -> VideoRecord | None:
    row = connection.execute(
        "SELECT * FROM videos WHERE video_id = :video_id", {"video_id": video_id}
    ).fetchone()
    return None if row is None else self._video_from_row(row)
```

They are private, read-only state helpers, not caller-facing trust/selection
APIs. They use the exact `sqlite3.Connection` whose `BEGIN IMMEDIATE`
transaction executed the CAS, have no side effects, and observe that coherent
transactional snapshot. No new connection or public repository surface is
authorized.

The Job tx-read must validate, before pointer/provenance classification:
`job_id`; `job_type == VIDEO_STAGE`; `target_stage == SCORING`; exact
`video_id`; exact `pipeline_version`; exact expected generation (v1 for the
new lineage path; NULL only when handling the explicitly pre-lineage path);
`status`; `lease_owner`; `lease_until` under frozen H0/H1 time semantics;
`authoritative_scoring_artifact_key`; and `scoring_success_provenance`.
The Video tx-read must validate `video_id`, `pipeline_status`, exact
`pipeline_version`, and `authoritative_scoring_job_id`, plus
`job.video_id == video.video_id`. No additional Video immutable field is part
of the Phase-G transition contract.

### 11.3 CAS predicates and exact zero-row classification

The v1 Job CAS additionally binds all validated immutable lineage identity
fields so a zero row has a closed diagnosis:

```sql
UPDATE jobs
SET authoritative_scoring_artifact_key = :key,
    scoring_success_provenance = :provenance
WHERE job_id = :job_id
  AND job_type = 'VIDEO_STAGE'
  AND target_stage = 'SCORING'
  AND video_id = :video_id
  AND pipeline_version = :pipeline_version
  AND scoring_lineage_version = 'task016c-scoring-lineage-v1'
  AND status = 'RUNNING'
  AND lease_owner = :owner
  AND lease_until > :now
  AND authoritative_scoring_artifact_key IS NULL
  AND scoring_success_provenance IS NULL;
```

After a zero-row Job CAS, read the Job exactly once with
`_read_job_in_transaction` and classify in this order:

1. missing → `PipelineInterrupted`;
2. malformed/mismatched immutable identity (`job_type`, stage, video,
   pipeline version, generation) → if still RUNNING and validly owned, rollback
   then terminalize `TRUST_INTEGRITY_INVALID` with
   `H2C_JOB_LINEAGE_CAS_UNEXPECTED`; otherwise use stale lease or
   `PipelineInterrupted` as the now-observed state requires;
3. if still RUNNING but owner/lease is invalid → `H2CStaleScoringLease`;
4. SUCCEEDED with exact intended pointer/provenance and complete Job/Video/
   Artifact/ProviderCall graph → idempotent success;
5. SUCCEEDED with any pointer/provenance/graph mismatch →
   `H2CAuthoritativeGraphConflict`, no mutation;
6. FAILED_FINAL → no persistence; existing terminal return/interrupt behavior;
7. expected active RUNNING with non-NULL differing pointer or provenance →
   active graph conflict, terminal detail `H2C_AUTHORITATIVE_GRAPH_CONFLICT`;
8. expected active RUNNING with exact-but-prepopulated pointer/provenance →
   `H2C_JOB_LINEAGE_CAS_UNEXPECTED`, unless it was already classified as the
   complete SUCCEEDED idempotent case;
9. expected active RUNNING with NULL pointer/provenance → identify the failed
   identity/status/owner/lease predicate from the tx row and route to that
   preceding exact classification; and
10. any other observed state → `PipelineInterrupted`, unless it remains an
    active-owned invariant failure, which terminalizes with the same Job
    unexpected detail.

The Video CAS remains exactly its first-success predicate from §5. After its
zero row, read the Video exactly once through
`_read_video_in_transaction`, reuse the tx-local Job row for lease/identity,
and classify in this order:

1. missing Video → `PipelineInterrupted`;
2. invalid current Job owner/lease → `H2CStaleScoringLease`;
3. pipeline-version mismatch → if the Job is still validly owned v1 RUNNING,
   rollback then terminalize `TRUST_INTEGRITY_INVALID` with
   `H2C_VIDEO_LINEAGE_CAS_UNEXPECTED`; otherwise stale/interrupted according
   to the tx Job state;
4. non-`TRANSCRIPT_READY` status → only `SCORED` plus current Job pointer,
   SUCCEEDED Job, and complete graph is idempotent; every other active-owned
   case terminalizes with `H2C_VIDEO_LINEAGE_CAS_UNEXPECTED`, otherwise stale/
   interrupted;
5. current Job pointer plus complete committed graph → idempotent success;
6. non-NULL pointer to another Job → active-owned terminal
   `TRUST_INTEGRITY_INVALID`, detail `H2C_VIDEO_LINEAGE_CAS_CONFLICT`;
7. NULL pointer, `TRANSCRIPT_READY`, and exact pipeline version with a zero row
   means no CAS predicate remains: terminalize the active-owned integrity
   failure with `H2C_VIDEO_LINEAGE_CAS_UNEXPECTED`.

### 11.4 Rollback, reader, version, and test closure

Both classifications occur while the original `BEGIN IMMEDIATE` remains active.
For an active-owned integrity finding, classify with tx-local reads, roll back,
then re-prove owner/lease through authoritative repository state. Only if that
re-proof succeeds may one separate `fail_job` write
`TRUST_INTEGRITY_INVALID`, `retry_at=None`, `FAILED_FINAL`, and the frozen
detail; if it fails, raise/return `H2CStaleScoringLease` with no `fail_job`.
`fail_job` is never called inside the rolled-back persistence transaction.

The pointerless legacy compatibility path must load the selected Artifact's
`job_id`, then its Job, and require `target_stage == SCORING` and a NULL
generation. Thus both completed historical and pre-v2 live-active Jobs that
later complete PRIMARY are intentionally readable; an H1 expired-SCORING
terminal recovery has no scoring result. A new v1 result or corruption cannot
downgrade. Migration 002 still performs no historical row rewrite and advances
`user_version` to 2; Round 1's `_database_check` v2 policy is unchanged.

Future tests add: every cutover state in §11.1; no historical version upgrade;
pre-v2 live-active PRIMARY continuation/read; pre-v2 live-active H2-B PASS
exact capability terminal; expired-SCORING H1 terminal recovery; new v2
creation; same-connection/no-public-reader Job and Video diagnosis; every
listed immutable/lease/status/pointer/provenance predicate; classification
before rollback; rollback before `fail_job`; post-rollback re-proof; and no
legacy downgrade for v1 corruption. The future file set is unchanged, with
`state.py` explicitly including the two private readers and tx-local diagnostics.

These cutover, reader, ordering, and diagnostic-detail decisions are closed.
Any deviation is **DECISION NEEDED**.

## 12. Round 3 — live continuation versus expired H1 recovery

Round 3 supersedes only the over-broad recovery wording in §3 and §11.1–11.4.
It makes no change to the Round-2 schema, generation, CAS, transaction-local
reader, reader-selection, reporting, or Phase-I decisions.

**LIVE CONTINUATION** is a pre-v2 SCORING Job that remains `RUNNING`, has its
current runtime owner, and has `lease_until > now` under frozen H1 semantics.
It is continuation of already-running execution, not lease-expiry recovery. It
retains NULL generation forever. It may complete PRIMARY through the legacy
Phase-F/Phase-G path; if its H2-B PASS would require H2-C, it instead uses the
already-frozen `CAPABILITY_UNAVAILABLE` / `H2B_PASS_AWAITING_H2C` /
`retry_at=None` / one `fail_job` / `FAILED_FINAL` /
`StageDisposition.TERMINAL` path. H2-C remains unavailable.

**EXPIRED/INTERRUPTED H1 RECOVERY** has the exact existing reclaim predicate:

```text
jobs.status == RUNNING AND jobs.lease_until <= now
```

This is the complete frozen predicate for the terminal recovery discussed here.
The schema itself requires every RUNNING Job to have non-NULL `lease_owner` and
`lease_until`; therefore “unleased RUNNING” is not a second normal H1 category.
Owner mismatch, missing Job, or a still-unexpired lease are governed by their
existing H1/claim paths and are not broadened by this lineage authorization.

For an expired SCORING Job, `reclaim_expired_jobs()` performs the existing H1
terminal recovery in its reclaim transaction: it records
`UNKNOWN_PROVIDER_STATE`, exact message
`scoring provider outcome is unknown after lease expiry`, JobAttempt outcome
`FAILED_FINAL`, Job status `FAILED_FINAL`, `available_at=now`, clears owner and
lease, and sets `finished_at=now`. It has no `retry_at` parameter or value and
does not call `fail_job`, so its `fail_job` count is zero. The generic method
returns after the reclaim transaction commits a `tuple[JobRecord, ...]` with
one saved durable post-reclaim JobRecord for every expired RUNNING row selected
by that invocation, or `()` when none are selected; it never returns a
`StageDisposition`, single JobRecord, iterator, or mutable row. Only the
SCORING element has the terminal semantics in this paragraph; non-SCORING
elements retain their existing reclaim behavior. It releases terminal H1
admission after commit for terminal scoring elements.

This terminal recovery is not executable continuation: it dispatches no
PRIMARY, performs no H2-B continuation, reaches no generation decision point,
and
consumes no REPAIR or REPAIR_JUDGE admission. It writes no lineage version,
provenance, Job Artifact pointer, or Video lineage; its generation remains NULL
forever. Consequently it cannot produce a scoring success or a legacy reader
candidate.

Required cutover tests distinguish: live-valid-lease continuation without v1;
its legacy PRIMARY success; its H2-B capability terminal; the exact expired
predicate and UNKNOWN_PROVIDER_STATE terminal record; no PRIMARY/H2-B/H2-C/
lineage mutation after expiry; and focused owner-mismatch/unexpired-lease claim
tests retaining their existing H1 classifications. All Round-2 transaction-local
Job/Video CAS tests remain unchanged.

The executor has no discretion over live continuation, expired recovery,
their separating predicate, or their success/terminal outcomes. Any deviation
is **DECISION NEEDED**.

## 13. Round 4 — reclaim tuple and generation decision branch

Round 4 changes no Round-3 reclaim predicate, direct terminal mutation,
detail, lease semantics, CAS/tx-reader rule, or lineage policy. The exact
`reclaim_expired_jobs()` return contract is `tuple[JobRecord, ...]` after its
reclaim transaction commits. Each element is the saved durable post-reclaim
record for one row reclaimed by that call; one row yields a one-element tuple,
multiple rows yield one element per row in the existing stable reclaim order,
and zero rows yield `()`. Returned records are committed terminal records for
expired SCORING rows, never `StageDisposition`, an iterator, a mutable live
row, or a single unwrapped JobRecord.

The exact post-H2-B-PASS branch is:

```text
H2-B validated PASS
  -> generation decision point
     -> version == task016c-scoring-lineage-v1: may enter v1-only H2-C entry gate
     -> version IS NULL: pre-lineage compatibility terminal; no H2-C entry
     -> other non-NULL version: TRUST_INTEGRITY_INVALID terminal; no H2-C entry or legacy fallback
```

For a live NULL-generation Job, the decision point deterministically executes
the frozen `CAPABILITY_UNAVAILABLE`, `H2B_PASS_AWAITING_H2C`, `retry_at=None`,
one-`fail_job`, `FAILED_FINAL`, `StageDisposition.TERMINAL` route. It starts no
H2-C replay, consumes no H2-C REPAIR/REPAIR_JUDGE admission, performs no H2-C
provider/Judge work, and persists no repair result. It reaches the generation
decision point but never reaches or passes the H2-C entry gate. Only a v1 Job
may reach that entry gate. Unknown non-NULL generation fails closed under the
existing lineage-version policy; it is not treated as the NULL capability path.

Future tests add only: exact tuple type; one/multiple/zero reclaimed rows;
records reflecting post-commit state; no `StageDisposition`; NULL at
the decision point with no H2-C entry and the exact capability terminal; v1
entry eligibility; and unknown-version fail-closed/no-entry behavior. All
Round-3 tests remain unchanged.

The executor has no discretion over tuple timing/cardinality, generation
classification location, generation allowed to enter H2-C, NULL terminal path,
or unknown-version behavior. Any deviation is **DECISION NEEDED**.

## 14. Round 5 — generic reclaim tuple and invalid-generation terminal

Round 5 changes no reclaim query, ordering, commit timing, SCORING reclaim
branch, NULL-generation branch, or prior CAS/schema decision. The general
`reclaim_expired_jobs()` tuple contains exactly one committed post-reclaim
`JobRecord` for each expired RUNNING row selected by its existing query, in
`lease_until, created_at, job_id` order. It is heterogeneous: a reclaimed
SCORING row has the frozen `UNKNOWN_PROVIDER_STATE` / `FAILED_FINAL` state,
while a non-SCORING row preserves its existing reclaim outcome (including
`RETRY_PENDING` / `LEASE_EXPIRED` where current state rules apply). The generic
tuple must never be described as only terminal, SCORING, UNKNOWN, or
FAILED_FINAL records. Zero/one/N reclaimed rows return `()`, a one-element
tuple, or N ordered elements respectively, after commit.

At the post-H2-B-PASS generation decision point, the exact branch table is:

| `scoring_lineage_version` | Classification | H2-C entry | Terminal result |
|---|---|---|---|
| NULL | known pre-lineage | no | `CAPABILITY_UNAVAILABLE`, `H2B_PASS_AWAITING_H2C`, `retry_at=None`, `FAILED_FINAL`, `TERMINAL` |
| `task016c-scoring-lineage-v1` | supported | may proceed to the v1 H2-C entry boundary | no generation-only terminal |
| any other non-NULL value | invalid lineage generation | no | `TRUST_INTEGRITY_INVALID`, `H2C_REPLAY_INVALID:SCORING_LINEAGE_VERSION_INVALID`, `retry_at=None`, `FAILED_FINAL`, `TERMINAL` |

The invalid-generation terminalization uses exactly one owner-authoritative
active-job `fail_job` through the existing H2-C integrity-failure mechanism.
It requires the current runtime's still-valid owner/lease. If that proof is
lost, it follows the already-frozen `H2CStaleScoringLease`/stale-interrupted
path with no stale mutation. Invalid generation has no legacy fallback, H2-C
entry, REPAIR admission, REPAIR_JUDGE admission, H2-C replay/provider/Judge
work, repair persistence, or repair-lineage persistence. The validated H2-B
PASS that precedes this decision remains H2-B work; it is not retroactively
classified as H2-C activity.

Future tests add: one mixed reclaim call containing expired SCORING and
non-SCORING rows, ordered tuple contents and committed states, plus the
SCORING/non-SCORING distinction; an unknown non-NULL generation after validated
H2-B PASS with the exact integrity terminal and no H2-C/legacy/repair effects;
and a lost-owner/lease variant proving no stale `fail_job`. All earlier test
requirements remain unchanged.

The executor has no discretion over generic tuple content, non-SCORING reclaim
description, invalid-generation terminal fields, H2-C exclusion, or stale-owner
handling. Any deviation is **DECISION NEEDED**.

## 15. Round 6 — closed unknown-generation diagnostic

At the generation decision point immediately after validated H2-B PASS, an
unknown generation means exactly `scoring_lineage_version IS NOT NULL AND
scoring_lineage_version != "task016c-scoring-lineage-v1"`. It is an
H2-C pre-entry trust-integrity incompatibility: the persisted SCORING Job claims
a non-NULL generation not recognized by the authorized scoring-lineage
contract. It is neither a schema-migration failure, capability absence,
provider/Judge failure, language failure, nor stale lease.

Its complete terminal mapping is one owner-authoritative `fail_job` with
`ErrorCode.TRUST_INTEGRITY_INVALID`, detail exactly
`H2C_REPLAY_INVALID:SCORING_LINEAGE_VERSION_INVALID`, `retry_at=None`,
`FAILED_FINAL`, and `StageDisposition.TERMINAL`. The primary H2-C authorization
defines `H2C_REPLAY_INVALID:<REASON>` as the one closed diagnostic family for
both replay reasons and explicitly authorized pre-entry H2-C trust-integrity
reasons. `SCORING_LINEAGE_VERSION_INVALID` is its sole authorized pre-entry
reason; no arbitrary `H2C_*` detail or implementation-defined reason is
permitted. The former unqualified
`H2C_SCORING_LINEAGE_VERSION_INVALID` detail is unauthorized and must not be
emitted.

The runtime must still hold the valid owner/lease required by the frozen active
integrity-failure path before terminalizing. If that authority is lost, it takes
the existing `H2CStaleScoringLease`/stale-interrupted path and performs no
stale `fail_job`. This branch never enters H2-C, never falls back to legacy,
and performs no post-decision REPAIR or REPAIR_JUDGE admission, H2-C replay,
provider/Judge work, repair persistence, or repair-lineage persistence. The
validated preceding H2-B PASS remains H2-B work.

The generation table is therefore closed: NULL is the unchanged pre-lineage
`CAPABILITY_UNAVAILABLE` / `H2B_PASS_AWAITING_H2C` terminal; v1 has no
generation-only error and may proceed to the H2-C entry boundary; every other
non-NULL value takes the exact Round 6 integrity terminal above. Future tests
must assert the exact qualified detail, closed reason-set membership, absence
of the old unqualified detail and arbitrary unknown reasons, and the existing
lost-owner no-stale-`fail_job` behavior. NULL and v1 generation tests remain
unchanged.

Round 6 changes no reclaim tuple, H1 reclaim, tx-local/CAS, migration/schema,
rerun, cross-job, reporting, or Phase-I decision. The executor has no
discretion over diagnostic family, reason literal, closed-set membership, or
the pre-entry meaning of this reason. Any deviation is **DECISION NEEDED**.
