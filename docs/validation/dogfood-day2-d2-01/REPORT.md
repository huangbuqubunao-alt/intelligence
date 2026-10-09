# INTELLIGENCE_DOGFOOD_DAY2_D2_01_FIX_REPORT

Task: D2-01 only. Phase 14 not started. Candidate is ready for conditional
ff-only adoption after the recorded gates; final adopted SHA/live provenance and
owner post-checks are recorded in the operational final report under candidate
`.var/d2-01/INTELLIGENCE_DOGFOOD_DAY2_D2_01_FIX_REPORT.md` after deployment.

1. Initial main HEAD: `ce60189f002270909e5ef234deedb61ceba19b0f`; fetched
   origin/main equal; authoritative worktree clean. No `.codegraph`; queried
   codebase-memory graph and indexed the isolated candidate. Read applicable
   AGENTS, collaboration/status/PRD/design/reuse rules. User's explicit complete
   goal authorizes this one executor's review/adoption/push/private owner update.
2. Reproduction: Following → Add Source → Import local file → select synthetic
   MP4 → return focus. Chrome on the exact accepted production build displays
   Add a Source, loses the file and sends zero upload requests (`red-browser.json`,
   `red-focus.png`). Original App plus the final valid regression test yields
   two failures (`red-tests.txt`); typecheck passed before that red run.
3. Root cause: Sources' window-focus Check Stale callback refreshes Workspace;
   `useRemote('/sources', refresh)` sets data null. Sources returns a Loading
   element and unmounts SourceForm/AddEntry/LocalImport. `adding` survives in
   Sources while AddEntry's `local=false` and selected File state reset on
   remount. During an active POST, the same unmount loses visible progress and
   results even though the request continues. No actual route-to-channel or
   backend-as-channel bug was found. Native chooser confirmation and product
   Confirm import are separate: focus can reset the flow before the POST; the
   delayed-upload regression also covers reset after the POST starts.
4. Fix: own AddEntry and its provider choice in Workspace, outside page loading
   returns and page navigation. Local library row/detail imports use that same
   stable modal. Local admission passes a distinct onImported(contentId) callback
   and navigates only after the sequential batch settles. Retain mixed/invalid
   selection outcomes. Add a synchronous submit ref and failed-only retry.
5. Changed production files: frontend/src/workspace/App.tsx, AddEntry.tsx,
   LocalImport.tsx, uiLanguage.tsx. Tests: AddEntry.test.tsx, LocalImport.test.tsx,
   new LocalImportFlow.test.tsx and tests/integration/test_dogfood_day2_local_import.py.
   Evidence: this directory and handoffs/DOGFOOD-DAY2-D2-01.md. No backend,
   schema/migration, launcher, dependency, lockfile, auth or production config edit.
6. Complete call chain: Following/Add or Local library → Workspace AddEntry →
   LocalImport File input/explicit Confirm → `api` with File body,
   application/octet-stream and X-YIA-Request → POST
   `/api/v1/local/imports?filename=...` → LocalApiApplication.handle →
   LocalContentProvider.import_bytes/_import_bytes → format/size/UTF-8 or ffprobe
   validation, SHA-256 identity/dedup → managed immutable source snapshot → local
   library Source, videos Content row, source_video_links, artifact and
   content_source_snapshots persisted → truthful processing status. Ready text
   uses SourceContentPublisher._persist_source_result/_finish_summary and the
   existing extractive Summary/Evidence path. Media without a provisioned
   transcriber keeps TRANSCRIPTION_UNAVAILABLE. API returns 201/200 after
   persistence → onImported → Workspace Content target → `/videos` plus
   `/videos/{id}` → existing Content projection/LocalTranscription reads.
7. Correct navigation: all-success batch automatically opens first saved Content
   Detail, refreshes the list and closes the add modal. Other batch items remain
   in Content. Mixed batches retain individual errors/results and explicit
   Open Content/Done; successful items are not retried. Importing has a polite
   status message. No success routes back to Add Source.
8. Persistence: 10 synthetic real UI admissions (4 video, 2 audio, 4 text) produce
   exactly 10 verified snapshots/Content rows, one LOCAL library, zero tracking
   state. Schema 35, integrity ok, foreign-key check empty (`persistence.json`).
   Restarted normal isolated API reads all 10 with names/states unchanged
   (`restart.json`). New API tests prove 201 first/200 duplicate, same ID and one
   durable row. Invalid media creates no Content.
9. Processing feedback: Content announces "File imported. Its processing status
   appears below." It renders real read-model state, including Missing model
   with explicit no-automatic-download explanation, unprocessed Summary/Evidence,
   live Transcribing, processing failure and reason. File upload success never
   fabricates completed analysis or Intelligence. Processing failure retains
   the admitted Content.
10. Duplicate protection: synchronous ref before POST; disabled selection,
    cancel/provider/confirmation during upload; no mid-batch Open Content links;
    saved files excluded from retries; SHA-256 backend dedup unchanged. Returning
    to Content or reloading does not repeat POST. Explicit later re-import remains
    supported/idempotent. Browser refresh/new-document interruption is not an
    in-memory resume claim; backend persisted records/dedup remain authoritative.
11. Errors: bounded bilingual API-code copy; no private backend prose. Failed
    bytes retained for explicit Retry failed files; mixed outcomes remain visible;
    invalid selections are retained rather than hidden by successful items.
12. New tests: 16 frontend cases and 6 backend cases. The two stable App regressions
    fail on original App and pass repaired App; test File bytes, focus refresh,
    in-flight page changes, automatic Content, live status, synchronous double
    click, rerender, failed-only retry, invalid-selection retention, no mid-batch
    navigation, bilingual errors and one-video provider non-enrollment.
13. Related regressions: 208 backend tests cover Local Provider/adversarial/media,
    transcription, mixed provider/Bilibili, YouTube Following, Local API/Content
    projection, Day 1 intelligence/migration/product and owner launcher. Focused
    frontend after review: 160 passed (52 local/Add/transcription + 108 App).
14. Full frontend: 268 passed in 17 files (`frontend-full.txt`).
15. Full backend: 3,896 passed, 1 existing optional-tokenizer-asset skip and 2
    expected fixture warnings, 793.31s (`backend-full.txt`). Collection happened
    before the 6 new cases were added; those separately pass after final edits
    (`backend-d2.txt`) and within the 208 focused run. This is 3,902 passing
    distinct backend cases, without pretending the new six were in that initial
    full-suite collection. Production backend source is unchanged.
16. TypeScript/typecheck, production build, Ruff src/tests and strict mypy src
    (98 files) pass; diff --check passes. Extra optional strict mypy including
    unchanged scripts/owner_launcher.py reports 2 baseline errors (uninstalled
    yaml stubs; paths annotation), reproduced on original main; not fixed or
    suppressed. No dependencies were installed. Jev returned HTTP451; routing
    remained the existing default. No checks/test assertions were weakened.
17. Real UI: Chrome headless executes 12 scenarios against real production UI,
    normal runtime composition, real File POST/ffprobe and isolated SQLite;
    credentials injected as an explicit empty test store. zh-CN/en × 1440/320
    video paths validate chooser-return focus and focus during delayed real POST,
    one request after repeated Enter, automatic detail, real filename, missing
    model, reloaded Content list and no page/dialog horizontal overflow. Both
    languages also exercise TXT/MD/WAV and malformed-video API/UI errors. Zero
    unexpected page/console errors/external browser requests; 2 expected HTTP422
    console messages retained. Screenshots visually reviewed. Running/failed
    transcription projections use deterministic tests, not real qualified ASR;
    no model download or cloud call occurred. External YouTube/Bilibili checks
    are fixture regression, not renewed live-provider qualification.
18. Real owner protection: all imports target ignored isolated roots/pytest temp
    databases and synthetic bytes. Owner initial/pre-adoption reads show zero
    videos/local snapshots/artifacts, no test media. Owner is actively in use:
    source/check/run metadata changes include concurrent MANUAL_CHECK_NOW runs,
    so no assertion that every live table is byte-identical. Existing source
    count and owner files remain; historical protected-worktree fingerprints
    match. No real record was manually altered/deleted or environment reset.
19. Self-review: no scoped P0/P1; fixed discovered mid-batch navigation and invalid
    selection feedback gaps before acceptance. Independent reviewer d2_review
    APPROVE, no P0/P1/P2, independently typechecked and reran 52 focused frontend,
    6 backend and diff checks. P3 all-scenario browser listener gap fixed and
    final 12-scenario rerun passed. Browser script setup issues were preserved
    locally: response-body eviction addressed by forwarding/capturing the real
    response before fulfillment; two same-document hash navigation timeouts
    addressed with actual Following button navigation. No owner test side effects.
20. Final commit: adoption HEAD in the operational final report.
21. Main HEAD: verified at adoption in the operational final report.
22. origin/main HEAD: fetched/push verified equal at adoption, no force push.
23. Frontend consistency: existing Day 1 owner launcher rebuilds adopted revision,
    binds frontend source digest and asset SHA-256 in build-provenance.json;
    served HTTP bytes must match that manifest and launcher receipt. Final
    operational report records measured equality, not just a build success.
24. Product: http://127.0.0.1:5488/; API http://127.0.0.1:5489/. Owner verification
    uses GETs only; launcher restart is the supported authorized update path.
25. Handoff: only after final adoption/provenance/owner checks pass return
    D2_01_FIXED_READY_FOR_USER_RETEST, then stop. Otherwise genuinely blocked;
    never start other Day 2 tasks or Phase 14.

Reproduce isolated UI evidence: generate-media.py; PYTHONPATH=src .venv/bin/python
server.py <candidate>/.var/d2-01/<new-isolated-root>; Vite preview on 18977 with
YIA_API_BASE=http://127.0.0.1:18975; node browser-validation.mjs. Each acceptance
run starts a new isolated test root, retaining failed-run databases for evidence.
DIRECT existing React/testing tools/provider/SQLite/launcher; no external code
copied. DESIGN.md is the unchanged existing persistent visual reference.
