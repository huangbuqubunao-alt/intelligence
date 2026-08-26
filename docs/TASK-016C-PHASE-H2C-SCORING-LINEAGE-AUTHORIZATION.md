# TASK-016C Phase H2-C — Authoritative Scoring Lineage Authorization

## Status and scope

Status: **READY FOR H2-C AUTHORITATIVE SCORING LINEAGE INDEPENDENT REVIEW**.

This is documentation-only control-plane authorization. It resolves the
downstream reachability, repair discrimination, cross-job ownership, reporting,
and graph-conflict gaps in the job-local selector authorization. It authorizes
no source or test change, migration, H2-C implementation, Phase I work, merge,
push, tag, rebase, reset, or squash.

Reuse decision: **DIRECT** — retain the existing SQLite repository, Job and
Artifact identities, exact `get_artifact_by_key`, and standard-library SQLite
support. No dependency or third-party component is added.

This document supersedes the authoritative-selection portions of
`TASK-016C-PHASE-H2C-AUTHORITATIVE-G-SCHEMA-AUTHORIZATION.md` where they are
inconsistent with the lineage below. Frozen P/R/J/E/S/G, path, filesystem,
H2-C replay, and parent H2/H2-B contracts remain unchanged.

## 1. Current workflow audit

| Flow | Durable identifiers now | Proven downstream gap |
|---|---|---|
| SCORING | `jobs.job_id`, `video_id`, target stage/status; raw/structured Artifacts carry `job_id`; ProviderCalls retain `request_hash` and raw Artifact ID | A scoring Artifact identifies its producer Job, but neither the Video nor a successor knows which scoring Job is authoritative. |
| ANALYSIS | New `VIDEO_STAGE/ANALYSIS` Job has its own `job_id`, `video_id`, stage/status; its ProviderCall request hash and Artifacts are analysis-only | `PipelineJobPlanner.ensure_next_job(video_id)` creates it with no predecessor. It cannot reach a score Job without a new relation. |
| NOTE | New `VIDEO_STAGE/NOTE_WRITE` Job has its own `job_id`, `video_id`, stage/status; the note Artifact carries that note Job only | `note_stage` calls `_load_scoring(video.video_id)`, which calls `latest_artifact(video_id, SCORING_STRUCTURED)`. |
| WEEKLY | `reports.report_id` has period identity but no Video or predecessor Job; the report flow begins from `videos` and passes a selected score Artifact to `WeeklyReportService` | `_latest_weekly_artifact` orders `SCORING_STRUCTURED` by creation time. It has no scoring `job_id`. |

`jobs.py` creates all video-stage Jobs with `video_id` and canonical
`scope_key=video:<video_id>:<stage>` only. `state.py` stores no parent job
identifier. `pipeline.py` re-fetches the Video at execution. These code paths,
not merely documentation, prove that a job-only Artifact key cannot be reached
by current analysis, note, or weekly consumers without forbidden ordering.

## 2. Options evaluated and selected root

| Option | Decision | Reason |
|---|---|---|
| A — `videos.authoritative_scoring_job_id` | **Selected** | All current downstream flows already have a durable `video_id`; one exact hop reaches the authoritative scoring Job. |
| B — downstream `source_scoring_job_id` only | Rejected | Would require propagation into ANALYSIS and NOTE Jobs and still leaves weekly reporting without a root. |
| C — video pointer plus optional downstream pointer | Rejected for current scope | The video pointer already gives the required execution-time lineage. A snapshot relation is not needed for existing flows. |
| D — dedicated lineage table | Rejected | It duplicates a nullable Video FK plus a nullable Job key and adds no necessary history capability. |

The single current downstream authority root is therefore the Video:

```text
videos.authoritative_scoring_job_id
  -> jobs.job_id
  -> jobs.authoritative_scoring_artifact_key
  -> artifacts.artifact_key
```

No reader may substitute job/artifact timestamp, artifact enumeration, a
directory scan, P-only lookup, cache, or heuristic for any hop.

## 3. Final durable schema and NULL semantics

The one future migration is exactly:

```text
src/youtube_intel/migrations/002_add_h2c_scoring_lineage.sql
```

It adds exactly these columns:

```sql
ALTER TABLE jobs ADD COLUMN authoritative_scoring_artifact_key TEXT NULL
    REFERENCES artifacts(artifact_key) ON DELETE RESTRICT;
ALTER TABLE jobs ADD COLUMN scoring_success_provenance TEXT NULL
    CHECK (scoring_success_provenance IS NULL
           OR scoring_success_provenance IN ('PRIMARY', 'REPAIR_H2C'));
ALTER TABLE jobs ADD COLUMN expected_authoritative_scoring_job_id TEXT NULL
    REFERENCES jobs(job_id) ON DELETE RESTRICT;

ALTER TABLE videos ADD COLUMN authoritative_scoring_job_id TEXT NULL
    REFERENCES jobs(job_id) ON DELETE RESTRICT;

CREATE INDEX idx_jobs_authoritative_scoring_artifact_key
    ON jobs(authoritative_scoring_artifact_key)
    WHERE authoritative_scoring_artifact_key IS NOT NULL;
CREATE INDEX idx_jobs_expected_authoritative_scoring_job_id
    ON jobs(expected_authoritative_scoring_job_id)
    WHERE expected_authoritative_scoring_job_id IS NOT NULL;
CREATE INDEX idx_videos_authoritative_scoring_job_id
    ON videos(authoritative_scoring_job_id)
    WHERE authoritative_scoring_job_id IS NOT NULL;
```

SQLite accepts these nullable `ALTER TABLE ... ADD COLUMN ... REFERENCES`
operations in the repository's verified system/Python SQLite versions (3.51.0
and 3.53.2). `jobs` exists before a new Artifact, each Artifact exists before a
Job is pointed at it, and the Video is pointed at an already-existing Job, so no
deferrable or circular-FK mechanism is needed. SQL CHECK/FK constraints cannot
prove same-video ownership or the non-NULL provenance/pointer combination;
those are mandatory repository transaction/read validations.

There is no video provenance marker. The durable discriminator is:

```text
jobs.scoring_success_provenance = 'PRIMARY' | 'REPAIR_H2C'
```

for every post-migration Phase-G scoring success, atomically with both pointers
and success. `NULL` means **pre-lineage legacy scoring provenance only**; it is
never a valid new PRIMARY or REPAIR_H2C success. Existing rows deterministically
remain NULL. This explicitly extends the Phase-G persistence completion contract
to record PRIMARY lineage as well as repair lineage; it does not alter Phase F's
memory-only trusted-success boundary, prior PRIMARY Artifact paths, or existing
historical PRIMARY semantics.

For a selected Video lineage, these are mandatory:

```text
video.authoritative_scoring_job_id != NULL
job.video_id == video.video_id
job.job_type == VIDEO_STAGE
job.target_stage == SCORING
job.status == SUCCEEDED
job.scoring_success_provenance IN ('PRIMARY', 'REPAIR_H2C')
job.authoritative_scoring_artifact_key != NULL
```

A Video pointer to a NULL-provenance Job, a PRIMARY/REPAIR_H2C Job with NULL
Artifact pointer, or any mismatched job/video/key/producer is malformed lineage
and rejects fail closed. The FK does not prove same-video ownership, so the
transaction and reader must prove it. A repair graph whose whole Video relation
is absent is non-authoritative material; an ordinary legacy reader must accept
only exact legacy producers, never silently interpret a repaired producer as
legacy.

`expected_authoritative_scoring_job_id` is a repository-owned snapshot taken
only when a SCORING Job is created: it is the Video pointer observed inside the
job-creation transaction. It is NULL for non-SCORING Jobs, and the repository
rejects a non-SCORING value or an expected Job from another Video. It is not a
caller capability.

## 4. Rerun and pointer CAS semantics

The first post-migration scoring success uses expected predecessor NULL and
atomically moves:

```text
video NULL -> scoring_job_1
```

An explicit legitimate SCORING rerun creates a new Job and snapshots the
currently selected Video pointer. If it reaches PRIMARY or repaired success, it
may move the Video pointer from that exact predecessor to the new Job. This is
the current authoritative score selected by an explicit state transaction,
never by timestamp. Old successful Jobs and their Artifact pointers remain
immutable. A failed rerun never moves the Video pointer.

The existing planner has no parent relation and currently treats a scoring Job
whose Video has advanced as stale. Future implementation must preserve the
existing explicit manual-rerun admission while applying the frozen snapshot
rule; it must not invent a broad reprocessing path in this work. Downstream
ANALYSIS and NOTE retain **current-at-execution** semantics: they read the
Video's committed pointer when their handler runs. They do not store a
`source_scoring_job_id`. A later successful scoring rerun before execution is
therefore intentionally consumed; a pointer change after execution begins does
not alter the already-read verified value.

Job Artifact-pointer CAS is exactly conceptual SQL:

```sql
UPDATE jobs
SET authoritative_scoring_artifact_key = :key,
    scoring_success_provenance = :provenance
WHERE job_id = :job_id
  AND status = 'RUNNING'
  AND lease_owner = :owner
  AND lease_until > :now
  AND (authoritative_scoring_artifact_key IS NULL
       OR authoritative_scoring_artifact_key = :key)
  AND (scoring_success_provenance IS NULL
       OR scoring_success_provenance = :provenance);
```

The repository then read-backs and requires exactly one updated row; an
existing non-NULL different key is `H2CAuthoritativeGraphConflict`, never a
replacement. The same key is permitted only for complete-graph idempotent
verification.

Video-pointer CAS is exactly conceptual SQL (the NULL case is explicit):

```sql
UPDATE videos
SET authoritative_scoring_job_id = :job_id
WHERE video_id = :video_id
  AND (
       (:expected_job_id IS NULL AND authoritative_scoring_job_id IS NULL)
       OR authoritative_scoring_job_id = :expected_job_id
  );
```

The stored expected predecessor is supplied from the Job row, not the caller.
Rowcount must be one. Two concurrent scoring Jobs that observed the same
predecessor race; one transaction wins, while the other rolls back its graph
registration and cannot replace the newer pointer. This is not last-commit-wins.

## 5. Cross-job graph ownership

Selected policy: **independently derived same-G convergence is permitted**.
Two Jobs may point to the same immutable structured Artifact key only after
each has independently completed the full live PRIMARY/H2-B/H2-C workflow and
derived the identical P/E/S/G. No job may inspect existing G to skip any
provider, Judge, replay, or admission operation. The pre-existing Artifact row
is then exact-verified/adopted as immutable material; its historical
`artifacts.job_id` remains the first materializing Job and need not equal every
selecting Job.

Therefore `idx_jobs_authoritative_scoring_artifact_key` is deliberately
**non-unique**. The reader requires matching Video and selecting Job pointers,
but for a converged immutable Artifact does not require `artifact.job_id` to
equal the selecting Job. This revises the earlier no-cross-job-sharing wording:
cross-job **execution short-circuit/cache reuse** remains forbidden; durable
convergence after independent execution is not Phase-I cache reuse.

## 6. Reader and reporting contract

The scoring read layer owns all scoring selection and verification. Its exact
conceptual return type is `VerifiedScoringRead` in `src/youtube_intel/scoring.py`:

```text
VerifiedScoringRead(
  scoring_outcome: ScoringOutcome,
  video_id: str,
  scoring_job_id: str,
  scoring_success_provenance: Literal['PRIMARY'] | Literal['REPAIR_H2C'] | Literal['LEGACY_PRIMARY']
)
```

For post-migration Video reads it performs: `get_video(video_id)` → exact Video
Job FK → `get_job(job_id)` → exact Job Artifact key →
`get_artifact_by_key(structured_key)` → parse P/G → derive and exact-load raw →
validate E/S → exact R/J ProviderCalls → rebuild/recompute G for `REPAIR_H2C`,
or uses the frozen primary verifier for `PRIMARY`. It returns no result on any
malformed lineage. Analysis calls this read layer before it consumes a scored
Video; NOTE uses it instead of `_load_scoring(video_id)`; and weekly candidate
construction uses it for each Video before reporting.

Reporting receives `VerifiedScoringRead` plus the existing verified video/note/
analysis inputs. It does not query repaired Artifacts, raw files, ProviderCalls,
or repository selection APIs; it does not select G or verify the repaired graph.
This is the single final reporting architecture. Its candidate provider may
still obtain Video/note/analysis eligibility records, but scoring selection is
performed before `WeeklyReportService` receives the candidate. Legacy Video
reads are routed through the same scoring read layer's exact legacy branch,
which retains the current legacy selection behavior only for legacy producers;
reporting itself has no separate score-reader branch.

This supersedes the contrary H2-C text requiring `reporting.py` to receive a
repository accessor or validate the repaired raw graph, including H2-C §12.1
paragraph beginning “`reporting.py` is also” and §13.5 item 5. It also
supersedes the earlier job-only document's reporting wording to the extent it
left Video reachability unresolved.

## 7. Conflict, pipeline, transaction, and crash semantics

| Case | Result |
|---|---|
| active owned RUNNING Job; pointer NULL; valid graph | CAS set pointer/provenance, then normal success transaction |
| active owned RUNNING Job; pointer equals intended key; complete graph matches | idempotent committed-success read; no write |
| active owned RUNNING Job; pointer differs | `H2CAuthoritativeGraphConflict`; rollback; terminalize current Job with `TRUST_INTEGRITY_INVALID`, detail `H2C_AUTHORITATIVE_GRAPH_CONFLICT`, `retry_at=None`; return `StageDisposition.TERMINAL` only after read-back confirms `FAILED_FINAL` |
| Video predecessor CAS has zero rows while current Job remains owned | `H2CAuthoritativeGraphConflict`; rollback; same terminal error with detail `H2C_VIDEO_LINEAGE_CAS_CONFLICT`; no Video movement |
| Job already SUCCEEDED; pointer equals intended and full graph matches | idempotent read behavior; no mutation/disposition |
| Job already SUCCEEDED; pointer differs or graph differs | `H2CAuthoritativeGraphConflict`; fail closed, no terminal mutation, no generic `_fail`; pipeline performs side-effect-free read and returns |
| lease invalid before transaction | existing `H2CStaleScoringLease`, not graph conflict; zero mutation and pipeline return according to frozen stale table |

The future `pipeline.py` handler catches `H2CAuthoritativeGraphConflict` before
generic `Exception`: for confirmed `FAILED_FINAL` it returns after the terminal
path; for confirmed `SUCCEEDED` it returns without mutation; any other durable
state raises `PipelineInterrupted`. This prevents generic `_fail` from
rewriting a terminal/conflicting Job. `H2CStaleScoringLease` remains exclusively
for failed ownership/lease proof and is never reclassified as graph conflict.

The post-migration scoring-success transaction order is:

```text
BEGIN IMMEDIATE
-> revalidate Job/owner/RUNNING-SCORING/lease and expected predecessor
-> validate intended graph and no conflicting Job pointer
-> reserve R/J ProviderCalls
-> insert/adopt Artifact rows and complete R/J rows
-> CAS Job Artifact pointer + exact PRIMARY or REPAIR_H2C provenance
-> CAS Video authoritative scoring Job pointer
-> update Video scoring summary/state and Job SUCCEEDED
-> COMMIT
```

Before commit, filesystem G material may remain orphaned but no new durable
lineage exists and the old Video pointer remains authoritative. After commit,
the graph, both pointers, provenance, Video state, and Job success are visible
together. A failed/stale rerun leaves the old Video authority intact.

## 8. Future scope, compatibility, and tests

Expected future implementation files, after independent approval only:

```text
src/youtube_intel/migrations/002_add_h2c_scoring_lineage.sql
src/youtube_intel/state.py
src/youtube_intel/jobs.py
src/youtube_intel/scoring.py
src/youtube_intel/runtime.py
src/youtube_intel/pipeline.py
src/youtube_intel/reporting.py
```

Required future tests:

1. migration upgrade/fresh schema, all four columns, FKs/checks/indexes, and
   NULL legacy defaults;
2. atomic repaired Job Artifact pointer, Video Job pointer, provenance, graph,
   state, and success; same-video validation; no ordering query;
3. legacy NULL path; PRIMARY/REPAIR_H2C marker plus NULL/wrong pointer
   rejection; malformed lineage rejection; repaired corruption never falling
   back to legacy;
4. Job pointer NULL→G1, G1→G1, G1→G2, and unrelated-update preservation;
   Video first success, failed rerun, valid later rerun, and stale-racer CAS;
5. independently executed same-G convergence, no pre-dispatch artifact search,
   and non-unique index behavior;
6. analysis, note, and weekly Video→Job→Artifact exact reads; current-at-
   execution behavior; no repaired latest path;
7. one `VerifiedScoringRead` reporting interface; no reporting graph selection/
   verification; and superseded reporting paths absent;
8. active conflict terminalization, terminal same/different pointer behavior,
   stale-lease distinction, and exact pipeline paths;
9. pre-commit orphan invisibility, failed-rerun old authority, post-commit full
   visibility; and
10. historical PRIMARY unchanged; post-migration PRIMARY writes PRIMARY
    lineage without changing legacy P-only Artifact grammar.

Phase I is still out of scope: no artifact cache, execution short-circuit,
cross-job G search, historical H2-C resume, best/latest selection, or cache
trust is authorized.

## 9. Security-discretion closure

The executor has no remaining discretion over downstream job reachability,
Video root, NULL/provenance semantics, final columns/filename, rerun snapshot,
CAS predicates, current-at-execution behavior, convergence policy/index,
reporting interface/supersession, conflict terminal paths, legacy behavior, or
Phase-I boundary. Any deviation is **DECISION NEEDED**.
