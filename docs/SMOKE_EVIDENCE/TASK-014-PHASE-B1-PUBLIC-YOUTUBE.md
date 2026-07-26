# TASK-014 Phase B-1 — Public YouTube subtitle smoke evidence

- Executor: Codex
- Worktree / branch: `/Users/hua/Documents/yia-worktrees/task-014-release-readiness-phase-b1` / `codex/task-014-release-readiness-phase-b1`
- Control-plane baseline: `main@c4c3c2be9f6893ed1e4d620b1ca4583744ec6566`
- Authorization commit present at start: `28223cc98f9da18fc877289231a92e240cc711d0`
- Evidence time (UTC): `2026-07-26T13:15:03Z`
- Reuse decision: `DIRECT` — existing locked yt-dlp Adapter and project CLI only; no new dependency or copied third-party code.

## Result

**BLOCKED — no public YouTube request was made.** This is not a release approval, a successful smoke, a legal conclusion, an exactly-once claim, or a risk acceptance.

The required existing project entry cannot constrain a real execution to the authorized sequence: one video metadata read, one subtitle-directory read, and one selected subtitle-body read. Per the Phase B-1 authorization package, execution stopped before selecting or calling any target rather than bypassing the product entry with an ad-hoc script or direct Adapter invocation.

## Target selection and execution ledger

| Slot | Exact public target | Official-channel / stability rationale | Result |
|---|---|---|---|
| 1 | Not selected | No target lookup was performed after the entry-point gate failed. | Not executed |
| 2 | Not selected | No target lookup was performed after the entry-point gate failed. | Not executed |
| 3 | Not selected | No target lookup was performed after the entry-point gate failed. | Not executed |

No YouTube URL, channel page, metadata, subtitle directory, subtitle body, media, audio, or video was requested or downloaded. No retry, authentication flow, Cookie, browser profile, API key, `.env`, environment credential, Keychain, paid API, OpenAI, Ollama, model, ffmpeg, launchd, real Vault, user note, existing DATA, or existing log path was accessed.

## Reproducible entry-point gate

Static review of the authorized project code found:

- `src/youtube_intel/cli.py:94` defines only `check`, `process`, `retry`, `weekly`, and `doctor`; it exposes no single-video metadata/subtitle-only command.
- `src/youtube_intel/cli.py:124` dispatches non-`doctor` commands with `operations or _UnavailableOperations()`.
- `src/youtube_intel/cli.py:53` defines `Operations` as an injected Protocol whose concrete composition is outside CLI parsing.
- `src/youtube_intel/cli.py:65` documents `_UnavailableOperations` as fail-closed until an explicit composition root supplies services; each non-doctor method returns a failed prerequisite result.

The known direct Adapter methods are intentionally lower-level (`YtDlpMetadataProvider.fetch`, `YtDlpSubtitleAdapter.enumerate_tracks`, and `YtDlpSubtitleAdapter.read_track`). Calling them from a temporary script would bypass the required project entry and would not exercise the requested temporary SQLite/DATA/test-Vault run boundary. It was therefore not used.

## Temporary-resource boundary

No execution began, so no temporary SQLite database, DATA directory, test Vault, configuration, product log, or transcript artifact was created. This avoids falsely implying an application run or a safe production composition when the authorized entry point is unavailable.

## Stop condition and decision needed

Stop condition: the existing CLI/configuration cannot confine the requested real smoke to the approved read-only operation sequence and isolated runtime roots.

`DECISION NEEDED`: authorize a dedicated, production-owned composition/command whose public surface is limited to one explicit video ID and performs only metadata fetch, subtitle discovery, and at most one selected subtitle-body read using caller-supplied temporary SQLite/DATA/test-Vault roots; or explicitly authorize a different existing project entry. This Phase B-1 executor must not create that entry point or use an ad-hoc substitute.

## Unclosed release gates

- `mutagen` GPL-2.0-or-later distribution treatment remains unclosed.
- `o200k_base.tiktoken` file-level attribution/license/NOTICE remains unclosed.
- Real Vault boundary verification, at-most-once best-effort risk sign-off, and PO/TL/QA final Go/No-Go remain unclosed.
