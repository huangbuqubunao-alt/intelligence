# TASK-014B0 handoff

## Metadata

- Task: `TASK-014B0 — Restricted public subtitle smoke entry`
- Role: `Implementer`
- Agent/session: `Codex`
- Base branch/commit: `main@28223cc98f9da18fc877289231a92e240cc711d0`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-014-phase-b0-restricted-public-subtitle-smoke`
- Branch: `codex/task-014-phase-b0-restricted-public-subtitle-smoke`
- Head commit: pending implementation commit
- Started: `2026-07-26T14:46:38Z`
- Reported: pending final checks and commit

## Goal and scope

- Task goal: provide the ADR-013 QA-only `smoke-public-subtitles` command without changing the default CLI composition or any production state semantics.
- Allowed and actual changes: `src/youtube_intel/cli.py`, `src/youtube_intel/public_subtitle_smoke.py`, `tests/integration/test_operations.py`, `tests/integration/test_public_subtitle_smoke.py`, `docs/operations.md`, and this handoff.
- Explicitly not changed: Provider adapters, `state.py`, domain/config, Schema/migrations, dependencies/lockfile, task/status control-plane files, B-1 evidence, real Vaults, credentials, or release status.

## Reuse decision

- `DIRECT`: existing locked `YtDlpMetadataProvider`, `YtDlpSubtitleAdapter`, SQLite migration through `SQLiteStateRepository`, `JsonlLogger`, and Python standard library only.
- No third-party code was copied, no dependency or lockfile changed, and no public Adapter protocol was introduced.
- Existing Adapter safe-option regression remains covered offline; the new composition passes its fixed 30-second timeout to both existing adapters.

## Acceptance evidence

| Acceptance item | Result | Evidence |
|---|---|---|
| 1–3 distinct explicit IDs and new absolute temporary root only | PASS | Offline Fake tests reject existing roots, invalid/duplicate IDs, and four IDs before any Adapter call. |
| One sequential metadata/enumerate/read call, fixed 30-second timeout, no retry | PASS | Fake call ledgers assert one call per stage/ID, manual candidate ranking, and failure does not retry; factory probes record `30.0` for both adapters. |
| Isolated initialized SQLite/DATA/test-Vault/log root with no business records | PASS | Temporary-root test verifies only the four fixed entries and zero `videos`, `jobs`, `provider_calls`, and `artifacts` rows. |
| Subtitle body, temporary URL, paths, and exception details do not persist | PASS | Tests scan every temporary-root file for the body and assert JSONL excludes body, URL, absolute root, and failure-path text. |
| Existing commands remain fail-closed | PASS | Existing CLI command test asserts default `check` exits `2` without injected Operations; no default command dispatch changed. |
| Existing Adapter safety options | PASS | Offline `test_ytdlp_adapter_enumerates_tracks_with_safe_no_download_options` verifies the locked subtitle Adapter options without network access. |

## Checks

| Command | Result |
|---|---|
| `uv run python -m pytest tests/integration/test_operations.py tests/integration/test_public_subtitle_smoke.py` | PASS — 11 passed |
| `uv run python -m pytest tests/integration/test_subtitle_provider.py -k 'ytdlp_adapter_enumerates_tracks_with_safe_no_download_options'` | PASS — 1 passed, 76 deselected |
| `uv run python -m pytest` | PASS — 449 passed |
| `uv run mypy src` | PASS — 24 source files |
| `uv run ruff check .` | PASS |
| `uv run python -m youtube_intel --help` | PASS — new command listed |
| `git diff --check` | PASS |

## Diff and boundary review

- Only the six task-authorized paths are modified or added.
- No generated files, formatting churn, dependencies, Schema/migrations, credentials, real Vault contents, external requests, media downloads, ffmpeg, models, OpenAI, or B-1 execution evidence are present.
- All verification used offline Fakes or existing offline fixtures. No real YouTube request, authentication material, environment value, Cookie, API key, real Vault, or user data was read.

## Failures, skips, and risks

- RED evidence: before implementation, the focused pytest command failed during collection with `ModuleNotFoundError: No module named 'youtube_intel.public_subtitle_smoke'`.
- Real B-1 smoke is intentionally not run and remains separately authorized only after B-0 review/integration.
- The entry makes a bounded best-effort external read only when a separately authorized future B-1 invokes it; its current B-0 proof is Fake-only and does not prove real YouTube compatibility or release readiness.
- `DECISION NEEDED`: `None`.

## Implementer conclusion

- Suggested status: `IN_REVIEW`
- Commit SHA: pending implementation commit
- Reviewer: not started, per task authorization.
