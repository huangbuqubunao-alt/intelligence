# TASK-014 Phase B-1 handoff

## Metadata

- Task: `TASK-014 Phase B-1 — Public YouTube subtitle smoke`
- Role: `Smoke Executor`
- Agent/session: `Codex`
- Control-plane baseline: `main@c4c3c2be9f6893ed1e4d620b1ca4583744ec6566`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-014-release-readiness-phase-b1`
- Branch: `codex/task-014-release-readiness-phase-b1`
- Start head: `28223cc98f9da18fc877289231a92e240cc711d0`

## Goal and authorized scope

The authorization allowed one low-frequency public YouTube smoke for 2–3 stable official videos, limited to metadata, subtitle discovery, and one selected subtitle-body read per selected target. The only writable paths were this handoff, `docs/SMOKE_EVIDENCE/TASK-014-PHASE-B1-PUBLIC-YOUTUBE.md`, and a Phase B-1 record in `docs/RELEASE_CHECKLIST.md`.

Reuse decision: `DIRECT` — use only the locked project yt-dlp Adapter and project CLI; no dependency, lockfile, Schema, test, config, or product-code changes.

## Result and evidence

- Outcome: `BLOCKED`; no public target was selected or contacted.
- Detailed evidence: `docs/SMOKE_EVIDENCE/TASK-014-PHASE-B1-PUBLIC-YOUTUBE.md`.
- Static entry-point evidence: `cli.main()` defaults all non-doctor commands to `_UnavailableOperations`; the concrete `Operations` composition is intentionally external. The CLI has no metadata/subtitle-only command or temporary-root flags. Direct Adapter calls were not used because they bypass the required project entry and isolated application-run boundary.

## Checks performed

| Command / inspection | Result | Evidence |
|---|---|---|
| `git rev-parse HEAD` and `git rev-parse main` | PASS | both were `28223cc98f9da18fc877289231a92e240cc711d0` before evidence edits |
| `git merge-base --is-ancestor c4c3c2be... HEAD` | PASS | authorization baseline is an ancestor of the start head |
| CodeGraph review of CLI parser, dispatch, `Operations`, and `_UnavailableOperations` | PASS | confirms fail-closed absence of an authorized constrained composition |
| Real YouTube / product command | NOT RUN | stopped before target selection because the execution gate failed |
| Tests, build, install, dependency resolution, lint, typecheck | NOT RUN | explicitly prohibited by the Phase B-1 package |

## Boundary and red-line verification

- No YouTube request, retry, media download, subtitle download beyond a selected body, ffmpeg, Whisper, model, Ollama, OpenAI, paid call, launchd, Cookie, login, API key, `.env`, Keychain, credential, real Vault, user data, existing DATA, or existing logs access occurred.
- No temporary SQLite/DATA/test-Vault was created because no application run began.
- No product code, tests, config, dependency, lockfile, Schema/migration, task status, control-plane document, LICENSE, or distribution conclusion changed.
- Actual modifications are confined to the three Phase B-1 evidence paths.

## Remaining risks and decision needed

- `DECISION NEEDED`: provide an explicitly approved existing production composition, or authorize a new dedicated constrained entry point, before another real B-1 smoke attempt. It must accept temporary SQLite/DATA/test-Vault roots and limit its work to one supplied video’s metadata, subtitle directory, and at most one selected subtitle-body read.
- TASK-014 remains `IN_PROGRESS` / `No-Go`; mutagen GPL distribution treatment, BPE file attribution/NOTICE, real Vault boundary, at-most-once risk sign-off, and final PO/TL/QA decision remain open.

## Executor conclusion

- Suggested status: `BLOCKED`
- Commit SHA: pending evidence commit
- Reviewer: not started, per authorization package
