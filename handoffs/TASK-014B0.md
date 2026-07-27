# TASK-014B0 handoff

## Metadata

- Task: `TASK-014B0 — Restricted public subtitle smoke entry`
- Role: `Implementer`
- Agent/session: `Codex`
- Base branch/commit: `main@c62310ab79f01f5f311c9f54bb28365905f5a81a`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-014-phase-b0-restricted-public-subtitle-smoke`
- Branch: `codex/task-014-phase-b0-restricted-public-subtitle-smoke`
- Initial implementation commit: `4e506847854f20a43011b0a15db3a1c8e320656d`
- Started: `2026-07-26T14:46:38Z`
- Reported: `2026-07-27` (Correction 1 evidence below)

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

- Suggested status: `REJECTED — Correction 1 implemented; pending independent re-review`
- Commit SHA: `4e506847854f20a43011b0a15db3a1c8e320656d` (initial implementation)
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

## Correction 1 implementation evidence — 2026-07-27

- Correction base/review evidence: `f8e336a8c3b09a8c0c0e5857148495f2cb2281aa` (sole parent required for the correction commit; first review `REJECT`, P1/P2).
- Correction commit: `HEAD` — the commit containing this handoff; it is verified before handoff as descending directly from the required review evidence.
- Correction status: implemented and awaiting an independently started re-review; this is not B-1 smoke evidence, release approval, or a TASK-014/TASK-014B0 status change.
- Scope: only `src/youtube_intel/cli.py`, `tests/integration/test_public_subtitle_smoke.py`, and this handoff changed for Correction 1.
- Reuse decision: `DIRECT` — the existing argparse surface, locked smoke runner, Python standard library, and offline Fake tests; no new dependency or copied third-party code.
- Fix: when `smoke-public-subtitles` appears in argv, any `--project-root`, `--settings`, or `--channels` token, including `--name=value` and either command position, returns the existing usage/configuration exit before parser dispatch, smoke runner construction, Adapter construction, or temporary-root initialization. Other command parsing remains unchanged.

| Offline verification | Result |
|---|---|
| RED: `uv run python -m pytest tests/integration/test_public_subtitle_smoke.py -q` after adding the regression | FAIL as expected — global `--project-root` before the subcommand returned `ExitCode.OK` and initialized the smoke path. |
| GREEN: `uv run python -m pytest tests/integration/test_public_subtitle_smoke.py -q` | PASS — 4 passed. The added Fake matrix covers all three disabled options, before/after positions, separate-value and `=` forms, zero Fake Adapter calls, and no temporary-root creation. |
| `uv run python -m pytest tests/integration/test_operations.py tests/integration/test_public_subtitle_smoke.py` | PASS — 12 passed |
| `uv run python -m pytest tests/integration/test_subtitle_provider.py -k 'ytdlp_adapter_enumerates_tracks_with_safe_no_download_options'` | PASS — 1 passed, 76 deselected |
| `uv run mypy src` | PASS — 24 source files |
| `uv run ruff check .` | PASS |
| `uv run python -m youtube_intel --help` | PASS — restricted command remains listed; no command execution or network access |
| `git diff --check` | PASS |

- No network, B-1 smoke, credentials/Cookie/environment-value access, real Vault/user data, media/ffmpeg/model/OpenAI/Ollama/launchd operation, dependency, lockfile, Schema, migration, or default CLI semantic change was performed.

## Correction 1 independent reviewer evidence — 2026-07-27

- Reviewer: `Codex Reviewer` (independent review only).
- Fixed correction base/source HEAD/sole parent: `f8e336a8c3b09a8c0c0e5857148495f2cb2281aa` / `cafcde82eaa032bfae3bcee8049ef60ebda6d650` / `f8e336a8c3b09a8c0c0e5857148495f2cb2281aa`. Correction 1 SHA is `cafcde82eaa032bfae3bcee8049ef60ebda6d650`; it is the sole child of the required review evidence.
- Pre-append Git evidence: source `HEAD` and sole parent matched the fixed values; `git status --short` was clean; `git diff --name-status base...HEAD` contained exactly `src/youtube_intel/cli.py`, `tests/integration/test_public_subtitle_smoke.py`, and `handoffs/TASK-014B0.md`; `git diff --check base...HEAD` passed. The full correction diff is 70 insertions/6 deletions in those three paths only.
- Dependency/Schema/control-plane evidence: no diff exists for `pyproject.toml`, `uv.lock`, migrations, `state.py`, domain/config, Provider Adapters, task/status files, or B-1 evidence. Reuse remains `DIRECT`: existing argparse surface, locked smoke runner, Python standard library, and Fake tests; no dependency or third-party code was added.
- Static restricted-path evidence: for an actual smoke invocation, each of `--project-root`, `--settings`, and `--channels`, in separated or `--flag=value` form and before or after the smoke command, is recognized by `_smoke_uses_global_configuration` before parser dispatch, `PublicSubtitleSmoke` construction/run, Adapter factories/calls, and temporary-root initialization. The Fake matrix covers all 12 combinations and confirms usage exit `2`, zero Fake metadata/enumerate Adapter calls, and no target root. The existing smoke implementation still enforces 1--3 unique IDs, one sequential metadata/directory/read sequence per ID, 30-second factory timeout, no retry loop, in-memory body discard, JSONL redaction, and zero Pipeline/Job/ProviderCall/Artifact records. Its call graph is only `cli.main -> PublicSubtitleSmoke`; the reviewed paths contain no media download, ffmpeg, Whisper, Ollama, OpenAI, paid-provider, launchd, real-Vault, or configuration-loading call from the smoke branch.
- Independent offline Fake verification: `uv run --offline python -m pytest tests/integration/test_public_subtitle_smoke.py -q` — PASS, 4 passed in 0.39s. This test file injects only Fake metadata/subtitle implementations and temporary paths; no real network or B-1 smoke was invoked.

### Findings

- **P1 — global-input rejection is not limited to the actual smoke subcommand.** `src/youtube_intel/cli.py:211-217` treats any occurrence of the literal `smoke-public-subtitles` anywhere in `argv` as proof that the smoke command is active. Thus a valid normal-command value such as `--settings config/settings.yaml process --video smoke-public-subtitles` is rejected before normal parsing/configuration/dispatch solely because it contains that string and one global configuration option. This changes the frozen `process` surface (and the same issue applies to `check`, `retry`, `weekly`, or `doctor` values), violating ADR-013 S-03 and the correction requirement that only `smoke-public-subtitles` change while existing commands retain their semantics. The added test only exercises actual smoke invocations, so it cannot catch this regression. Minimum fix: identify the parsed/lexically valid subcommand without constructing the smoke runner or reading configuration, then apply the configuration-token rejection only when that subcommand is actually `smoke-public-subtitles`; add offline regressions proving normal commands with `smoke-public-subtitles` as an option value retain their prior behavior.
- P0: none. P2: none. P3: none.

### Reviewer conclusion

- Deliberately not run: network/YouTube, B-1 or any real smoke, credentials/Cookie/API-key or environment-value access, real Vault/user data, media/ffmpeg, Whisper/model/Ollama/OpenAI/paid services/launchd, build/install/package, or any test outside `tests/integration/test_public_subtitle_smoke.py`.
- Verdict: `REJECT` because of unresolved P1. This is offline Correction 1 review evidence only; it is not B-1 smoke evidence, release approval, a legal conclusion, an exactly-once proof, risk acceptance, or TASK-014 Go.

## Correction 2 implementation evidence — 2026-07-27

- Correction base/review evidence: `48df2e2a0afb54d5f6252f197dddf32ff685f0db` (sole parent required for the Correction 2 commit; Correction 1 review `REJECT`, P1 only).
- Correction 2 commit: `HEAD` — the commit containing this handoff; it descends directly from the required review evidence.
- Correction status: implemented and awaiting an independently started re-review; this is not B-1 smoke evidence, release approval, or a TASK-014/TASK-014B0 status change.
- Scope: only `src/youtube_intel/cli.py`, `tests/integration/test_public_subtitle_smoke.py`, and this handoff changed for Correction 2.
- Reuse decision: `DIRECT` — the existing argparse surface, locked smoke runner, Python standard library, and offline Fakes; no dependency or third-party code was added.
- Fix: argparse now first establishes `args.command`; only an actual `smoke-public-subtitles` command applies the existing global configuration-token rejection before smoke runner construction, Adapter construction, or temporary-root initialization. `check`, `process`, `retry`, `weekly`, and `doctor` retain their original parsing/configuration/fail-closed paths even when a legal option value is `smoke-public-subtitles`.

| Offline verification | Result |
|---|---|
| RED: `uv run python -m pytest tests/integration/test_public_subtitle_smoke.py -q` after adding the regression | FAIL as expected — `check --channel smoke-public-subtitles` returned usage exit `2` before normal configuration and Fake Operations dispatch. |
| GREEN: `uv run python -m pytest tests/integration/test_public_subtitle_smoke.py -q` | PASS — 5 passed. New Fake regression creates only a temporary local configuration and proves `check --channel smoke-public-subtitles` returns `0` and dispatches once; the existing 12-case smoke matrix still rejects all disabled global inputs before Adapter calls or root creation. |
| `uv run ruff check src/youtube_intel/cli.py tests/integration/test_public_subtitle_smoke.py` | PASS |
| `uv run mypy src` | PASS — 24 source files |

- No network, B-1 smoke, credentials/Cookie/environment-value access, real Vault/user data, media/ffmpeg/model/OpenAI/Ollama/launchd operation, dependency, lockfile, Schema, migration, or default CLI semantic change was performed.

## Correction 2 independent reviewer evidence — 2026-07-27

- Reviewer: `Codex Reviewer` (independent review only).
- Fixed correction base/source HEAD/sole parent: `48df2e2a0afb54d5f6252f197dddf32ff685f0db` / `b7cb846e650eb02b64321ef566991123d319f310` / `48df2e2a0afb54d5f6252f197dddf32ff685f0db`. Before this append, `git status --short` was clean; `git diff --name-status base...HEAD` contained exactly `src/youtube_intel/cli.py`, `tests/integration/test_public_subtitle_smoke.py`, and this handoff; `git diff --check base...HEAD` passed.
- Scope/reuse evidence: the range contains no `pyproject.toml`, `uv.lock`, migration, Schema, `state.py`, domain/config, Provider Adapter, task/status, ADR, B-1 evidence, or control-plane change. Reuse remains `DIRECT`: existing argparse surface, locked smoke runner, Python standard library, and offline Fakes; no dependency or copied third-party code.
- Static parser evidence: `main` first performs the existing argparse parse, then calls `_uses_global_configuration` only when parsed `args.command == "smoke-public-subtitles"`, before runner construction, Adapter factories/calls, or temporary-root initialization. `_uses_global_configuration` matches only the three exact option tokens or `--flag=value`; it does not infer a command from an argv value. Thus the 12 smoke combinations (three flags, before/after command, separate/equals values) fail closed, while `check`, `process`, `retry`, `weekly`, and `doctor` stay on their existing parse/configuration/default-fail-closed paths even if a legal argument value equals `smoke-public-subtitles`. The offline Fake regression proves one normal `check --channel smoke-public-subtitles` dispatch; static review of `_build_parser`, `_validate_arguments`, and `_dispatch` confirms the other command surfaces do not enter the smoke interceptor.
- Restricted-runner boundary evidence: the existing `PublicSubtitleSmoke` still validates a nonexistent absolute temporary root and 1--3 unique explicit IDs before initialization; initializes only SQLite, DATA, empty test Vault, and JSONL logs; uses fixed 30-second factories; invokes metadata, directory enumeration, and the selected body read at most once per ID sequentially with no retry; and deletes the in-memory body. It makes no Pipeline/Job/ProviderCall/Artifact records. The audited JSONL fields exclude body, temporary URL, absolute root, credentials, user data, and exception text. No reviewed route calls YAML/config loading from the smoke branch, media download, ffmpeg, Whisper, Ollama, OpenAI, paid services, launchd, or a real Vault.
- Independent offline Fake verification: `uv run --offline python -m pytest tests/integration/test_public_subtitle_smoke.py -q` — PASS, `5 passed in 0.41s`. The test injects only Fake metadata/subtitle adapters and uses pytest temporary paths; no real network, B-1 smoke, credentials/Cookie/API key/environment-value access, real Vault/user data, media/ffmpeg, Whisper/model/Ollama/OpenAI/paid-service/launchd operation, build, install, package, or other product command was run.

### Findings

- No P0–P3 findings.

### Reviewer conclusion

- Verdict: `APPROVE` for the Correction 2 offline review.
- This approval is limited to the stated offline correction. It is not real B-1 smoke evidence, release approval, a legal conclusion, a strict exactly-once proof, risk acceptance, or a TASK-014 Go/No-Go or task-status change.
