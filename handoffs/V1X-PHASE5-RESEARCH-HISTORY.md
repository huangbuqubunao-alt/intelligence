# V1X_PHASE5_RESEARCH_HISTORY_REPORT

Sole executor: Codex. Completed under the owner's continuous Phase 5 goal.
The final documentation commit contains this report and the validation manifest;
its exact SHA is recorded in the final conversation response. Reviewed code HEAD:
`e8ab0dc7e0d50e755ec8523a885f893f3daa2a27`.

| # | Acceptance item | Result |
| --- | --- | --- |
| 1 | Worktree / branch | `/Users/developer/Documents/yia-worktrees/v1x-research-history` / `chatgpt/v1x-research-history`; independently created clean. |
| 2 | Starting HEAD | Exactly `22ea84a79bba3f27566a221e774c93c3cc797a4f`. |
| 3 | Final HEAD | Final report-only commit; resolve `git rev-parse chatgpt/v1x-research-history`. Reviewed implementation SHA above. |
| 4 | Phase 4 persistence audit | `research_items`: semantic input + current pointer. `research_results`: immutable execution, sequence, canonical packet, payload hash, result seal and aware UTC timestamp. Packet includes exact scope/language/contract/Evidence/recorded Intelligence provenance. |
| 5 | Execution == revision | Yes. Existing execution is the authoritative revision; existing result identity is the public revision id. |
| 6 | Reuse / new components | Reuse schema 031, transactions, packet validator, batched Evidence resolver, recorded Intelligence reader and archive verification. Add bounded History service/API, section/types/copy, tests and decision record. |
| 7 | Stable Research identity | Unchanged canonical contract + trimmed exact question + sorted/deduplicated selected Content + configured output language. |
| 8 | Revision identity | Existing sealed `result_identity`; random execution id and unique per-item execution sequence remain unchanged. |
| 9 | Current pointer | Existing composite FK and single transaction; trusted append plus pointer advance commit together. Current reads still reject invalid/regressed pointers without fallback. |
| 10 | Rerun | Same semantic item, new immutable revision; one collection item. Configured language changes retain accepted distinct-item semantics. |
| 11 | Failed/corrupt execution | Failed/corrupt new persistence rolls back; no failed History row. Corrupt old contents excluded with page-local unavailable count; valid unrelated history remains readable. |
| 12 | Trusted History read | Reuses complete row/contract/semantic/result/execution/timestamp/scope/reference/provenance checks. No row-existence-only trust. |
| 13 | Historical authority snapshot | Exact stored packet and own references. Later Intelligence revision cannot rewrite it; unavailable Evidence rejects read rather than reconstructing or substituting. |
| 14 | Ordering | Unique immutable execution sequence descending, deterministic across timestamp ties and clock changes. Timestamp-first display, no renumbering. |
| 15 | Pagination | 25 candidate rows plus lookahead; Research-bound stateless anchor/before-sequence cursor, `has_more`, `next_cursor`. Corrupt pages advance; reruns do not shift later pages. UI replaces pages. |
| 16 | API | GET `/api/v1/research/{id}/history` and `/history/{revision_id}`. Explicit historical packet plus separate `is_current` context. Phase 4 current response unchanged. |
| 17 | Frontend UX | Minimal History section inside Research detail; bounded localized metadata and source navigation. Six primary destinations preserved. |
| 18 | Current / historical | Explicit headings, read-only historical packet, return to current, restartable deep routes. Same-entry reopening preserves loaded contents. |
| 19 | Localization | zh-CN/en controls, states, metadata and errors; original source text/language names remain accepted source context. No backend enums/diagnostics displayed. |
| 20 | Persistence / migration / schema | No new table or migration; schema remains 31. Migration directory and checksums unchanged. |
| 21 | Backup/Restore | Three-revision exact-packet/order/pointer/source tests and real 40-revision HTTP archive + server restart. Corrupt older archive authority rejected before live replacement. |
| 22 | Security | Parameterized queries; revision id is constrained to its Research owner; malformed cursor, absent and wrong-owner reads have stable codes. |
| 23 | No Diff | Production Diff route remains absent/rejected; no comparison UI, generated comparison, new Diff table/cache or derived Diff. Existing historical demo is untouched. |
| 24 | Adversarial validation | All 31 owner cases covered; mapping below. 109 Research backend cases pass. |
| 25 | Phase 4 regression | All accepted 84 Research cases retained and passing within focused/full runs. Scope, lexical bounds, source authority, identity, persistence, localization and zero dispatch preserved. |
| 26 | Integrated regression | 505 focused integrated cases pass; four subsequently added hostile cases pass in Research/full suites. Eight real integrated HTTP/SQLite/disposable-vault browser flows pass. |
| 27 | Full backend | 3,224 passed, 1 unchanged optional skip, 2 expected fixture warnings; 466.66 seconds. One complete full run. |
| 28 | Frontend / build | 148 passed: App 91, Research 18, Delta 7, historical demo 32. Typecheck and production build pass. |
| 29 | Browser/E2E | 8 full History + 8 restart/current/history + 8 same-entry reopening + 8 integrated flows; real HTTP backup/restore and 25-row UI pagination. Both languages × 320/768/1024/1440. No console errors, overflow or external requests. |
| 30 | Static / docs | Ruff passes; strict mypy 77 source files; compileall/diff checks pass. designmd: zero errors/warnings. Markdown structure, whitespace, fences and local links pass. |
| 31 | Database | Actual restored schema 31: quick_check/integrity_check `ok`, no FK violations; 2 semantic items / 40 revisions. Query plan uses existing unique sequence index. Packaged migration lineage/checksums verified. |
| 32 | Phase 4 preservation | Clean, unchanged HEAD `22ea84a79bba3f27566a221e774c93c3cc797a4f`; status and all recorded file hashes identical. |
| 33 | Integration preservation | Clean, unchanged HEAD `ba9f27fd2869e24a0b30e58f3ef6e5e29c747a7b`; status and file hashes identical. |
| 34 | M13 preservation | HEAD `e228294f705401b0200439076c3378b78f9c9d84`; original 35 dirty/untracked entries and all recorded file hashes unchanged, including migration 029. |
| 35 | Commits | `1519e15` authority/API/tests; `0e9c0f5` UI/restore acceptance; `e8ab0dc` final selected-revision remediation; subsequent report-only commit. No merge/rebase/push/PR. |
| 36 | Phase 6 readiness | Stable revision ids and exact immutable packets are available for future explicitly derived Diff. No Diff has been implemented. |
| 37 | Genuine blockers | None. Fresh complete baseline-to-code review: no P0/P1 or material Phase 5 P2 remains. |

Decision: [V1X-PHASE5-DR-001](../docs/decisions/V1X-PHASE5-DR-001-research-history.md).
Evidence inventory, reviewed files, checksums and preservation:
[validation manifest](V1X-PHASE5-VALIDATION.json).
Local logs/screenshots: `.var/phase5/validation`,
`.var/phase5/browser-acceptance`, `.var/phase5/integrated-browser-final`.

## Required hostile-case evidence

| Owner cases | External evidence |
| --- | --- |
| 1–4 | First/second/third exact revision reads, immutable packet/one-item assertions; real browser reruns and current/history states. |
| 5–7 | Verification and pointer-update rollback injection; genuinely fabricated new packet rejected; corrupt historical payload excluded without corrupting current. |
| 8–11 | Exact historical `as_dict`, old Evidence id source navigation, later legitimate Intelligence revision, unavailable Evidence rejection and unchanged stored packet. |
| 12–13 | Fixed equal timestamps, sequence/cursor order, new rerun between pages, no duplicate/skip; all-corrupt page still reaches valid older rows. |
| 14–17 | Wrong-owner/absent revision API codes, language/scope identity separation and independent History. |
| 18–20 | Real three-revision archive restore; current/order/source equality; corrupt-only-old archive rejected with live DB hash unchanged. |
| 21–24 | Complete before/after equality of every database table, including Research/Intelligence/Topic/Delta authority. |
| 25–26 | Prohibited socket/web dispatch tests, no provider import/call in production Research/History; browser external requests empty. |
| 27–29 | Bilingual unit/browser states, 32-version backend page bound, 25-row real browser pagination, all viewport overflow checks. |
| 30–31 | Diff API rejected, live UI comparison absent, no diff-named database table and no migration/new authority storage. |

## Review and remediation evidence

Domain review checked storage reuse, append-only behavior, current-pointer rollback,
exact source snapshots, semantic collection uniqueness, owner-bound revision reads,
sequence ordering and absence of Diff. Product/authority review inspected live API,
desktop/mobile screenshots, source-return routes and restored authority. Fresh final
review inspected all 17 changed code/design/test/decision files from the exact base,
including actual validation logic rather than test names. The final report-only
diff was also reviewed.

| Command / failure | File and resolved cause |
| --- | --- |
| `pytest tests/integration/test_research_history.py -q`: 5 initial AttributeError failures | Expected red stage before adding `history`/`read_revision`; implemented then green. |
| `vitest Research.test.tsx`: historical heading missing | Test response fixture treated detail routes as list responses; suffix-specific fixture restored, retaining exact-route assertions. |
| `node research-history.e2e.mjs`: historical heading timeout at line 64 | Missing mounted-page hash synchronization fixed in `Research.tsx`; then existing-history async rerun race diagnosed by live URL/response inspection and fixed with explicit POST/completion waits. |
| Restore harness: `403 !== 201`, then `415 !== 200` | Used accepted `X-YIA-Request: local-ui` and ZIP media-type contract; no security gate weakened. |
| Integrated browser publication timeout | Disposable fixture was passed a relative vault root; reran using an absolute path inside Phase 5. No product/publisher changes. |
| Restore startup: `500 !== 200` | Harness reached Vite before backend restore initialization/listening completed; waited for the actual ready output, then exact restore/browser tests passed. |
| Same-revision regression: `Unable to find an element with the text: Original authority.` | Fresh review found result clearing without a state transition. Test demonstrably fails with old handler; guard, 18-test focused pass, 148-test full frontend pass and eight actual browser cases prove remediation. |

The optional tokenizer test is unchanged and skips because
`YOUTUBE_INTEL_O200K_TEST_ASSET` is absent. Warnings are intentional duplicate ZIP
entries and invalid-enum serialization fixtures. No accepted test was deleted,
skipped, assertion removed or coverage/CI weakened. The old UI assertion banning
History was explicitly updated to require the authorized History while retaining
its no-comparison/ no-Diff assertion. No dependencies, lockfiles, credentials,
production configuration, paid providers, external exploration or real vaults
were changed or used. Validation reuses the already approved environment and an
independent copy of existing frontend dependencies.

V1X_PHASE5_RESEARCH_HISTORY_FULLY_COMPLETE_PHASE6_MAY_START
