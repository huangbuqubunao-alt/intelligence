# M10 — Core Backup and Restore Acceptance

Status: **PASS** for the owner-authorized V1 Intelligence-managed core scope.
Validated 2026-09-24 (Asia/Shanghai) on an isolated, task-owned clone of real
pipeline data. The owner’s primary data and external Vault were not used as a
restore target. [Issue #10](https://github.com/huangbuqubunao-alt/intelligence/issues/10)
tracks the launch-critical acceptance.

## Scope and recovery contract

The archive contains the coherent SQLite snapshot and only live `StorageRoot.DATA`
files referenced by that snapshot. The V1 core scope covers Following, Content,
Transcript, Summary / Video Notes, Evidence, Evidence translation presentation,
Intelligence, Topic, and persisted product settings. `StorageRoot.VAULT`, model
weights, credentials, browser state, and environment secrets are excluded.

Backup readiness uses validated effective processing authority, including the
M5B positive-zero binding; genuinely mutable or unresolved work blocks creation.
SQLite’s backup API creates the database snapshot, which is opened independently
and checked with `PRAGMA integrity_check`. The deterministic manifest records the
schema, scope counts, and each DATA path, size, and SHA-256.

Restore stages and validates the selected archive without touching live data.
The confirmation is typed and bound to the staged archive and manifest hashes.
Confirmation marks a pending operation; activation occurs before repositories
and workers open. The database and DATA directory are activated as one recoverable
pair, with a persisted marker and retained old pair until restored authority and
DATA hashes validate. Startup rechecks archive identity and the activated pair;
validation failure restores the previous pair. Replaying a completed confirmation
is rejected.

The finite marker states are `PENDING`, `APPLYING`, `VALIDATED`, and `APPLIED`.
Startup rechecks archive identity and the activated pair, including the restored
SQLite file’s exact manifest hash. `APPLIED` is persisted only after the pair
passes those checks; rollback copies are retired after that commit marker. An
interruption during retirement is idempotently completed at the next startup.
Validation failure before `APPLIED` restores the previous pair; a failure after
commit either restores the still-complete rollback pair or stops startup with
the marker and stage preserved.

## Migration 024 proof

A fresh-database integration test applies the full migration lineage through
024. Separately, a task-owned SQLite backup and DATA copy of the real restored
pipeline state was shaped to the exact 023 predecessor by setting
`user_version=23`, removing only the three 024 triggers and its migration-history
row, then upgraded through the
repository initializer. `PRAGMA integrity_check` returned `ok`; one current
Summary pointer, one Evidence translation presentation, one M5B positive-zero
result, and its checkpoint retained identical before/after row fingerprints.
Backup readiness remained quiescent after migration. No 001–023 migration was
edited.

## Reuse decision

**DIRECT** — use Python’s existing `sqlite3` backup API, `zipfile`, and
standard-library filesystem primitives for coherent snapshots, bounded archive
handling, exclusive temporary files, no-overwrite publication, and controlled
renames. No production dependency was added. Historical PRs #28 and #29 were
**REFERENCE** only; no obsolete branch or implementation was merged or
cherry-picked.

## Real-data round trip

The Settings GUI created and downloaded Backup A through the production loopback
API, then changed the test clone’s output-language preference from `zh-CN` to
`en` to form State B. A corrupted copy was rejected with HTTP 409 while State B
remained intact. Inspecting and cancelling Backup A made no live changes. The GUI
then staged Backup A, required the explicit typed `RESTORE` confirmation, and
applied it at the controlled restart boundary.

Backup A was 73,422 bytes (SHA-256
`1d08a98a28bac76d55b8beb362e7daa7fc2109a26facc0a761287a88ab422602`). Its
manifest records format version 1, application version 0.1.0, schema version 24,
and these counts:

| Object | Count |
|---|---:|
| Following | 1 |
| Content | 1 |
| Current Summary | 1 |
| Evidence | 4 |
| Intelligence | 0 |
| Topic | 1 |
| DATA artifacts | 6 (33,310 bytes) |
| Persisted settings | 1 |

The restored SQLite snapshot hash matches the archive (`a80a1b304af35346b706e5a33c34d24e3a6bf3a9f0e97d196b5d342a1cb3c04b`) and
passes `integrity_check`. All six manifest DATA hashes and sizes match the live
restored files. The archived entry list is exactly the manifest, database, and
those six files.

Post-restore verification confirmed:

- Following `2a08b789-b3a4-45df-8fd0-5295ae9065f9` and Content `--khbXchTeE`;
- canonical transcript SHA-256
  `fcde4db460a76a2d8ff2bb2eddd61a3ea42bab361bec7d912980a95e8c648cad` and
  trusted local scoring job `4567e2d1-2f3a-464b-b0d3-426c9ff677f9`;
- the same explicitly referenced current Summary artifact
  `analysis-structured-9f2bef30b6a98a95b3cf7b1234e4b4984d9f39b802a7adf7f86f0372adcc4ce4`,
  returned through the trusted Summary reader with the same content and evidence
  references as before the backup;
- all four original Evidence records, including translated presentation for
  Evidence `e0bbc0cf14396c6ec73a2f0a7c7d16424a4fb052fea248dec237cbbc1c5e2203`;
  the GUI verified `译文`, `双语`, and `原文` modes, and translation hashes match;
- zero Intelligence with the persisted successful
  `NO_NEW_INTELLIGENCE` outcome; no active jobs or Source Runs;
- Topic `topic:m10-real-acceptance-001` and the `zh-CN` output-language setting.

Both the task-owned clone's configured `StorageRoot.VAULT` and the external
read-only M8 Vault fixture were independently hashed by the Playwright drill;
both hashes were identical before and after restore.
The configured clone Vault tree hash was
`13ed01dc3da86194287e5a93fe15c7588bab5b7bede3477440479b74861359b8`
(1 entry); the external M8 Vault tree hash was
`a7928d5e2e9e5844d12b3f2887d240fb587b32f7751b86a7c22039d193520583`
(3 entries).
The archive manifest marks Vault, credentials, and model weights excluded; the
archive has no Vault, credentials, or browser-profile entries, and the core
database schema has no credential-bearing columns. No provider call, cloud
inference, paid call, or authenticated YouTube access occurred during this M10
backup/restore exercise. The sample’s existing local-model outputs were already
persisted before the exercise.

## Failure coverage and limits

Backend tests reject manifest-hash mismatch, SQLite corruption, DATA hash
mismatch, missing referenced DATA, unexpected entries, traversal paths,
duplicate paths, and incompatible schema before live mutation. Staged-data
tampering is rejected before confirmation. Tests also prove cancellation leaves
live data untouched, repeated confirmation is rejected, activation failure rolls
back the database/DATA pair, and post-activation revalidation failure restores
State B before startup proceeds. A restart during rollback-copy retirement
finishes from the persisted `APPLIED` state.

The drill verifies controlled process restart and software recovery states. It
does not simulate physical power loss, kernel/filesystem failure, or arbitrary
external concurrent writers; backup is available only at the validated
quiescent boundary. No claim of hardware-level atomicity or a real power-loss
test is made. Vault restore and cloud backup are outside M10.

## Verification

- `uv run python -m pytest tests/unit/test_backup_restore.py -q` — 21 passed.
- `uv run python -m pytest -q` — 2,349 passed, 1 skipped, 0 failed.
- Ruff, mypy (61 source files), compileall, and `git diff --check` — PASS.
- Frontend typecheck, 65 Vitest tests, and production build — PASS.
- `npm run test:e2e --prefix frontend` — PASS at 1440×900 and 768×900, with no
  console errors or external requests.
- `node frontend/backup-restore.e2e.mjs` against the task-owned real-data clone,
  hashing both its configured Vault root and the external M8 Vault fixture —
  PASS, including corrupt-archive rejection, cancellation, explicit confirmation,
  restart-boundary application, current Summary, M8 translation modes, and Vault
  exclusion.
