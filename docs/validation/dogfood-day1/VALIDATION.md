# Intelligence Dogfood Day 1 acceptance

Starting main and origin/main: `943bc05bbc0c20e5d2f8e92c8358aa6e3e988981`.
Isolated branch: `codex/dogfood-day1-fixes`. Initial product implementation was
frozen at `758a050`; its evidence commit `e7d7b64` changed no application code.
The post-adoption launcher restart correction below remains in this same goal.

## Final checks

| Check | Result |
| --- | --- |
| `PYTHONPATH=src .venv/bin/python -m pytest -q` | 3896 passed, 1 existing optional-asset skip, 2 fixture warnings; 763.78s |
| Focused final backend | 45 passed; 21.93s |
| Independent review regressions | 283 passed; includes reservations, trusted orchestration, Phase 12/13 and backup |
| Frontend complete suite | 248 passed, 16 files |
| `npm run typecheck -- --pretty false` | passed (`tsc -b`) |
| `npm run build` | passed, production assets generated |
| Strict mypy | passed, 98 source files |
| Ruff `src scripts tests docs/validation/dogfood-day1` | passed |
| Compileall for the same Python scope | passed |
| `git diff --check` against starting main | passed |

The optional asset skip requires `YOUTUBE_INTEL_O200K_TEST_ASSET`; no skip was
introduced. Full-suite fixtures intentionally exercise duplicate ZIP entries and
Pydantic validation bypass, producing the two existing warnings. An earlier
entry-point invocation `.venv/bin/pytest` could not import the repository's
`scripts.phase9r_profiles`. The correct repository-root invocation
`python -m pytest` passes those tests and the entire suite; no assertions or
configuration were weakened. Earlier failures and their repairs are recorded in
PLAN.md and retained in ignored runtime logs.

An additional unscoped `ruff .` finds 39 pre-existing lint findings exclusively
in historical `docs/validation/phase13` scripts. Those archived scripts are
unchanged from the starting revision. Production code, tests, launcher and new
Day 1 validation scripts pass Ruff. Historical script cleanup is deferred.

## Real local and browser evidence

`live-validation.json` uses a fresh isolated database, normal production runtime
composition, real public provider requests and no cloud credentials. It proves:

- A YouTube single-video request immediately has durable Content identity, then
  real metadata, timed transcript, readable Summary and source references.
- `@3blue1brown/videos` resolves to named tracked Following. Its completed
  baseline has 15 observations, zero historical Content links, a tracking state
  and a future background check. Pause and resume use the existing scheduler.
- Bilibili public-video import returns real metadata and an actual title.
  Captions remain unavailable; there is no creator Following or ASR fallback.
- Manual extraction on organized Content returns a durable waiting-model result
  with invocation count zero. Content remains completed. No Intelligence or
  Topic is fabricated.

The initial public channel resolution briefly returned external HTTP 429.
Read-only accepted-main probing encountered the same provider condition. A
later candidate request resolved successfully without a networking code change.
External provider availability is not forced by application code.

`browser-validation.json` and screenshots prove compact Settings language
Edit/Save, closed Advanced disclosure, unified Add recognition and default
Content-only policy in zh-CN/en at 320px and 1440px. Two local-file imports
succeed. No horizontal overflow, browser errors or unexpected external browser
requests were observed. `browser-following-content.json` proves real manual
waiting feedback, actual channel names, direct row pause/resume and accessible
legacy-source inspection in both languages. Its final rerun follows the final
frontend build. Screenshots use viewport capture; the separate viewport/scrolled
Settings images disambiguate a Chrome full-page capture artifact.

Public transcript and Summary text are not committed: the live evidence stores
hashes, lengths, cue counts and reference counts. Runtime databases remain in
the ignored isolated `.var` tree.

## Owner evidence and migration

`owner-before.json` records the preserved Day 1 physical snapshot. Validation
uses copies exclusively. `owner-copy-validation.json` proves normal supported
application startup migrates 34 to 35, integrity remains `ok`, every historical
Source field is identical, and all table counts are unchanged except the added
migration record. The old unresolved `@lingdujieshuo` Source remains visible as
needs attention with no tracking state and no Content. The bilingual browser
inspection uses that copy, never the real owner database.

Schema 35 is necessary because schema 34's no-new-result trigger incorrectly
includes Summary-derived EXTRACTION evidence in the canonical transcript set.
The migration replaces only that trigger with the exact ORIGINAL_TRANSCRIPT
set; no table, Source or historical data is rewritten. Upgrade, restart,
rollback, schema history and backup/restore compatibility are covered.

`protected-after.json` exactly equals `protected-before.json` for all eight
protected worktrees (HEAD, complete status, binary diff and staged diff hashes).
Only the isolated candidate is developed. Owner startup after adoption is the
only authorized real-owner migration; subsequent verification uses safe GETs.

## Fresh self-review and fixes

The final review asks the frozen product questions and checks persisted
authority against presentation. A first-time user can paste a channel `/videos`
URL, distinguish continuous Following from one-time content, and discover local
files and Bilibili public import. Valid actions show real work, including failure
and retry. Baselines create no historical Content. Content succeeds without
cloud Intelligence. Model readiness distinguishes configured local runtime from
advanced candidate preferences, and explains optional cloud prerequisites.
Settings starts with consumer controls and retains diagnostics behind Advanced.

Review findings fixed before acceptance: one-time subtitle failure visibility;
bounded retry projection; non-retryable trust/capability terminals; waiting for
organized Summary before optional analysis; no full-pipeline fallback for a
missing Summary; production manual output-language sealing without forged
Scoring/relevance; localized waiting/no-new labels and actionable validation
copy. Fresh independent review approves the final guards and frontend changes.
No scoped P0/P1 remains.

Content-only never requests Intelligence. Optional and manual analysis retain
qualification, verified Evidence, reservation/budget, explicit cloud review and
confirmation, and trusted admission. Missing credentials or a qualified local
model persist a waiting state with zero dispatch. Completed no-new analysis has
an explicit result. Existing Topic updates run only downstream of admitted
Intelligence. Bilibili creator/caption/ASR restrictions and Phase 12 networking
safety remain unchanged. No dependency, credential, production configuration or
lockfile change was needed. Phase 14 remains unstarted.

The final candidate is adopted only by fast-forward after refreshing clean main
and origin. The launcher rebuilds the adopted revision automatically and binds
its served bytes to revision, frontend source digest and per-asset SHA-256.
Post-adoption equality, HTTP asset proof and safe owner GET preservation are
recorded in the final report and ignored operational adoption receipt.

Next action: **REAL-USER DOGFOOD DAY 2**.

## Post-adoption restart finding

The initial accepted candidate `e7d7b64` was fast-forward adopted, pushed and
fetched successfully. Normal owner launch rebuilt current production bytes and
stopped the two verified owned October 3 processes. Its bare socket bind
preflight then failed with `OSError: [Errno 48] Address already in use`
(`scripts/owner_launcher.py`, launch port probe). `lsof` confirmed no listener;
`netstat` showed the closed owner connections in TIME_WAIT. Startup had not yet
opened or migrated owner data.

The isolated correction uses reusable bind after a bounded no-payload loopback
connection check. Independent review found that reusable bind alone can miss a
macOS wildcard listener; this was fixed before re-adoption. Only connection
refusal permits bind, while a live listener or unexpected error/timeout fails
closed with an actionable launcher error. No unrelated process is stopped.
Eleven focused tests pass, including real TIME_WAIT, loopback/wildcard listener
refusal and timeout fail-closed coverage. Fresh independent review approves the
correction with no P0/P1. Ruff, strict mypy and diff checks pass. The final code freeze `f8c5688` passed a fresh full backend rerun: 3896 passed,
1 existing optional-asset skip, 2 fixture warnings in 763.78s. This follow-up
evidence commit changes no application code. The original 3892-pass result is
retained in backend-final.txt; backend-launcher-final.txt contains the final
acceptance run. Frontend source is unchanged from its 248-pass/typecheck/build
acceptance. Final compileall and diff checks also pass before re-adoption.
