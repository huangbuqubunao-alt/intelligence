# TASK-016C Phase H2-C — Authoritative Scoring Lineage Authorization, Round 1

## Status, scope, and supersession

Status: **READY FOR H2-C AUTHORITATIVE SCORING LINEAGE AMENDMENT ROUND 1
INDEPENDENT REVIEW**.

This is documentation-only control-plane authorization. It authorizes neither
source/test/schema changes nor a migration, H2-C implementation, scoring rerun,
Phase I, ProviderCall identity changes, Artifact ownership changes, merge,
push, tag, rebase, reset, or squash.

Reuse decision: **DIRECT** — retain the SQLite repository, `jobs`, `videos`,
`artifacts.artifact_key`, global ProviderCall request-hash admission, exact
`get_artifact_by_key`, and standard-library SQLite support. No dependency is
added.

This Round 1 document supersedes the rejected Round 0 lineage decisions in
this file: rerun/predecessor CAS, cross-job same-G convergence, non-unique Job
artifact pointers, repair-only future lineage, and its corresponding migration
shape/tests. It also supersedes inconsistent portions of
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
Migration leaves all existing rows NULL, meaning only that the row predates the
lineage contract. A non-NULL unknown version fails closed; it never receives a
legacy fallback.

`scoring_success_provenance` has exactly two post-migration success literals:
`PRIMARY` and `REPAIR_H2C`. It is not set at Job creation. The legal matrix is:

| Job category | lineage version | provenance / artifact pointer | Video pointer | Reader result |
|---|---|---|---|---|
| historical successful PRIMARY | NULL | NULL / NULL | may be NULL | legacy branch allowed |
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

After a zero-row Job CAS, read `get_job(job_id)` once in the transaction and
classify in this exact order:

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

After a zero-row Video CAS, read the exact Video and classify in this order:

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
existing legacy PRIMARY selection behavior only to identify a historical
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
