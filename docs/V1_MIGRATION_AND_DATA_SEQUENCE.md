# V1 Migration and Data Sequence

Status: **FROZEN PLAN — NO MIGRATION AUTHORIZED BY THIS DOCUMENT**

## Current reality

At the approved TASK-018 anchor, `PRAGMA user_version` is **6**. `SQLiteStateRepository.initialize()` loads ordered migration files, verifies checksum history, wraps each migration and `schema_migrations`/`user_version` update in one immediate transaction, and fails closed on mismatch or SQL failure. Migration 005 owns `source_subscriptions`, `source_video_links`, `automation_schedules`, `automation_runs`, and `global_model_preferences`; m006 owns the immutable Evidence/Intelligence foundation. Existing `videos`, `artifacts`, `jobs`, `job_attempts`, `provider_calls`, `provider_dispatch_states`, reports, trusted scoring, Source, and Automation records remain authority owners.

## Forward-only sequence

| Version | Owner | Content | Requires |
| --- | --- | --- | --- |
| 006 | TASK-018 | Evidence identity/lineage/availability; Intelligence identity/current pointer; immutable revisions/state history; revision-to-evidence and dependency edges | v005 |
| 007 | TASK-018A | immutable revision-specific finite claim classification; `UNCLASSIFIED` only for upgraded v006 rows | v006 |
| 008 | TASK-020 | raw feedback; explicit/derived long/recent/temporary preference records; expiry and correction separation | v007 |
| 009 | TASK-021 | Source policy revision/config fields; source-video filter disposition/reason; manual-analyze audit | v008 |
| 010 | TASK-022 | V1 execution target/checkpoint and immutable resource-usage ledger linked to existing jobs/provider calls | v009 |
| 011 | TASK-023 | Topic, Intelligence membership, pin state, source-backed timeline event, light relation | v010 |
| 012 | TASK-025 | immutable V1 Brief snapshot/item references and supersession marker | v011 |

Each migration is additive/forward-only, one file, one owner, and may reference existing stable IDs without duplicating their authority. No V2 Investigation, Early Signal, external evidence, Daily, Ask, credential, dispatch, or TASK-016 tables are added. Migration rollback is not an operating strategy: restore a verified pre-upgrade local backup, diagnose the migration, issue a later corrective migration only after PO approval, and never alter applied migration text/checksums.

## Upgrade and failure safety

Upgrades from v005 retain all Source/Automation rows unchanged. New source-policy fields receive conservative V1 defaults equivalent to current `STANDARD_INTELLIGENCE` behavior: history 5, per-run cap 5, no override, balanced style; existing source/video links receive an explicit `UNASSESSED_LEGACY` disposition rather than inferred relevance. No existing job/provider-call state is reclassified; old AMBIGUOUS remains terminal.

The migration transaction must leave neither schema nor `user_version` advanced on failure. New nullable/current pointers are filled only atomically with their first valid revision; read services fail closed for incomplete rows. Restart does not enqueue or call providers merely because a migration ran. Execution checkpoints/ledger rows must identify an interrupted step and resume only after existing job/artifact/provider-call/dispatch checks prove it safe.

## Independent evidence per owner

For every migration owner: assert fresh-v012 schema, v005-to-target sequential upgrade, exact constraints/indexes/FKs, preservation of source/schedule/run data, transaction rollback on injected malformed SQL, checksum/history mismatch failure, and restart without work admission. TASK-027 runs the packaged wheel/runtime against a v005 fixture, initializes to v012, serves the read-only synthetic API, and verifies no real provider/YouTube call. Version gates must be updated only by their owning task after all migration fixtures pass.
