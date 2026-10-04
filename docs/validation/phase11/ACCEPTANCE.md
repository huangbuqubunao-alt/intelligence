# Phase 11 final acceptance

Starting authority: `bda7e3eeeaf7f71ab243a82bd75dc4995825d06b`, schema 33.
Worktree: `/Users/hua/Documents/yia-worktrees/v1x-bilibili-following`.
Branch: `chatgpt/v1x-bilibili-following`. Sole engineering executor.
Reviewed production code: `0153cf8ef0d08e8492683deb2d2287767c061b74`.
Subsequent changes only improve browser assertion waits and record acceptance.

## Delivered behavior

Follow a public creator by approved profile URL, numeric mid, or verified uploader
metadata in existing Bilibili Content. Canonical creator identity deduplicates all
forms. Following establishes a bounded starting point, without importing history.
Later checks record canonical BV observations, automatically enroll genuinely new
videos into ordinary Content, and acquire legitimate public timed captions.
Captioned Content uses accepted extractive Summary and durable TIMED_MEDIA
Evidence. Captionless Content remains unavailable for transcript-dependent work.
Intelligence, Topic, Research and Knowledge Delta keep their existing authority.

The existing Source Run worker runs explicit checks and bounded stale checks on
Following open/focus. Pause, durable cooldown, queued-run reuse and shared provider
budgets apply. Tracking is portable SQLite authority, including pending enrollment,
observed identities, check receipts, health and the last verified frontier.
Backup/Restore validates both that state and immutable uploader relationships.
Large or incomplete scans expose UPDATE_GAP; offsets are never completeness proof.

See [decision record](../../decisions/V1X-PHASE11-CREATOR-FOLLOWING.md),
[55-case adversarial matrix](ADVERSARIAL_MATRIX.md),
[self-review and remediation](SELF_REVIEW.md) and
[reviewed code hashes](reviewed-code-manifest.json).

## External verification

Commands ran inside the dedicated worktree using the existing Python environment
`/Users/hua/youtube-intel/.venv`, `PYTHONPATH=src`, and existing frontend tools.
No production dependency or toolchain changes were made. Logs are in `checks/`.

| Verification | Result / evidence |
| --- | --- |
| Accepted baseline focused regression | 111 passed; `baseline-tests-corrected.txt` |
| Phase 11 focused slice | 121 passed; `phase11-focused-corrected.txt` |
| Final creator/publication authority tests | 62 passed; `creator-authority-final.txt` |
| Following lifecycle, API and existing task 024 | 83 passed; `following-lifecycle-final.txt` |
| Portable creator relationship/restore | 67 passed; `relationship-restore-corrected.txt` |
| Rapid queued check commands | One dedicated test passed; ten requests reuse one run and make zero provider calls before worker execution |
| Phase 7/8/9/9R acoustic state | 170 passed; `phases7-8-9-9r-state.txt` |
| YouTube and migration lineage | 237 passed; `lineage-youtube-remediated.txt` |
| Bilibili Phase 10B/provider regression | 116 passed; `providers-remediated.txt` |
| Migration/state/Phase 8 remediation | 255 passed; `migration-phase8-remediated.txt` |
| Integrated V1.x regression | 151 passed; `integrated-v1x.txt` |
| Full backend, final complete run | **3,550 passed, one inherited skip, two fixture warnings, 731.13 seconds**; `backend-acceptance-complete.txt` |
| Frontend all tests | **181 passed, nine files**; `frontend-acceptance-tests.txt` |
| `npm run typecheck` | Passed; `frontend-typecheck-final.txt` |
| `npm run build` | Passed; `frontend-acceptance-build.txt` |
| `ruff check src tests` | Passed; `ruff-final-acceptance.txt` |
| `mypy --strict src` | Passed, 94 files; `mypy-final-acceptance.txt` |
| `python -m compileall -q src tests` | Passed; `compileall-final-acceptance.txt` |
| `designmd lint DESIGN.md` and workspace DESIGN.md | Zero findings; both final design logs |
| `git diff --check` and local Markdown links | Passed in final acceptance |
| SQLite checks | Five fixture databases: schema 34, quick/integrity `ok`, zero foreign-key violations, exact migration lineage/checksums, valid tracking; [database.json](database.json) |
| Protected worktrees | All 21 retain before/after HEAD, status and diff, including pre-existing M13 changes; [protected-preservation.json](protected-preservation.json) |

The full backend command was `PYTHONPATH=src .../python -m pytest -q`.
The inherited skip is
`tests/unit/test_o200k_provisioning.py::test_external_provisioned_canonical_asset_preserves_golden_token_ids`:
it requires an explicitly provisioned canonical tokenizer asset. This phase did
not change or skip that test. The two warnings arise from intentional corrupt ZIP
and invalid enum fixtures. The initial full-suite failure is retained in
`checks/full-backend.txt`; all failures were fixed and the complete suite reran.

## Real browser and public provider evidence

Actual installed Chrome, production build for creator/Phase 10B/Phase 7/Phase 8,
and existing integrated development browser flow; real loopback HTTP, SQLite,
ordinary Source Run worker and isolated fixtures. Provider mutations are test-only.

| Browser matrix | Passed scenarios |
| --- | --- |
| Creator Following online | Nine: eight language/width combinations plus numeric id and automatic stale discovery |
| Creator Following after process restart, offline | Eight, same database; health text, last successful/verified state and two discoveries preserved |
| Phase 10B manual Bilibili | Eight |
| Phase 7 Local | Eight |
| Phase 8 transcription state | Eight, fixture executor only |
| Integrated V1.x / Evidence / Obsidian / NONE state | Eight |

Both zh-CN/en and 320/768/1024/1440 widths passed; zero horizontal overflow,
unexpected console errors or external browser requests. Primary navigation remains
six items. Stored captions/Evidence and mixed YouTube + Local + manual Bilibili +
creator-discovered Bilibili Research work offline. No fixture acoustic or historical
Deep Analysis result confers production qualification. Creator fixture transport
asserts zero model calls. [Online](creator-browser.json),
[offline](creator-offline-browser.json), [screenshots](screenshots.json).

[Real public validation](live-public-creator.json): public 央视新闻, mid
456664753, resolved and established a 30-identity bounded baseline with zero
Content imports. Repeat retrieval returned RATE_LIMITED and preserved the last
verified state. The bounded repeat used a local validation clock advanced by
16 minutes; the production provider pacing, concurrency, HTTP retries and risk
cooldown remained enforced. No bypass, cookies or provider manipulation occurred.
No successful live repeat or real newly uploaded video is claimed; deterministic
fixtures prove actual incremental discovery and recovery.

## Final review and limits

Fresh acceptance inspected the complete baseline-to-final implementation:
Following identity/ledger/receipts, partial enumeration and acquisition failures,
restart/restore, dedupe, public networking, Content admission/publication/uploader
checks, immutable captions, frontend grouping/filters, source-health Delta and
ordinary Research/Intelligence provenance. All prior 32 migration files remain
byte-identical; 029 remains intentionally absent. Schema 034 is justified by
durable generalized tracking authority, not provider-specific subscriptions.

No remaining P0/P1 or material Phase 11 P2 finding. No genuine blocker.
Public availability remains provider-controlled; restricted/offline checks are
truthful failures with preserved state. Very large lists remain conservatively
incomplete within the finite discovery policy. Update counts are cumulative,
without an invented read/unread inbox.

Deferred: always-on helper, notifications, historical import, full multipart,
explicit versioned caption refresh, acoustic qualification and production Deep
Analysis. Recommended next phase: explicit versioned caption refresh that retains
existing Summary/Evidence authority while retrying unavailable public captions.
Production acoustic ASR remains NONE; large-v3-turbo remains NOT QUALIFIED / FAILED;
production Deep Analysis remains NONE. No merge, push, PR or accepted history
rewrite. Completion is local to this branch.
