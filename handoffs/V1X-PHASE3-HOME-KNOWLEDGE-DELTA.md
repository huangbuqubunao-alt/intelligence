# V1.x Phase 3 Home Knowledge Delta acceptance

Dedicated worktree: `/Users/developer/Documents/yia-worktrees/v1x-knowledge-delta`.
Branch: `chatgpt/v1x-knowledge-delta`. Exact accepted Phase 1B base:
`432f085d76824dfa51a447622aa2dba23ff8bfc8`.
Implementation commit: `eb59e7859693a2478d2b1bd3baf65c99fca2caf4`.
No merge, push, PR, deployment, dependency change or migration was performed.

Decision authority is `docs/decisions/V1X-PHASE3-DR-001-home-knowledge-delta.md`;
visual reference is `frontend/src/workspace/DESIGN.md` (designmd lint passed).

## Implemented behavior and source authority

One Home section answers the frozen Chinese/English seven-day question. It
computes a typed local GET projection from one read-only SQLite snapshot, with
five fixed SELECTs and no per-item DB calls. There is no Delta table, persisted
output, watermark, cursor, unread marker, primary navigation entry or model call.
The interval is closed `[now UTC - 168 hours, now UTC]`; one injected aware clock
is used once. Dates display in the application's configured timezone, default
Asia/Shanghai. Exact UTC normalization preserves offset/microsecond boundaries;
malformed, naive and future event timestamps are excluded.

Completed Content uses `completed_at`, with real `discovered_at` ordering;
unfinished discovery is excluded. `videos.created_at` does not exist and is not
used. Revision 1 is Intelligence admission. Later revisions are grouped once
per identity, with additional revisions disclosed for newly admitted identities
without counting them again under revisions. Evidence membership comparison
detects set replacement as well as count changes. Explicit meaningful recorded
state transitions are historical facts; lifecycle NEW/UPDATED is not a feed.
Incomplete recent revision structure makes Intelligence unavailable, not zero.
This metadata reader does not issue generated conclusions; existing sealed
object readers retain that authority when a user navigates to an object.

Topics use only real active Topic timeline/membership/revision/Evidence
relationships. Compatibility `knowledge_graph.topics` and renames/pins are
inert. Enabled channel sources show bounded explicit checking failure or at
least two consecutive proven blocked discoveries, followed by proven recovery
of checking when supported. Model/guard/budget/child noise is excluded. Recovery
does not imply new Content resumed; ordinary later success does not erase it.

Counts are exact per category. At most two items per category, ten overall, are
returned/rendered; contextual titles are limited to 240 characters. Categories
have fixed order; items sort latest occurrence then stable entity identity.
Source events also use immutable event identity for equal-instant ties.
Local GET `/api/v1/knowledge-delta` exposes window, availability, typed categories,
fact metadata and existing navigation targets. Query failures yield explicit
partial/unavailable status with null counts and no private SQL/error prose.
Successful zero changes is a legitimate localized empty state. Loading and
retry are localized. Both languages and real object target navigation work;
the six existing primary navigation buttons remain unchanged.

Backup/Restore has no new schema authority or archive entry. Underlying records
recompute the projection with the same clock. The connection uses URI `mode=ro`
plus query-only transaction protection; an absent DB is not created by reading.

## Review and remediation evidence

Review 1 inspected SQL, revision authority, real timestamps, grouping, localized
labels, original Home hierarchy and navigation. Remediation covered exact UTC
normalization, 168-hour DST behavior, classification by actual revision admission,
Evidence set comparison, truthful historical states, structural authority checks,
namespaced object IDs, and preservation of recovery after ordinary checking.
Raw job/row activity, unsupported personal-belief claims and compatibility Topic
authority are absent. Unsupported pinned-Topic “since last checked” copy was
replaced with factual “Pinned Topics”.

Review 2 inspected real SQLite projections and actual Chrome screenshots for
empty/one/many/mixed/revision-heavy/source-failure/recovery/boundary/partial/
unavailable cases, in both languages and four widths. No overflow, raw status
enum, product-English leak in Chinese, external request or console warning/error
was observed. API failure remains distinct from empty state. Additional
adversarial fixes proved a concurrent writer cannot mix snapshots and a missing
database read cannot create authority accidentally.

Final source review found an equal-instant source failure/recovery tie. Reproduced
with `PYTHONPATH=src python -m pytest tests/integration/test_v1x_knowledge_delta.py::test_same_instant_failure_and_recovery_use_event_identity -q --tb=short`:
`AssertionError: 'Source discovery repeatedly blocked' != 'Source checks resumed'`.
Added event-identity sorting, preserving the assertion; all 28 focused tests then
passed. A new retry test initially failed TypeScript TS2769 because role queries
do not accept `exact`; removed that unsupported query option without changing the
exact accessible-name assertion. Frontend typecheck and all 111 tests then passed.
Browser harness timing/modal-close issues were corrected in the harness; product
assertions were retained. No test/assertion was deleted or skipped to hide errors.

## Required adversarial matrix

| Owner case | Evidence |
| --- | --- |
| 1 Empty window | Real SQLite empty result, frontend and both-language Chrome empty state |
| 2 Just before start | One-microsecond exclusion |
| 3 Inclusive start/end | Both exact endpoints included; browser boundary case |
| 4 Future corruption | Future Content/revision/source events excluded |
| 5 Equal timestamps | Content/Topic/source entity ties; source failure/recovery event-identity regression |
| 6 Uncompleted discovery | Explicitly excluded rather than fabricated as admitted knowledge |
| 7 Completed Content | COMPLETE plus actual completion timestamp included |
| 8 New Intelligence | Revision-1 admission, empty identity excluded |
| 9 Revision creation deduplication | New identity plus subsequent revisions counted once |
| 10 Many revisions | Coalesced per identity, deterministic last revision and bounded details |
| 11 State noise | NEW/UPDATED suppressed as separate events; meaningful historical state localized |
| 12 Authoritative relationships | Real cross-Content/Topic membership test, no heuristic assignment |
| 13 Compatibility Topics | Model JSON/knowledge_graph topics alone yield no Topic change |
| 14 Source failures | Repeated discovery proof, explicit checking error, noise/disabled source exclusion |
| 15 Recovery | Proven failure sequence plus completion; ordinary success preserves historical recovery |
| 16 Determinism | Same DB/clock structure equivalence and stable ties |
| 17 Restart | New repository connection recomputes identical mixed-authority projection |
| 18 Restore | Real BackupRestoreService archive round trip plus SQLite dump reconstruction |
| 19 Chinese | Unit/UI and 40 Chrome cases, no raw enums or English product copy |
| 20 English | Unit/UI and 40 Chrome cases, correct labels/navigation |
| 21 Large dataset | 10,000 records: five SELECTs, exact count, at most ten total details, title limit |
| 22 No persistence | Schema remains version 30, no Delta/watermark tables, no write statements |

Additional proof covers normalized legacy offsets, naive/malformed dates, DST,
one clock call, missing/incomplete authority, private diagnostic suppression,
query failure/transport retry, and concurrent snapshot isolation.

## Validation and reproduction

Use the existing Python environment `/Users/developer/youtube-intel/.venv/bin/python`
with `PYTHONPATH=src`; frontend uses the existing dependency versions. No package
installation, lockfile edit or production dependency upgrade was required.

| Check | Result |
| --- | --- |
| Phase 3 integration + API | 28 passed |
| Phase 1B authority/backup/migration/contracts | 65 passed |
| Shared state-connection regression (earlier scoped pass) | 70 passed |
| Full backend before final tie remediation | 3018 passed, one existing optional tokenizer-asset skip |
| Final implementation backend, offline tokenizer asset supplied | 3020 passed, zero skipped; 375.76 seconds |
| Frontend `npm run typecheck` | Passed |
| Frontend `npm test -- --run` | 111 passed (72 workspace, 7 Delta, 32 demo) |
| Frontend `npm run build` | Passed |
| Phase 3 Chrome | 80 scenarios + 8 object navigations; zero external requests/console errors or warnings/overflow |
| Phase 1B Chrome | 16 scenarios passed |
| Ruff `check src tests scripts` | Passed |
| Strict mypy `--strict src` | 70 source files passed |
| compileall `-q src tests scripts` | Passed |
| `git diff --check` | Passed |
| designmd lint | Zero errors/warnings |

The standard full suite's conditional tokenizer test requires an explicitly
provisioned canonical asset. An already installed offline copy was SHA256 checked
(`446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`), copied
into a disposable test directory and supplied through the test's existing
`YOUTUBE_INTEL_O200K_TEST_ASSET` seam. Its eight provisioning tests passed, with
no download, model call, production file or test-policy change. Final full-suite
run uses the same asset. Existing warnings are adversarial duplicate ZIP path and
Pydantic invalid-enum fixtures; frontend's existing Chinese Deep Analysis failure
test emits React act harness warnings. These do not occur in the real browser.

To reproduce browser evidence, run `PYTHONPATH=src python scripts/phase3_delta_browser_fixtures.py`,
start the local Vite UI on 5293, and run `node frontend/v1x-phase3.e2e.mjs`.
Temporary screenshots/result JSON are under `/tmp/v1x-phase3-browser`; requests
are intercepted locally using real SQLite/service Delta projections and synthetic
existing-object responses. This is not a live production-data exercise.
The 10,000-record local read benchmark took 83–85 ms over five reads, returning
1,466 serialized bytes (environment-specific evidence, not an SLA).

## Parallel worktree preservation and integration

Only this dedicated Phase 3 worktree and disposable test artifacts were written.
Before/after read-only HEAD/status/file-hash snapshots were taken for all three
other worktrees. M13's HEAD/status/file hashes are identical (zero changed files).
Phase 1C advanced independently from `31c2ff59b594ca15b8f5e38ba813b0e81bed0abe`
to `d8ec069f4798a443166d270adcba8eb078fcde06` with 18 changed files; Phase 2
advanced independently from the accepted base to
`b9362fb64d1f87ec8cfd19972f5f2abd64f6bf6a` with 17 changed files.
Those are parallel development observations, not Phase 3 writes. Their legitimate
work was not reset, modified, merged or used as a dependency.

Integration must reconcile ordinary shared App/API/localization edits. The Phase 3
decision identifier is phase-scoped to avoid parallel decision-number ambiguity.
There is no migration ordinal collision: Phase 3
adds no migration and does not allocate 031. Historical V1 specs were not rewritten.

Fresh acceptance reviewed the complete diff from accepted Phase 1B through the
implementation commit, including SQL/service/API/UI behavior and all test fixtures,
then the final documentation-only decision identifier and acceptance record.
All 22 completion criteria are satisfied; no unresolved P0/P1/material P2 defect,
product decision or genuine blocker remains. Integration may proceed; nothing
was pushed or merged.
