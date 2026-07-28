# TASK-014 Phase B-1 — Public YouTube Subtitle Smoke Retry Evidence

- Executor: `Codex Smoke Retry Executor`
- Source: `codex/task-014-phase-b1-console-entry-retry@49869c6ff2bbc53673c6a35071c5f1407c269cba`
- Attempted at: `2026-07-28T05:57:50Z`
- Reuse decision: `DIRECT` — existing locked dependencies, yt-dlp Adapter, and integrated `youtube-intel` console entry; no dependency or third-party-code change.
- Overall result: `BLOCKED — command entry unavailable on PATH before product execution`.

## Controlled pre-provisioning

| Step | Result | Evidence |
|---|---|---|
| Pre-provision `uv lock --check` | PASS | Resolved 84 locked packages; no lockfile or dependency change. |
| Single `uv sync --locked` | PASS | Installed only existing `uv.lock` packages, including the previously missing `fsspec==2026.6.0`; no dependency resolution or lockfile change. |
| Post-provision `uv lock --check` | PASS | Resolved the same 84 locked packages. |

## One authorized smoke invocation

The executor created one new empty temporary root and invoked exactly once:

```text
youtube-intel smoke-public-subtitles --temporary-root <new-empty-temporary-root> --video-id=--khbXchTeE --video-id=JTxsNm9IdYU
```

The shell returned `command not found: youtube-intel` with exit status `127`. The integrated product entry did not start. In accordance with the one-attempt boundary, no alternate executable path, activation step, retry, replacement target, or additional product command was run.

| Fixed video ID | Actually called | Metadata reads | Subtitle-directory reads | Subtitle-body reads | Result / stop condition |
|---|---:|---:|---:|---:|---|
| `--khbXchTeE` | No | 0 | 0 | 0 | Product entry was unavailable on PATH before any Adapter call. |
| `JTxsNm9IdYU` | No | 0 | 0 | 0 | Product entry was unavailable on PATH before any Adapter call. |

## Boundary and non-execution record

- No YouTube request, metadata payload, subtitle-directory payload, subtitle body, URL, credential, Cookie, API key, `.env`, Keychain, real Vault, user data, media, ffmpeg, model, Ollama, OpenAI, paid call, or launchd action was accessed or used.
- No media, audio, or video download occurred. No retry, loop, parallel fan-out, `retry` command, or second smoke invocation occurred.
- Temporary absolute paths and all temporary-root contents are intentionally excluded from this evidence.
- This blocked result is not B-1 smoke success, release approval, a `mutagen` GPL decision, BPE resource attribution/NOTICE conclusion, true-Vault-boundary closure, at-most-once risk acceptance, or PO/TL/QA Go/No-Go.

## Follow-up boundary

Any future smoke requires a new explicit authorization package and a new one-attempt allocation. This executor must not rerun the smoke under a different command path.

## Final venv console-path retry — 2026-07-28

- Authorization source: `codex/task-014-phase-b1-console-entry-retry@3c3dd4ac45cb6ea66bc927a1542c4612554a56fa`, whose sole parent is `49869c6ff2bbc53673c6a35071c5f1407c269cba`; the worktree was clean before this attempt.
- Launcher verification: PASS. The only permitted absolute launcher existed, was executable, and its static contents import `main` from `youtube_intel.cli`, then call `sys.exit(main())`. No `--help`, module entry, bare command, PATH change, venv activation, `uv`, installation, download, or alternate entry was used.
- At `2026-07-28T06:11:20Z` evidence capture, the one new temporary root from the one permitted invocation existed but was empty: no SQLite, DATA, test-Vault, log, or JSONL artifact was initialized. The invocation emitted no stdout/stderr. Its numeric exit status was not retained in the command transcript; this record therefore does not infer success from the lack of output.

The absolute launcher was invoked exactly once with the fixed order and IDs:

```text
/Users/hua/Documents/yia-worktrees/task-014-phase-b1-console-entry-retry/.venv/bin/youtube-intel smoke-public-subtitles --temporary-root <new-empty-temporary-root> --video-id=--khbXchTeE --video-id=JTxsNm9IdYU
```

| Fixed video ID | Actually reached smoke Adapter | Metadata reads | Subtitle-directory reads | Subtitle-body reads | Result / stop condition |
|---|---:|---:|---:|---:|---|
| `--khbXchTeE` | No | 0 | 0 | 0 | The new root remained uninitialized after the sole console-path invocation. |
| `JTxsNm9IdYU` | No | 0 | 0 | 0 | The new root remained uninitialized after the sole console-path invocation. |

- Result: `BLOCKED — the sole permitted absolute console-path invocation did not initialize the smoke runner; no public-resource call is evidenced.` No retry, substitution, secondary command, PATH change, or temporary-root replacement occurred.
- Not accessed or used: login, Cookie, browser profile, API key, `.env`, Keychain, credential, real Vault, user data, media, ffmpeg, Whisper/model, Ollama, OpenAI, paid call, launchd, metadata payload, subtitle-directory payload, subtitle body, or temporary URL.
- This final retry is not B-1 success, release approval, a `mutagen` GPL decision, BPE attribution/NOTICE conclusion, real-Vault-boundary closure, at-most-once risk acceptance, or a PO/TL/QA Go/No-Go.

## Final non-existing temporary-root retry — 2026-07-28

- Authorization source: `codex/task-014-phase-b1-console-entry-retry@365c8fca966a3fb7608f41b2d3ac530504193c7b`, with required sole parent `3c3dd4ac45cb6ea66bc927a1542c4612554a56fa`; the source worktree was clean before execution.
- Reuse decision: `DIRECT` — the previously verified project venv launcher, integrated smoke entry, and locked yt-dlp Adapter. No dependency, lockfile, source, test, configuration, Schema/migration, task-status, LICENSE, or third-party-code change was made.
- Preparation: PASS. A new temporary parent directory was created; immediately before execution, the parent existed and its `smoke-root` child path did not exist as a file, directory, or symlink. The absolute parent/root paths are intentionally not committed.

The only permitted launcher was invoked exactly once with the fixed order and IDs:

```text
/Users/hua/Documents/yia-worktrees/task-014-phase-b1-console-entry-retry/.venv/bin/youtube-intel smoke-public-subtitles --temporary-root <new-parent>/smoke-root --video-id=--khbXchTeE --video-id=JTxsNm9IdYU
```

| Fixed video ID | Actually called | Metadata reads | Subtitle-directory reads | Subtitle-body reads | Result / stop condition |
|---|---:|---:|---:|---:|---|
| `--khbXchTeE` | Yes | 1 | 1 | 0 | `INVALID_RESPONSE`; runner stopped this target before body selection/read. |
| `JTxsNm9IdYU` | Yes | 1 | 1 | 0 | `INVALID_RESPONSE`; runner stopped this target before body selection/read. |

- Runner initialization: PASS. The new root was initialized with isolated SQLite, DATA, empty test-Vault, and log directories.
- Numerical exit code: `1`. The redacted smoke ledger records `targets=2 failed=2`; the two target failures occurred at `2026-07-28T06:23:48Z` and `2026-07-28T06:23:52Z` respectively.
- Stop condition: each fixed ID received its single permitted attempt. No retry, loop, concurrency, target substitution, alternative launcher, PATH/venv change, module entry, `uv`, download, or additional product command was used.
- Not accessed or used: login, Cookie, browser profile, API key, `.env`, Keychain, credential, real Vault, user data, media, ffmpeg, Whisper/model, Ollama, OpenAI, paid call, launchd, subtitle body, temporary URL, or payload content.
- Result: `FAIL — B-1 public subtitle smoke did not complete because both permitted targets returned INVALID_RESPONSE before a subtitle body read.` This failure is not release approval, a `mutagen` GPL decision, BPE attribution/NOTICE conclusion, real-Vault-boundary closure, at-most-once risk acceptance, or PO/TL/QA Go/No-Go.
