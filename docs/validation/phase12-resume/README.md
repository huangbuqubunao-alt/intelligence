# Phase 12 resumed acceptance evidence

This evidence belongs to `codex/phase12-resume`. The original paused worktree
is a read-only preservation source. Original evidence under `../phase12/` remains
unchanged. The reviewed application implementation is
`e48da8ca0cf8b7d06e60f15cfa0929b5cb73950d`; the final evidence commit changes
only documentation and captured validation artifacts.

## Preservation and integration

`initial-fingerprint.json` records the original branch, HEAD, tracked/cached
patch hashes, index hash, all 35 untracked file hashes, recent commits and reflog.
`reconstruction-proof.json` proves reconstruction before checkpoint `97d2a73`.
The tracked patch is also byte-equivalent in that checkpoint; all 35 untracked
files have matching Git blob hashes. `final-fingerprint.json` and
`frozen-unchanged.json` are the final independent preservation gate.

The shared ancestor is `a81b8e90a662eab72dda28fdc2140362649d9544`.
Merge `23a4f85` preserves checkpoint and validated Phase 11R.1
`8ebdf282af49d9d8d2e7c336f650a74febc83214` as ancestors.
Conflicts were App.tsx, CreatorFollowing.tsx, following_tracking.py and
local_api.py. Resolution retained unified YouTube dispatch, durable tracking,
fair bounded admission and truthful enrollment while retaining Bilibili
withdrawal, capability guards, active/settled run semantics and localized status.
No whole-file ours/theirs selection was used.

## Completed implementation and fresh review

Existing work already implemented the provider seam, stable YouTube identities,
bounded discovery/verified overlap, zero-history baseline, Content enrollment,
durable pending/frontier, fair admission, shared UI and restore validation.
Resume work closed capability separation, queued/direct Bilibili withdrawal,
Check Now terminal feedback, cooldown expiry, withdrawn historical-health copy,
and restored-paused acceptance gaps. No new migration was needed.

`fresh-final-review.json` records code hashes and preservation, integration,
product and scope review passes. Remaining P0/P1 are empty. Production Bilibili
creator and captions capabilities remain false. Historical fixture tests explicitly
inject their provider capability; this does not enable production access.

## Deterministic gates

- Focused acceptance: 203 passed (`focused-final.txt`).
- Named earlier-provider / integrated V1.x regression: 744 passed across the
  39 files in `named-regression-files.json` (`named-regressions.txt`).
- Full backend: 3,650 passed, one inherited provisioning skip, two deliberate
  fixture warnings (`full-backend.txt`, `inherited-skip.txt`).
- Full frontend: 204 passed in 11 files (`frontend-final.txt`). A React act
  warning remains in a unit fixture; production browser console errors are zero.
- `tsc -b` and production build passed (`frontend-typecheck.txt`,
  `frontend-build.txt`).
- Ruff, strict mypy (96 source files), compileall, both DESIGN.md lints and
  scoped `git diff --check` passed. No repo-wide formatting occurred.

Backend commands use the existing `/Users/hua/youtube-intel/.venv/bin/python`
with `PYTHONPATH=src`, e.g. `-m pytest -q`, `-m mypy --strict src`,
`-m compileall -q src tests scripts`; Ruff checks source/tests and the two new
validation scripts. Frontend uses existing dependency bytes, `npm test -- --run`,
`npm run typecheck` and `npm run build`. No dependencies or lockfiles changed.

First failing runs are retained alongside green reruns. The fixture capability
mismatch was fixed by explicit fixture injection. The shared-browser pause race
was fixed by waiting for the actual check-stale response and terminal check state.
No assertion was removed or weakened, and no test/CI script was changed to hide
failure. Fresh text logs normalize trailing whitespace and blank EOF lines only; raw captures and
SHA-256 mapping are retained outside the repository in
`/Users/hua/Documents/phase12-preservation/raw-resume-logs/`.
Original paused raw logs retain every byte, including existing whitespace.

## Browser, restart and Backup/Restore — FIXTURE/REPLAY

The production frontend and actual local API/SQLite/worker ran with deterministic
public-provider seams. Both languages and all four widths were exercised:
8 initial flows, 8 restarted offline flows, 8 restored offline flows,
2 shared Following flows, 8 cooldown states, 8 untrusted/withdrawn/Backup status
projections and a restored-paused then resumed Chinese 320px flow.
JSON artifacts record no console errors or horizontal overflow.
The cooldown UI clock matches the disposable provider fixture clock.

`rapid-check.json`: 12 simultaneous YouTube commands create one source run;
12 withdrawn Bilibili commands create none. Failed offline checks retain frontier,
last success and Content. Settled failure permits Backup.

`database-restore.json` and `database-paused-restore.json`: all 70 authority-table
digests match exactly before/after offline restore, including source identity,
frontier, health, checks/runs, enrolled Content and paused state. All 33 historical
migration files match both starting histories; schema stays 34. quick_check and
integrity_check return ok; foreign_key_check is empty. No duplicate identities,
orphan links/checks/runs, false baseline success or stuck active runs were found.
Deterministic tests separately prove genuinely active work blocks Backup and
settled NEEDS_ATTENTION does not. Physical power loss was not simulated.

## Bounded public YouTube attempts — REAL

`real-public-youtube.json` records exactly two public handle attempts,
@NASA and @GoogleDevelopers. Both returned HTTP 503 / YOUTUBE_NETWORK_UNAVAILABLE.
No source identity, successful baseline or historical Content was fabricated.
The isolated database passed integrity checks and Backup. There was no login,
cookie import, browser profile, auth circumvention, model download or fallback.
A successful real public baseline and subsequent live upload are therefore
unproven in this network environment. New-video discovery is proven separately
by deterministic replay, not represented as a live upload.

## Preserved Phase 11R.1 and boundaries

Focused/full regressions cover both false Bilibili capabilities, available manual
video import, metadata-only no-caption behavior, no ASR fallback, HTTP 412 and
-352/-412/-509 risk control, public DNS answer-set validation/SSRF rejection,
settled versus genuinely active Backup barriers, both untrusted source localizations,
320px wrapping and generic -40003 fallback. Baseline provider, Backup/run-state,
status CSS and historical migration bytes are retained.
No production acoustic ASR or Deep Analysis; large-v3-turbo remains unqualified.
No new provider, daemon, cron, launch agent, notification or infinite polling loop.
Phase 13 and Phase 14 remain future work.

Deferred unrelated P2/P3 remain: Local 1970 fallback, generic Loading localization,
unknown Bilibili fallback copy, operator NEEDS_ATTENTION UI, multipart, caption
refresh and the 235-file formatting backlog. Completion here does not change
existing release governance or authorize push/merge/deployment.
