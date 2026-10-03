# V1X_PHASE6_RESEARCH_DIFF_REPORT

Phase 6 is implemented, remediated, validated and locally committed. The fresh
acceptance review found no P0, P1 or material Phase 6 P2. No merge, push or PR.
The final documentation commit follows reviewed code HEAD
`13e40baf45d721e325a1823827a16ae3710d0164`; resolve the final local completion HEAD
with `git rev-parse chatgpt/v1x-research-diff`. Its exact SHA is reported in the
owner-facing completion report, avoiding a self-referential commit hash here.

| # | Required result | Accepted outcome |
|---|---|---|
| 1 | Worktree / branch | `/Users/hua/Documents/yia-worktrees/v1x-research-diff`; `chatgpt/v1x-research-diff`. Independent clean worktree, all writes isolated here. |
| 2 | Starting HEAD | Exactly `15f720377b661164a227ba599281b81b33a1e189`. |
| 3 | Final HEAD | Completion documentation commit on the branch above; reviewed code HEAD is recorded above and in the validation manifest. |
| 4 | Phase 5 revision audit | Execution equals immutable revision. Sealed result id, canonical item identity, payload/result seals, stored original Evidence and admitted Intelligence revision dependencies are checked by the accepted historical `verify_row`. History pagination and atomic current pointer remain unchanged. |
| 5 | Reused/new components | Reused canonical hashing, packet limits, trusted historical reader, read-only database, existing API/client/source navigation and Backup/Restore. Added typed pure `research_diff.py`, a service read, GET route and in-History React comparison. No dependencies. |
| 6 | Diff product definition | Factual differences between two trusted immutable snapshots of one stable Research item. Derived, non-persisted and deterministic. |
| 7 | Base/target semantics | Caller base → target preserved, including reverse direction. Self-comparison valid and empty. |
| 8 | Trusted-revision prerequisites | Both rows individually verified in one read-only transaction before projection. Missing, corrupt, failed, unavailable, unsupported or incompatible authority fails closed. |
| 9 | Same-Research enforcement | Each requested revision must belong to the requested stable Research id; foreign base and foreign target rejected before projecting content. |
| 10 | Semantic matching/identity | Content id; durable Evidence id; canonical interpretation hash over stored Intelligence/revision/source/Content, conclusion, classification, state and sorted Evidence–stance pairs. Array position, labels and timestamps are not semantic ids. |
| 11 | Findings/packet behavior | Persisted interpretations use added/removed/unchanged. No invented changed-finding identity. Five factual packet fields may be changed: status, two candidate counts, truncation and unresolved flags. |
| 12 | Evidence/reference behavior | Separate Content and Evidence groups. Target supplies additions; base supplies removals; exact stored excerpts, ranges, languages and ids retained. No inferred strength. |
| 13 | Intelligence revision references | Separate recorded-interpretation group includes exact stored revision identity. Old→new reference becomes old removed/new added. Today's newer Intelligence is never substituted. |
| 14 | Insufficient transitions | Both insufficient→available and available→insufficient represented with deterministic status/reference changes. |
| 15 | No-material-change behavior | Identical reruns and self-comparison show a legitimate localized no-change state. Execution ids, timestamps, result seals and context labels do not fabricate changes. |
| 16 | Ordering/determinism | Sorted authoritative ids/hashes, canonical paired citations, sorted unresolved flags and fixed packet-field order; deterministic React ids. Repeated HTTP bytes match. |
| 17 | Bounds/pagination | Complete comparison of accepted bounded snapshots: per side 20 Content, 24 Evidence, 6 interpretations, five changed packet fields. No Diff pagination or silent subset; retrieval truncation remains explicit. History remains 25/page. |
| 18 | API | GET `/api/v1/research/{id}/diff?base_revision=…&target_revision=…`; typed `research-diff-v1` envelope. Stable 404 missing-item/base/target, 409 foreign/untrusted/incompatible, 422 malformed request. |
| 19 | Frontend UX | Inside Research detail/History only. Current→compare with previous resolves previous as base/current as target; historical→compare with current. One-version state has no previous action. Explicit deep route reloads correctly. Six accepted navigation destinations. |
| 20 | Source tracing | Stored side-specific Content/Evidence ids and own Research revision links. Intelligence link explicitly says it opens current state; exact recorded revision remains displayed and inspectable in its own Research packet. |
| 21 | Localization | Complete zh-CN/en labels, machine errors and enum presentation. Original question/conclusion/Evidence content and accepted output language remain intact. |
| 22 | No persistence | No Diff table/cache/current pointer, execution, backup member, Research provenance, Intelligence evidence, Knowledge Delta fact or Obsidian artifact. HTTP/database dump equality proves no mutation. |
| 23 | Migration/schema | Schema 31; migration lineage and all SQL hashes unchanged. No migration 032. |
| 24 | Backup/Restore | Unit/integration and real HTTP backup/stage/confirm/restart/restore recompute equivalent changed and no-change A/B with exact same revision ids. |
| 25 | Security | Three ids validated as lowercase 64-hex; bound SQL; owner checked; duplicate/unknown/missing parameters rejected; safe machine errors; no raw persisted JSON or diagnostics. |
| 26 | No-model/cloud/web | Pure projection has no provider/retrieval imports. Real retrieval, DA/distillation execution and outbound socket/HTTP entry points guarded by tests. Browser logs have zero external requests. |
| 27 | Adversarial validation | All 42 owner requirements mapped below; 46 final backend Diff cases and 15 frontend cases, plus real browser, HTTP, DB and preservation evidence. |
| 28 | Phase 5 regression | All Research backend tests pass; inherited History/browser behavior passes in eight locale/width flows, including rerun append and exact historical opening. |
| 29 | Phase 4 regression | Deterministic bounded packet, identity, explicit scope, insufficient material and stored authorities preserved. Final Research backend suite: 155 passed. |
| 30 | Integrated regression | 761 focused integrated backend cases passed; eight integrated browser flows cover DA production NONE, durable Evidence, no-result, Obsidian publication and Home Knowledge Delta. Full backend includes all integrated tests. |
| 31 | Full backend count | 3,270 passed, one unchanged optional canonical o200k asset skip, two expected fixture warnings; 475.41 seconds. No added skip or weakened assertions. |
| 32 | Frontend count/build | 163 passed; typecheck and production build passed. |
| 33 | Browser/E2E | Eight Phase 6 flows plus eight after HTTP restore, four corrupt-side flows, eight inherited Research/History flows and eight integrated flows. zh-CN/en at 320/768/1024/1440; no normal console errors, no overflow, no external requests. Deliberate missing/corrupt HTTP resource errors are separately asserted. |
| 34 | Static/docs checks | Ruff, strict mypy (78 source files), compileall, baseline/working diff checks, designmd lint and documentation structure/link lint passed. |
| 35 | Database checks | Schema 31; quick_check/integrity_check both ok; foreign_key_check empty; only research_items/research_results; zero Diff tables; restored migration lineage/checksums match accepted base. |
| 36 | Phase 5 preservation | HEAD `15f720377b661164a227ba599281b81b33a1e189`; clean; 990 file fingerprints unchanged. |
| 37 | Phase 4 preservation | HEAD `22ea84a79bba3f27566a221e774c93c3cc797a4f`; clean; 983 file fingerprints unchanged. |
| 38 | Integration preservation | HEAD `ba9f27fd2869e24a0b30e58f3ef6e5e29c747a7b`; clean; 964 file fingerprints unchanged. |
| 39 | M13 preservation | HEAD `e228294f705401b0200439076c3378b78f9c9d84`; original 35 dirty/untracked entries and 915 file fingerprints unchanged, including migration 029. |
| 40 | Commits | `20decda` domain/API/tests; `e979e1a` History comparison/localization/browser validation; `13e40ba` strengthen actual no-dispatch entry guards; final scoped acceptance-documentation commit. |
| 41 | Genuine blockers | None. Unchanged optional asset test remains skipped because its canonical asset is not provisioned; no external download performed. No material review finding remains. |
| 42 | Recommended next step | Owner may close the V1.x Advanced Intelligence milestone; any integration merge/release is a separate authorized task. |

## Adversarial acceptance mapping

The domain/API tests exercise the actual immutable validator and parameterized
repository read. Pure projection tests additionally isolate ordering/identity
rules at maximum bounds. Browser fixtures use real API/UI and disposable databases
inside this worktree; they do not mock Diff or bypass revision trust.

| Owner case | Evidence |
|---|---|
| 1 One revision | Frontend one-version test; all eight browser flows have no previous action. |
| 2 Two trusted revisions | Current/previous frontend and real browser; trusted identical reruns domain test. |
| 3 Three revisions/direction | API reverse and arbitrary A/B; three-revision browser flows. |
| 4 Self comparison | Domain/API deterministic empty result; browser self comparison. |
| 5 Cross Research | Real trusted rows of two items rejected. |
| 6–7 Missing base/target | Separate API/domain machine-code assertions; localized missing browser state. |
| 8 Foreign base | Owner check before trust/projection, real foreign rows; foreign target also covered. |
| 9–10 Corrupt base/target | Parameterized corruption cases and four real browser corrupt-side flows. |
| 11 Execution metadata noise | Real rerun seals/execution ids differ while material projection remains empty. |
| 12–13 Evidence addition/removal | Real recorded snapshot transitions; browser reference sections both directions. |
| 14–15 Evidence/Content ordering | Actual trusted reordered packet and canonical projection permutation tests. |
| 16–17 Intelligence ref addition/removal | Real admitted stored interpretation snapshots in both directions. |
| 18 Newer Intelligence today | Stored A/B unchanged despite later revision not used by either packet. |
| 19 Stored old/new Intelligence revisions | Legitimately appended Intelligence revision/card/dependencies; old removed/new added. |
| 20 Current advances | Real third revision and corrupt newer current leave explicit old A/B unchanged. |
| 21 Later Evidence | New durable Evidence after A/B does not change stored comparison. |
| 22–24 Question/scope/language | Corrupted same-owner immutable rows rejected; projection compatibility independently guarded. |
| 25–26 Insufficient transitions | Real trusted available/empty packets tested in both directions. |
| 27 No change | Reruns, self, frontend and real browser empty states. |
| 28 Large bounded packet | 130 candidates retain accepted 24 limit; disjoint maximum24/24 projection complete. |
| 29 Stable sorting/ties | Equal-context-label data and array/citation permutations; sorted authoritative ids/hash tie-breakers. |
| 30 Backup restore | Exact changed Diff through real backup restore; real HTTP restore and all eight browser flows repeated. |
| 31–35 No DB/product mutation | Whole-database iterdump equality before/after Diff covers Research, Intelligence, Topic and Knowledge Delta, plus real repeated HTTP read equality. |
| 32 No Research rerun | Actual `_terms`/packet assembly entry guards during read; no current/library scan in implementation. |
| 36–37 No provider/web | Actual DA/distillation execution guards, socket/HTTP guards and browser external-request assertions. |
| 38–39 zh-CN/en | Frontend localization tests and both languages in real browser, including corrupt errors. |
| 40 Mobile | All four widths in both languages, overflow assertions and inspected screenshots. |
| 41–42 No Diff table/migration | Restored sqlite schema, accepted SQL hashes, baseline git diff and backup member inspection. |

## Review and remediation

Semantics review directly inspected matching and the trusted row path. Execution
metadata is outside changes; identity/scope/language mismatches fail closed;
canonical citation pairing prevents order noise. No current pointer, today's
source selection, strength inference or generated interpretation enters Diff.

Authority/product review directly inspected GET routing, revision ownership and
verification, historical source navigation, bounded first-page previous selection,
reload state, empty/error states and both language dictionaries. UI content derives
only from the two projected stored packets. The existing Intelligence destination
opens current state and is explicitly labeled; own Research revision/citation
controls preserve exact historical inspection. No unbounded History scan.

Fresh acceptance review inspected every Phase 6 production/test/doc change against
the exact accepted Phase 5 base, not just test names. No persistence/dependency/
migration/auth/backup/Knowledge Delta implementation was introduced or modified.
Two integrated fixture path guards only admit this task's isolated worktree roots;
existing browser assertions are retained. The existing absent-Diff API assertion
now asserts the newly supported route's missing-parameter error, not a weakened
test. Review result: zero P0, zero P1, zero material Phase 6 P2.

Material intermediate failures were fixed and retested rather than waived:

| Check / key failure | Affected scope | Remediation / passing evidence |
|---|---|---|
| Frontend typecheck: TS1117 duplicate translation property | uiLanguage.tsx | Reused accepted existing label; final typecheck/all163/build pass. |
| Newer-reference test: CARD_HASH_INVALID, then immutable citation-link mismatch | test_research_diff.py fixture | Constructed a legitimate appended revision with exact card hash and dependency links; final46/155 pass. Accepted validator unchanged. |
| HTTP backup: missing/unsafe fixture DATA authority | research_diff_fixture_server.py | Materialized exact source bytes/hash inside isolated root; real HTTP restore equivalence passes. |
| Browser source roundtrip: deep-analysis 404 | Phase 6 HTTP fixture | Wired accepted production-NONE read service; eight normal/restore flows pass with zero console errors/provider dispatch. |
| Integrated Obsidian publication timeout | v1x_integration_fixture_server.py | Resolved isolated fixture root to absolute path; fresh integrated fixture passes all eight flows. Failed evidence retained locally. |
| Review found no-dispatch guard named a nonexistent helper; correction initially raised ModuleNotFoundError | test_research_diff.py | Guarded actual `_terms`, DeepAnalysisService.run and PersonalizedDistillationService.distill using the real distillation module; final46/155 pass. |

## Validation commands and evidence

Commands run from this worktree using the pre-existing interpreter at
`/Users/hua/youtube-intel/.venv/bin/python` and current `PYTHONPATH=src`:

```text
python -m pytest --basetemp=.var/phase6/full-pytest tests -q
python -m pytest tests/integration/test_research_diff.py tests/unit/test_research_diff_api.py tests/unit/test_research_diff_projection.py -q
python -m pytest tests/integration/test_research*.py tests/unit/test_research*.py -q
ruff check src tests
mypy --strict src
python -m compileall -q src tests
npm --prefix frontend run typecheck
npm --prefix frontend test -- --run
npm --prefix frontend run build
git diff --check 15f720377b661164a227ba599281b81b33a1e189 HEAD
designmd lint frontend/src/workspace/DESIGN.md
```

Full backend ran once on the final production implementation. The later guard-only
test correction was independently revalidated by all46Diff/all155Research and
static checks. No production change followed the full run. The unchanged optional
skip is `test_o200k_provisioning.py:134`; fixture warnings are duplicate ZIP-path
and deliberate invalid-enum serialization fixtures. No new skip or external asset
provisioning. The integrated focused suite log records its passing counts and warnings.

Committed [validation manifest](V1X-PHASE6-VALIDATION.json) records counts, review
outcomes and SHA256 fingerprints of local evidence. Detailed logs, database
reports, HTTP backup/restore evidence, screenshots and protected before/after
fingerprints remain in `.var/phase6` (ignored test artifacts). The decision record
is [V1X-PHASE6-DR-001](../docs/decisions/V1X-PHASE6-DR-001-research-diff.md).

V1X_PHASE6_RESEARCH_DIFF_FULLY_COMPLETE_V1X_ADVANCED_INTELLIGENCE_MILESTONE_MAY_CLOSE
