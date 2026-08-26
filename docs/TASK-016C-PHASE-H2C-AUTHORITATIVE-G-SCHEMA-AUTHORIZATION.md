# TASK-016C Phase H2-C — Authoritative Graph Selection Schema Authorization

## Status and boundary

Status: **SUPERSEDED FOR DOWNSTREAM LINEAGE BY
`TASK-016C-PHASE-H2C-SCORING-LINEAGE-AUTHORIZATION.md` Round 2; its graph/key
facts remain normative where not superseded.**

This is a control-plane schema/state authorization only. It resolves the
authoritative-graph-selection blocker recorded in
`TASK-016C-PHASE-H2C-AUTHORIZATION.md` §13.4, but does **not** authorize its
implementation, a migration, production-source changes, tests, Phase I, cache
reuse, recovery, resume, cross-job reuse, merge, push, tag, rebase, reset, or
squash.

Reuse decision: **DIRECT** — retain the approved SQLite state store,
`artifacts.artifact_key` unique key, `jobs`, existing migration framework, and
`get_artifact_by_key`; add no dependency or third-party component.

This document is subordinate to the frozen H2/H2-B parent contracts and the
Round-4 H2-C facts. Its job-local selector, migration shape, cross-job policy,
reader root, reporting path, and conflict semantics are superseded by the
lineage authorization above; it remains the record of the initial blocker audit
and its P/G exact-key rationale. In particular, Round 1 selects one Video
first-success pointer, an immutable job-local exact structured-key pointer, a
creation-time lineage-version discriminator, and a partial-unique Job-key
index. Round 2 additionally freezes migration-cutover generation and
transaction-local CAS diagnosis. It authorizes neither scoring rerun nor
cross-job Artifact convergence.

## 1. Audit result

### 1.1 Current physical schema

`src/youtube_intel/migrations/001_initial.sql` is the only current migration.
The relevant durable model is:

| Table | Relevant columns and constraints |
|---|---|
| `videos` | `video_id` PK; `pipeline_status`, `pipeline_version`, `score`, `should_summarize`, `updated_at`, `completed_at`. It has no scoring Artifact/G reference. |
| `jobs` | `job_id` PK; nullable `video_id REFERENCES videos(video_id) ON DELETE RESTRICT`; `job_type`, `target_stage`, `pipeline_version`, lifecycle/lease fields and terminal-status checks. `uq_jobs_active_scope_pipeline` applies only to active jobs; `idx_jobs_video_stage_created` orders `(video_id, target_stage, created_at)`. It has no Artifact/G reference. |
| `artifacts` | `artifact_id` PK; `artifact_key TEXT NOT NULL UNIQUE`; nullable `video_id REFERENCES videos` and `job_id REFERENCES jobs`, both `ON DELETE RESTRICT`; `kind`, root/path/hash/provenance/retention fields. `idx_artifacts_video_kind_created` is an ordering index, not authority. |
| `provider_calls` | `request_hash` PK; `response_artifact_id REFERENCES artifacts(artifact_id) ON DELETE RESTRICT`; operation/provenance/lifecycle fields. It has no job/video success selector. |
| relation tables | `job_attempts` is attempt history only; `reports` is weekly-report identity only. No job-to-authoritative-scoring relation exists. |

The existing unique `artifacts.artifact_key` permits same-P, distinct-G repaired
rows. It deliberately does not select one of them.

### 1.2 Current state and reader APIs

`VideoRecord`, `JobRecord`, and `ArtifactRecord` mirror those fields. Artifact
registration is `_upsert_artifact_in_transaction`; it validates an existing
key's complete record identity and otherwise inserts it. The exact API
`get_artifact_by_key(artifact_key)` performs a single key lookup.

The successful Phase-G transaction currently inserts Artifacts, completes
ProviderCalls, updates `videos` to `SCORED`, and calls
`_finish_job_success_in_transaction` in one `BEGIN IMMEDIATE` transaction.
That transaction has no selector write today.

The current authoritative PRIMARY answer is explicitly weak legacy behavior:
`RuntimeOperations._load_scoring(video_id)` calls
`latest_artifact(video_id, SCORING_STRUCTURED)`, ordered by
`created_at DESC, artifact_id DESC`. `list_weekly_candidates` likewise calls
`_latest_weekly_artifact`, ordered by `created_at DESC, artifact_id ASC`.
Neither is an authoritative relation, and neither is permitted for repaired
producers.

## 2. Options considered

| Option | Decision | Reason |
|---|---|---|
| A — nullable exact structured Artifact key on `jobs` | **Selected** | One nullable field provides a stable, job-bound, exact selection relation; completed jobs are already durable audit history. |
| B — exact key on `videos` | Rejected | It would overwrite a prior successful rerun's identity or require a second history relation. A video-only pointer would introduce a separate “current” authority that H2-C does not need. |
| C — `scoring_successes` relation table | Rejected | It supplies no selection capability beyond a job-owned field but adds a table, API, and migration surface. A table that also selects a current video job would be a second authority. |
| D — strengthen existing Artifact relation with no schema change | Rejected | `artifacts.job_id` is many-to-one and cannot select exactly one structured graph. Any read query would reintroduce ordering or guessing. |
| E — another relation | Rejected | No smaller relation satisfies both immutable per-job history and exact lookup. |

## 3. Selected authoritative relation and cardinality

**Selected option A:** add the nullable `jobs.authoritative_scoring_artifact_key`
column. Its stored value is exactly the complete repaired structured Artifact
key, never G alone:

```text
scoring/<P>/repair/<G>/structured
```

It is derived inside the trusted Phase-G write-plan construction from the
replayed/validated H2-C graph. No caller supplies the key, P, G, or role as an
independent persistence input.

The cardinality is frozen:

```text
one scoring Job -> zero or one authoritative structured Artifact key
before scoring success -> NULL
successful H2-C repair scoring Job -> exactly one non-NULL key
one Job -> never two G values
```

The unique `artifact_key` FK target means the stored value resolves to one
Artifact record. The repository transaction additionally requires that record
to be the just-validated `SCORING_STRUCTURED`, DATA-root, same-`job_id`,
same-`video_id` repaired plan Artifact; the foreign key alone cannot express
those cross-row predicates.

This relation is intentionally **job-level only**. A completed repair job owns
an immutable selection for its own success. There is no `videos` pointer and
therefore no “currently authoritative repair for a naked video” concept in
H2-C. A caller that has only `video_id` must not derive a repair job by recency,
ordering, artifact enumeration, or a cache. It must be given the exact
successful scoring `job_id` by its owning workflow, or no repaired result is
available. This is not a missing fallback; it prevents a second authority.

Manual rerun creates a new Job under existing rules. Each new successful repair
job gets its own immutable non-NULL key. Previous jobs and their pointers stay
unchanged. H2-C does not select a winning/current job for a video and does not
permit cross-job graph reuse: a retry may succeed only by registering its own
complete graph under its own job. If its prospective key is already bound to a
different job, existing exact Artifact identity validation rejects it; it must
not point at or adopt the previous job's graph.

## 4. PRIMARY compatibility and existing data

This is **repair-only**. Phase F PRIMARY remains frozen as PRIMARY-only,
memory-only, zero-persistence at its own boundary, and existing persisted
PRIMARY readers/reporting retain their legacy `latest_artifact` behavior.
`authoritative_scoring_artifact_key` is NULL for all existing rows and for
legacy PRIMARY jobs. There is no backfill.

Repair identity is recognized only by the exact repaired producer versions and
G-shaped key grammar; a reader never treats a NULL legacy job as a repair
selection. Backfill from historical PRIMARY Artifacts would require forbidden
latest/heuristic selection when a video has multiple rows, so it is expressly
out of scope. A later, separately approved PRIMARY normalization may decide a
different migration and backfill policy; it is not implied here.

## 5. Frozen migration and state contract

The future implementation shall add, and only then apply, a new migration:

```text
src/youtube_intel/migrations/002_add_authoritative_scoring_artifact_key.sql
```

Its exact schema operations are:

```sql
ALTER TABLE jobs
    ADD COLUMN authoritative_scoring_artifact_key TEXT NULL
    REFERENCES artifacts(artifact_key) ON DELETE RESTRICT;

CREATE INDEX idx_jobs_authoritative_scoring_artifact_key
    ON jobs(authoritative_scoring_artifact_key)
    WHERE authoritative_scoring_artifact_key IS NOT NULL;
```

No unique index is added: distinct jobs are historical records, and a unique
job-column is already intrinsic to one column per row. The non-unique partial
index supports SQLite foreign-key reverse checks and exact audit queries.
`artifacts.artifact_key` is already `UNIQUE`, so it is a legal referenced
parent key. `ON DELETE RESTRICT` prevents deleting the registered structured
Artifact row while a job authorizes it.

The repository enables `PRAGMA foreign_keys = ON` on every connection. The
executor must extend `_load_migrations()` to load ordered immutable migrations
001 then 002; it must not edit 001. Both the system `sqlite3` (3.51.0) and the
Python runtime `sqlite3` (3.53.2) in this worktree accept a nullable
`ALTER TABLE ... ADD COLUMN ... REFERENCES ... ON DELETE RESTRICT`; the
verified insert of a missing referenced key fails with `FOREIGN KEY constraint
failed`. No deferrable FK is needed or authorized: the existing Job must exist,
then both Artifact rows are inserted, then `jobs` is updated to point at the
already-inserted structured Artifact, all within one transaction.

An upgrade database gains NULL for every existing Job. A fresh database applies
001 and then 002 to the same final schema. Migration history/checksum and
`PRAGMA user_version` retain the existing monotonic migration contract.

`JobRecord` gains `authoritative_scoring_artifact_key: str | None`; its row
mapper and `get_job(job_id)` expose it. No generic “latest repaired artifact”
or video-only repaired selector API is authorized. The exact reader starts with
`get_job(job_id)` and that field.

## 6. Transactional write, idempotency, and conflicts

The frozen repaired success ordering is:

```text
PREWRITE_VALIDATE and graph/key derivation
-> repair filesystem materialization/adoption
-> BEGIN IMMEDIATE
-> revalidate current job / owner / RUNNING SCORING / active lease
-> insert/reserve R and J ProviderCalls as PENDING with no response Artifact ID
-> insert or exact-upsert raw and structured Artifacts
-> complete R and J ProviderCalls with the raw Artifact ID
-> verify structured Artifact is the same job/video/repaired structured plan record
-> set jobs.authoritative_scoring_artifact_key to its exact artifact_key
-> transition videos TRANSCRIPT_READY -> SCORED with summary
-> transition job -> SUCCEEDED
-> COMMIT
```

The selector write and both transitions are in the same SQLite transaction.
The repair persistence entry must reject a NULL selector before it may invoke
the success transition. Thus H2-C has no committed state where the Job is
`SUCCEEDED` but lacks a selector, or where a selector points at an unregistered
Artifact. The filesystem may contain unregistered material before `COMMIT`, but
it is not authority.

Before filesystem work, committed-graph checking first reads the job's stored
selector if present:

1. If it equals the plan's exact structured key, the complete Artifacts,
   ProviderCalls, video state, job state, pointer, and files must all match;
   return the existing Phase-G idempotent result with no writes.
2. If it is non-NULL and differs, raise the exact internal
   `H2CAuthoritativeGraphConflict` (a subclass of `IntegrityConflict`) with
   stable code `H2C_AUTHORITATIVE_GRAPH_CONFLICT`. It is fail-closed: no second
   graph registration, pointer update, state transition, or file overwrite.
   The trusted persistence boundary maps it to a non-retryable
   `ScoringPersistenceError` with `ErrorCode.TRUST_INTEGRITY_INVALID` and the
   same stable diagnostic code. If observed by a stale runtime, the existing
   H2C stale no-mutation handling reads the terminal Job and returns; it must
   never route through generic `_fail`.
3. If it is NULL, ordinary H2-C PREWRITE lease/ownership checks govern the new
   registration. A changed owner or expired lease uses the already-frozen
   `H2CStaleScoringLease` no-mutation path.

The exact same-G idempotent branch additionally requires the stored pointer to
equal the planned structured key. A complete matching file/Artifact graph with
NULL or another pointer is not idempotent; it is integrity-invalid.

## 7. Exact reader and reporting contract

### 7.1 Runtime repaired reader

The repaired runtime reader accepts an exact successful SCORING `job_id` and
the expected video context. It must:

1. `get_job(job_id)` and require `VIDEO_STAGE`, `SCORING`, `SUCCEEDED`, the
   expected video, and non-NULL `authoritative_scoring_artifact_key`.
2. Call `get_artifact_by_key(job.authoritative_scoring_artifact_key)` exactly
   once for the structured Artifact; require undeleted DATA
   `SCORING_STRUCTURED`, the repaired structured producer version, and matching
   `job_id`/`video_id`.
3. Parse its exact key grammar as `scoring/<P>/repair/<G>/structured`, require
   lower-hex P/G, and require its relative path to be
   `scoring/<P>/repair/<G>/structured.json`.
4. Read and hash the sealed structured bytes; require its Artifact content hash
   to equal S and validate the replayed finalizer/structured result.
5. Derive, never search for, `raw_key = scoring/<P>/repair/<G>/raw`; call
   `get_artifact_by_key(raw_key)`; require the matching raw kind, producer,
   job/video, DATA root, path, and exact raw envelope hash E.
6. Strictly parse the envelope; obtain R only from
   `repair_provider_evidence.request_hash`, J only from the replayed repair
   Judge H2, and settings only from the sealed provenance. Fetch exactly
   `get_provider_call(R)` and `get_provider_call(J)`; require successful rows,
   frozen operations/provenance, raw Artifact ID, and all P/R/J/settings links.
7. Rebuild `RepairPersistenceGraphIdentityV2` from P, R, J, settings hash, E,
   S, and the frozen producer/schema/policy versions; H2-JCS hash it; require
   the recomputed G to equal the structured key/path G and raw key/path G.
8. Return only the trusted result after all checks pass; any missing, duplicate,
   malformed, wrong producer/path/job/video/P/G/E/S/R/J/settings, or mismatch
   rejects fail closed.

No step may call `latest_artifact`, `latest_video_job`, `_latest_weekly_artifact`,
an ordering query, directory enumeration, a P-only lookup, or a cache.

### 7.2 Reporting

Selected reporting architecture: **B — reporting receives a pre-verified
repair scoring result produced by the runtime reader**, together with its
`job_id` provenance for audit. Reporting receives neither a naked Artifact nor
a naked video ID and does not choose G, a job, or an Artifact. This keeps graph
selection in repository/state responsibility and avoids a second verifier or
selector in `reporting.py`.

The shared verifier decision is therefore: implement one pure future repaired
graph verifier in `src/youtube_intel/scoring.py`, taking already-fetched
Job/Artifact/ProviderCall records plus exact bytes and expected job/video
context, and returning the verified scoring result. It receives no repository,
performs no selection, and does not accept an Artifact list. The runtime reader
owns the initial `get_job(job_id)` selector lookup and exact record fetches;
reporting consumes the verified output only. Legacy PRIMARY weekly reporting
remains unchanged.

## 8. Crash, authority, and Phase I boundary

Crash before the SQLite `COMMIT`: Artifact rows, R/J ProviderCall rows, selector
write, video transition, and Job success all roll back. Filesystem orphans may
remain, but the NULL/absent durable selector means they are invisible and
non-authoritative.

Crash after `COMMIT`: both Artifact rows, both ProviderCalls, the exact job
selector, video `SCORED`, and Job `SUCCEEDED` are visible together. The durable
pointer is an output of the already-authorized persistence transaction; it is
not a trusted-success capability and cannot initiate H2-C or repair.

This authorization covers current repaired runtime selection and reporting's
consumption of a verified result only. It does not authorize cache reuse,
cross-job reuse, historical-envelope recovery, H2-C resume, selection of a
best/latest Artifact, cache trust, Phase I, or a video-level “current result.”

## 9. Frozen future implementation and test scope

After independent approval, the expected implementation files are:

```text
src/youtube_intel/migrations/002_add_authoritative_scoring_artifact_key.sql
src/youtube_intel/state.py
src/youtube_intel/scoring.py
src/youtube_intel/runtime.py
src/youtube_intel/reporting.py
```

plus the previously authorized H2-C files only after overall H2-C
implementation authorization. This document itself authorizes none of them.

Required future tests are:

1. migration upgrade from a 001 database, fresh 001+002 initialization, exact
   column/index, NULL pre-success state, FK rejection, and migration history;
2. transaction success commits Artifacts, pointer, video/job success together;
   injected rollback leaves no pointer; pointer cannot reference a missing
   Artifact; repaired success cannot commit without a pointer;
3. job cardinality is zero/one; same G is no-write idempotent; G1 then G2 for
   one Job returns `H2C_AUTHORITATIVE_GRAPH_CONFLICT`; a retry Job has its own
   immutable relation and cannot reuse another Job's Artifact graph;
4. reader starts at `get_job(job_id).authoritative_scoring_artifact_key`, uses
   exact structured and derived raw `get_artifact_by_key` lookups, never latest,
   and rejects missing/wrong structured/raw/G/E/S/R/J/settings/job/video;
5. reporting accepts only the pre-verified repaired result, has no naked-latest
   repaired path, and shares no selection responsibility;
6. pre-commit filesystem orphans are not selectable; post-commit full graph is
   visible; and
7. legacy PRIMARY runtime/reporting behavior remains unchanged with NULL
   pointer, including no ambiguous backfill.

## 10. Security-discretion closure

The future executor has no discretion over the schema option, exact table and
column, stored value, repair-only scope, job-level cardinality, rerun behavior,
migration filename/operations, FK/index policy, no-backfill rule, transaction
ordering, same-G idempotency, G1/G2 conflict/error path, reader starting query,
exact raw derivation, R/J lookup, reporting input, shared-verifier boundary, or
the no-latest/no-orphan-selection rules. Any deviation is **DECISION NEEDED**.
