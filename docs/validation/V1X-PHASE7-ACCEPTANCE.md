# V1X Phase 7 acceptance evidence

Baseline: `08d62d8cb459a7d157f9c4a4c87cf23a3209d4b8` (verified clean local main, schema 31).
Worktree: `/Users/hua/Documents/yia-worktrees/v1x-local-provider`.
Branch: `chatgpt/v1x-local-provider`.
Authority: the owner's continuous Phase 7 goal; one engineering executor.
Decision: [V1X-PHASE7-DR-001](../decisions/V1X-PHASE7-DR-001-local-provider.md).

## Product and authority acceptance

Local is the first production non-YouTube provider. One Following Local library
contains imported ordinary Contents. User selection and confirmation are required;
no terminal, typed path, folder scan or new primary navigation is introduced.
All eight specified formats are accepted within the documented size/validation
policy. TXT/MD becomes READY with exact UTF-8 source text, durable ranges and a
normal deterministic source-excerpt Summary. Audio/video becomes a truthful
TRANSCRIPTION_UNAVAILABLE library item by default. Existing MLX Whisper has no
provisioned production offline timed executor; no weights are downloaded and no
transcript/timestamps are invented. The offline typed adapter is exercised with
real local media bytes and deterministic timed fixtures, including DA authority.
Production DA execution remains NONE.

Snapshots use SHA-256 bytes and immutable managed DATA artifacts. Original files
are never mutated, moved or deleted. Dedupe verifies existing authority; changed
bytes create another identity. Original move/delete/edit does not alter historical
Content. Paths and filenames cannot choose storage or become authority. No
original absolute path is retained by production import. Text ranges and timed
media share the existing durable Evidence domain, ownership and dependency guards.

Mixed YouTube/Local Intelligence uses sealed SYNTHESIS revisions and exact durable
Evidence dependencies. Topic association uses normal explicit authoritative
membership. Mixed selected-Content Research packets retain provider provenance and
use no model or web call. Research history/diff and Knowledge Delta use ordinary
contracts. Existing versioned archives include every registered source/transcript/
provenance/Summary DATA artifact within archive bounds; corruption fails before
live activation. Schema-31 live databases upgrade atomically. Archive restoration
retains the existing matching-schema application contract; it does not silently
accept schema-31 archives as schema-32 archives.

## Validation commands and results

Logs and screenshots are isolated under `.var/phase7`, outside accepted source.
Browser fixture setup: `PYTHONPATH=src python tests/e2e/local_provider_fixture_server.py .var/phase7/browser-fixture --port 5572`; from `frontend`, run
`YIA_API_BASE=http://127.0.0.1:5572 npm run dev -- --host 127.0.0.1 --port 5573`.
E2E uses the installed Chrome and existing Playwright dependency. All fixture app
storage, fake credentials and fixture Obsidian vault remain within the Phase 7 root.
No production dependency, lockfile, credential or production configuration changed.

| Gate | Command / boundary | Final evidence |
| --- | --- | --- |
| Local adversarial integration | `PYTHONPATH=src python -m pytest tests/integration/test_local_content_provider.py tests/integration/test_local_content_adversarial.py -q` | 45 passed; `validation/local-focused-acceptance.log` |
| Provider-neutral regression | Existing Summary, timed Evidence, DA, Intelligence, Topic, Research, backup and Knowledge Delta tests | Focused remediation run: 90 passed, followed by full suite |
| Full backend | `PYTHONPATH=src python -m pytest -q -ra` | 3319 passed, one existing optional-resource skip, two adversarial warnings; `validation/full-backend-acceptance.log` |
| Frontend | `npm run typecheck`; `npm test -- --run`; `npm run build` | 169 passed in six files; typecheck/build pass |
| Local browser | `node local-provider.e2e.mjs` | Eight real HTTP/SQLite flows, zh-CN/en × 320/768/1024/1440 |
| Integrated browser | `node local-provider-regression.e2e.mjs` | Eight Following/YouTube/DA/Evidence/Obsidian/Settings/Research History/Diff flows |
| Actual process restart | Stop own fixture server; restart same DB/DATA; `YIA_PHASE7_RESTART_ONLY=1 node local-provider.e2e.mjs` | Eight persisted Content/Summary/Evidence/Local+mixed Research/Delta flows |
| Static | `ruff check src tests`; `mypy --strict src`; `python -m compileall -q src tests`; `git diff --check` | Pass; mypy checks 82 source files |
| Design | `designmd lint frontend/src/workspace/DESIGN.md` | Zero errors, warnings or infos |
| Docs | Relative-link, code-fence and whitespace checks for Phase 7 decision, index and acceptance | Pass |
| Database | Read-only history/checksum/source-schema verification; `PRAGMA quick_check`, `integrity_check`, `foreign_key_check` | Schema 32; 31 migrations (029 absent); ok/ok/empty |
| Protected worktrees | HEAD, porcelain status and SHA-256 of tracked/untracked regular files against pre-task inventory | main, dirty M13 and clean milestone closure unchanged |

The pre-existing optional o200k provisioning test is skipped because the canonical
asset has not been explicitly provisioned. No skip was added. Two Pydantic warnings
come from existing deliberate adversarial enum values. Existing frontend unit tests
emit React act warnings; actual browser flows have no console warnings/errors,
page errors, unexpected external requests or viewport overflow.

The native picker is implemented with the platform browser's File picker. Adapter
selection (`setInputFiles` / File tests) and real filesystem/HTTP integration were
validated. The actual owner OS dialog was not driven; that manual interaction check
is not claimed. Screenshots of the actual rendered UI were visually reviewed.

## Required adversarial matrix

`A` = `tests/integration/test_local_content_adversarial.py`;
`P` = `tests/integration/test_local_content_provider.py`;
`B` = `frontend/local-provider.e2e.mjs`;
`R` = `frontend/local-provider-regression.e2e.mjs`.

| # | Required case | Evidence |
| --- | --- | --- |
| 1 | Valid UTF-8 TXT → READY | P `test_text_snapshot_ready_and_restart` |
| 2 | MD original text preserved | A `test_research_and_backup_restore_preserve_source_text`, original-byte/tamper cases |
| 3 | Valid audio processing | A real WAV/MP3/M4A ffmpeg fixtures |
| 4 | Valid video processing | A real MP4/MOV/M4V ffmpeg fixtures |
| 5 | Unsupported extension | P invalid sources; B invalid PDF feedback |
| 6 | Invalid/binary TXT | P invalid UTF-8/NUL cases |
| 7 | Malformed media | A three malformed fixtures, no Content admission |
| 8 | Oversized text | A per-type size limit before storage |
| 9 | Oversized media | A per-type size limit before storage |
| 10 | Traversal filename | A safe filename/storage/API cases |
| 11 | Absolute-looking filename | A safe filename/storage/API cases |
| 12 | Control/Unicode filename | A sanitization; B long Chinese filename |
| 13 | Selected symlink | A selected descriptor snapshot |
| 14 | Symlink replacement/race | A replaced target and in-place mutation rejection |
| 15 | Original deleted | A original move/delete/mutation test |
| 16 | Original moved | Same original ownership test |
| 17 | Original modified | Same original ownership test; prior Evidence remains exact |
| 18 | Changed reimport | Same test; new digest/Content identity |
| 19 | Identical bytes | Verified deterministic dedupe, B duplicate import; extension bypass rejected |
| 20 | Path privacy | A API and artifact path assertions |
| 21 | Restart | P repository reopen; actual server restart B |
| 22 | Text locator | P exact offsets; A excerpt/hash/range verification |
| 23 | Media locator | A `test_trusted_media_has_real_timed_locator_and_normal_summary` |
| 24 | Foreign Content Evidence | A `test_foreign_content_range_cannot_bind` |
| 25 | Source tampered | A source/canonical and media source tamper |
| 26 | Canonical/transcript tampered | A canonical/cue/provenance and corrupt archive cases |
| 27 | Local Summary | Normal current Summary pointer, durable citations, exact excerpts; Chinese language regression |
| 28 | YouTube Summary | Full existing Summary authority tests; R original fixture |
| 29 | Mixed Intelligence | A sealed SYNTHESIS, exact dependency edges, per-Evidence API provenance |
| 30 | Topic | A normal explicit Topic association with mixed authoritative Evidence |
| 31 | Local Research | A deterministic Local packet and restore; B Local selection |
| 32 | Mixed Research | A repeat deterministic packet/scope/provenance; B both provider labels |
| 33 | Knowledge Delta | A ordinary completed category; B actual Home change |
| 34 | Delete original invariant | A logical removal retains both original and managed snapshot |
| 35 | Text backup/restore | A archive stage/confirm/activation, trusted packet and dedupe |
| 36 | Media backup/restore | A source/provenance/cues/timed Evidence restored |
| 37 | Corrupt archive | A four authority attacks, rejection and unchanged live DB hash |
| 38 | No import network | A forbidden socket seam; B no unexpected requests; ffprobe remote protocols and playlist autodetection blocked |
| 39 | No required model/cloud | Deterministic text/excerpt path and truthful media state; offline fixtures only |
| 40 | Chinese | B and R zh-CN all four widths |
| 41 | English | B and R en all four widths |
| 42 | Narrow 320px | Actual long-filename/excerpt UI, zero overflow |
| 43 | No scan/watch | A glob/rglob forbidden; Local source check/schedule blocked; diff audit |
| 44 | No new nav | B verifies existing six primary destinations |

Extra gates cover a playlist disguised as MP3, forced demuxer boundaries for all six
real media formats, atomic interrupted READY recovery, full migration-32 table-rebuild
rollback/retry, schema-31 trigger preservation and historical checksum preservation.

## Three self-review passes and remediation

Authority: filename/path cannot become identity; source and canonical artifacts
are rehashed at trusted reads; text offsets and excerpt ownership are exact; timed
provenance binds the full cue hash. Original edits cannot change the snapshot.
Backup checks packaged schema guards and all Local authority before activation.
The migration preserves every existing Evidence trigger, including current
Intelligence availability protection. Invalid TEXT_RANGE cannot fall back to the
timed resolver. An unrelated provider default applied to non-Content DTO parsers
was removed. Duplicate import cannot evade extension/container validation.
Forced MP3/WAV/MOV demuxers prevent probing a disguised playlist and accessing
its additional referenced inputs; QuickTime external data references stay disabled.

Product: actual zh-CN/en UI was examined at four widths. Fixed long-filename
wrapping, imported-Content deep links, Source text/Summary/text Evidence labels,
loading/error title branches, original-language Summary display and Research text
locator copy. Multi-file adapter test proves explicit confirmation, sequential
uploads, per-file failure continuation and duplicate presentation. Originals and
private absolute paths are absent from normal UI. Media unavailability is explicit.

Multi-source: the existing Content table, Artifact registry, Summary pointer,
Evidence domain, revision/dependency admission and Research scope are reused.
Legacy channel/video field names survive behind compatibility boundaries;
Local does not invent creator metadata, URL authority or a second subsystem.
A future provider adds provider/admission capabilities and uses the same snapshot,
locator and downstream authority, rather than parallel Content/Evidence domains.

After all gates passed, the complete baseline-to-Phase-7 diff was reviewed again
across provider, persistence, filesystem, Evidence/Summary, Following/Research,
mixed-source contracts, backup, UI and every changed test. No P0/P1 or material
Phase 7 P2 remains. Backend and UI commits are `26f8b34a68e2f663316880abef08b445b79efd44`
and `f299c7771b6a5bbca7e6a0930741bfb3a3cb804e`; the final documentation commit and
HEAD are supplied in the owner report to avoid a self-referential commit hash.

## Failure evidence retained

Initial full `python -m pytest -q` found 44 failures (3263 passed): current-schema
assertions needed additive migration-32 expectations; one rebuilt Evidence trigger
was missing; Research introduced per-Evidence queries; pre-32 fixtures hit new
columns; historical projections acquired an empty provenance field. Failures and
assertions are retained in `validation/full-backend-first.log`. Remediation restored
the exact trigger, batched provider lookup, isolated old-schema compatibility,
preserved historical serialization and updated additive schema expectations without
removing tests/assertions or reducing coverage. A later full run passed 3316 tests.

Frontend verification caught four loading/error branches referencing a scoped
Evidence title; fixed the declaration and reran all tests. A new Chinese Summary
regression initially had fixture-construction errors (`TypeError: ... missing
service`, then `KeyError: notes` at `test_local_content_adversarial.py`); corrected
it to the actual service and `note` API contract without weakening assertions.
Full runs were intentionally interrupted for language and demuxer security
remediation; those logs are retained, and the final full suite ran afterward
against frozen backend code. Test preservation audit confirmed all existing test
functions remain (the doctor test name advanced from schema 31 to schema 32).

## Bounded limitations and Phase 8

Production offline timed transcription provisioning remains future work; imported
media truthfully has no Summary/Evidence until such an adapter exists. Native OS
dialog interaction remains an owner manual check. Physical snapshot garbage
collection is deferred under existing dependency-impact rules. Existing backup
size bounds reject oversized libraries explicitly and matching-schema archive
restore remains unchanged. These are documented Phase 7 contracts, not hidden
in-scope blockers. PDF/OCR/cloud storage/social providers/watch mode remain deferred.

Recommended Phase 8: provision and qualify a fully offline timed transcription
executor, then validate its retry/operability UX with this existing source authority.
