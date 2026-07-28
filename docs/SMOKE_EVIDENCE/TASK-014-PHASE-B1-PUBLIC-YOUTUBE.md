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
