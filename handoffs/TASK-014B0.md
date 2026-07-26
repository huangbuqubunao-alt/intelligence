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

## Independent Reviewer evidence — 2026-07-26

- Reviewer agent/session: `Codex Reviewer`
- Fixed implementation base/source HEAD/parent: `c62310ab79f01f5f311c9f54bb28365905f5a81a` / `4e506847854f20a43011b0a15db3a1c8e320656d` / `c62310ab79f01f5f311c9f54bb28365905f5a81a`.
- Source branch/worktree: `codex/task-014-phase-b0-restricted-public-subtitle-smoke` / `/Users/hua/Documents/yia-worktrees/task-014-phase-b0-restricted-public-subtitle-smoke`.
- Pre-append Git evidence: source HEAD and sole parent matched the fixed values; `git status --short` was clean; `git diff --name-status base...source` contained exactly `docs/operations.md`, `handoffs/TASK-014B0.md`, `src/youtube_intel/cli.py`, `src/youtube_intel/public_subtitle_smoke.py`, `tests/integration/test_operations.py`, and `tests/integration/test_public_subtitle_smoke.py`; `git diff --check base...source` passed.
- Static boundary evidence: `PublicSubtitleSmoke` validates a non-existing absolute root and 1--3 distinct existing-rule video IDs before initialization; initializes only `state.sqlite`, `data/`, `test-vault/`, and `logs/`; uses 30 seconds for both locked adapters; processes IDs sequentially with one `fetch`, one `enumerate_tracks`, one first-ranked `read_track`, no retry loop, and deletes the in-memory read result. It only initializes SQLite and never calls Pipeline/Job/ProviderCall/Artifact writes. JSONL inputs are fixed metadata/counters/error code/duration and use `JsonlLogger`; no result body, track URL, exception message, root path, credential, or user content enters the logger.
- Static adapter/reuse evidence: no dependency, lockfile, schema/migration, state, domain/config, Provider Adapter, B-1 evidence, or task-status path is in the fixed range. The existing locked yt-dlp adapters retain `ignoreconfig`, `skip_download`, no media/subtitle/thumbnail writes, `usenetrc=False`, and no configured Cookie/login/remote-component/ffmpeg path. The new graph contains no model, OpenAI, Ollama, Whisper, paid-provider, launchd, media-download, or real-Vault service call.
- Static Fake-test evidence: the added Fake tests cover root/ID bounds, 30-second factories, exact per-stage call ledgers, no retry after failure, root file set, zero `videos`/`jobs`/`provider_calls`/`artifacts` rows, redaction of body/temporary URL/path/error text, and the existing default `check` fail-closed assertion. This reviewer did not execute tests or product code.

### Findings

- **P1 — restricted CLI still accepts configuration-path inputs.** `src/youtube_intel/cli.py:97-104` registers `--project-root`, `--settings`, and `--channels` on the top-level parser, so `smoke-public-subtitles` accepts those options before the subcommand. Although `main` returns at lines 146-151 before loading them, ADR-013 S-01 and the task acceptance criterion require this entry to accept only the new temporary root and 1--3 explicit IDs, with no YAML/configuration input. No added test rejects these options. Minimum fix: make the smoke parse surface reject all three global configuration options (without changing the existing commands), and add an offline assertion that each is rejected before any runner/adapter call.
- **P2 — Implementer handoff metadata is stale and conflicts with Git facts.** `handoffs/TASK-014B0.md:8,11,13,66` still names `main@28223cc...` and `pending implementation commit`/pending reporting, while the mandated fixed implementation parent is `c62310ab...` and the reviewed commit is `4e506847...`. Update the Implementer metadata and commit/verification record in the correction; do not treat the current self-reported verification table as final evidence.
- No P0 or P3 findings.

### Reviewer conclusion

- Re-run checks: none by authorization. Deliberately not run: tests, build, installation/uv, Python/import, CLI, network/B-1 smoke, credentials/Cookie/API-key access, media/ffmpeg/model/OpenAI/Ollama/launchd access, real Vault/user data, SQLite/log/cache reads.
- Verdict: `REJECT`.
- Unresolved P0/P1: P1 above. This is a B0 offline static review only; it is not B-1 smoke evidence, release approval, a legal conclusion, an exactly-once proof, or TASK-014 Go.
