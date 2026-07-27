# TASK-014 Phase B-1 — Public YouTube Subtitle Smoke Evidence

- Executor: `Codex` (authorized B-1 smoke executor)
- Time window: `2026-07-27T11:29:19+08:00`
- Intended entry: `youtube-intel smoke-public-subtitles`
- Reuse decision: `DIRECT` — the already integrated project CLI and locked yt-dlp Adapter only; no new dependency or third-party code.
- Verdict: **NOT EXECUTED / NO PASS RESULT**. This is not a release approval, legal conclusion, risk acceptance, or final Go.

## Fixed candidate list and selection record

The maximum was fixed at two IDs before attempting the entry. No candidate was replaced or added.

| Video ID | Intended public URL | Declared channel affiliation | Stability rationale | Target call result |
|---|---|---|---|---|
| `--khbXchTeE` | `https://www.youtube.com/watch?v=--khbXchTeE` | OpenAI official YouTube channel (historical product-announcement selection) | A long-lived public product announcement, rather than a live stream or personal upload. | Not called. |
| `JTxsNm9IdYU` | `https://www.youtube.com/watch?v=JTxsNm9IdYU` | OpenAI official YouTube channel (historical product-announcement selection) | A long-lived public product announcement, rather than a live stream or personal upload. | Not called. |

The intended affiliation/public status was not independently fetched: the authorization allows public-resource reads only through the integrated smoke entry, and the entry never became runnable. Therefore this record does not assert runtime confirmation of either target's current availability or channel metadata.

## Authorized-boundary preflight

- The integrated entry was inspected before execution: it accepts only a new absolute temporary root and 1–3 explicit IDs, creates only temporary SQLite/DATA/test-Vault/log directories, and sequences one metadata read, one subtitle-directory read, and one selected subtitle-body read per ID.
- The planned process used a cleared environment containing only executable-path and non-secret temporary-runtime variables. It supplied no login, Cookie, API key, `.env`, browser profile, Keychain value, user data, or Vault path.
- No media download, ffmpeg, Whisper, model, Ollama, OpenAI, paid service, launchd action, `retry`, concurrent fan-out, or candidate substitution was requested.

## Execution record and stop condition

| Attempt | Command category | Result | Target effects |
|---|---|---|---|
| 1 | Offline/no-sync invocation of the installed `youtube-intel smoke-public-subtitles` entry | Stopped before project CLI dispatch: the worktree had no installed `youtube-intel` script (`exit 2`). | No temporary smoke root; neither ID was called. |
| 2 | Cleared-environment, offline/no-dev invocation of `python -m youtube_intel smoke-public-subtitles` using an isolated temporary runtime environment | Stopped before module/CLI dispatch: offline resolution could not find `fsspec==2026.6.0` in cache. The resolver reported the locked path `mlx-whisper -> torch -> fsspec` and refused the disabled-network download (`exit 1`). | No temporary smoke root, SQLite, DATA, test Vault, audit JSONL, metadata call, subtitle-directory call, or subtitle-body read; neither ID was called. |

Stop condition: the required project entry cannot be made runnable from the approved offline resources. Installing or resolving the missing package from the network would exceed this B-1 run authorization. Per the single-run/no-retry boundary, execution stopped without a third invocation, dependency installation, network fallback, or target replacement.

## Result and remaining gates

- Result counts: selected `2`; executed target attempts `0`; metadata reads `0`; subtitle-directory reads `0`; subtitle-body reads `0`; successful targets `0`; failed target calls `0`.
- No subtitle text, metadata payload, audit JSONL, credentials, user content, real Vault content, or temporary application artifact was committed. The test Vault was never created because the entry did not dispatch.
- Temporary interpreter/cache artifacts from the failed launcher preflight were isolated outside the repository and not retained as evidence or committed. The worktree contains no generated runtime directory.
- **DECISION NEEDED:** PO/TL must authorize a pre-provisioned, offline-complete runtime for a new B-1 execution window, or explicitly authorize the otherwise prohibited dependency-resolution/install path. The current result leaves TASK-014 `IN_PROGRESS` / `No-Go`; existing mutagen GPL, BPE attribution/NOTICE, at-most-once risk-signoff, real-Vault boundary, and final PO/TL/QA Go-No-Go gates remain open.

## Phase B-1 Retry — controlled pre-provisioning and single integrated-entry attempt

- Execution date: `2026-07-27`.
- Reuse decision: `DIRECT` — the already integrated project CLI, locked dependency set, and yt-dlp Adapter only; no third-party code or dependency was added, copied, upgraded, or changed.
- Verdict: **NOT PASSED / NO TARGET CALLS**. This retry is not a release approval, legal conclusion, risk acceptance, or final Go.

### Authorized environment pre-provisioning

| Ordered action | Result | Boundary evidence |
|---|---|---|
| `uv lock --check` (pre) | PASS | The committed lock resolved 84 packages; no lock or project metadata change was made. |
| `uv sync --locked` (once) | PASS | Created the local virtual environment and installed only packages already pinned by `uv.lock`, including the formerly missing `fsspec==2026.6.0`; no dependency resolution, version change, source change, or lockfile write occurred. |
| `uv lock --check` (post) | PASS | The committed lock again resolved 84 packages after provisioning. |

### Fixed targets and one allowed smoke-entry attempt

The retry retained exactly the original two fixed IDs and their recorded selection rationale. Neither was substituted, reordered, or expanded.

| Video ID | Integrated-entry result | Metadata reads | Subtitle-directory reads | Selected-body reads |
|---|---|---:|---:|---:|
| `--khbXchTeE` | Not called. | 0 | 0 | 0 |
| `JTxsNm9IdYU` | Not called. | 0 | 0 | 0 |

After all three provisioning steps passed, the executor made the one authorized `youtube-intel smoke-public-subtitles` invocation with both fixed IDs, a new previously nonexistent absolute temporary root, and a cleared non-secret runtime environment. The shell stopped before project CLI dispatch with `env: youtube-intel: No such file or directory`.

The resulting virtual environment contains no `youtube-intel` console script. Therefore the entry did not create the temporary root, SQLite, DATA directory, test Vault, or audit JSONL, and it did not read metadata, enumerate subtitles, or retain a subtitle body. No login, Cookie, browser profile, API key, `.env`, Keychain value, media download, ffmpeg, model, Ollama, OpenAI, paid service, real Vault, user data, retry command, concurrent fan-out, or additional product command was used.

### Stop condition and remaining gates

- Result counts: selected `2`; integrated smoke invocations `1`; project CLI dispatches `0`; target attempts `0`; metadata reads `0`; subtitle-directory reads `0`; subtitle-body reads `0`; successful targets `0`; target failures `0`.
- Stop condition: the exact integrated console entry required by the authorization is absent after the one allowed locked sync. Running an alternative module entry, adding a console-script declaration, or re-running smoke would exceed this retry authorization.
- **DECISION NEEDED:** PO/TL must provide a new, explicit execution window that resolves the missing integrated console entry without weakening the one-attempt/resource boundaries. TASK-014 remains `IN_PROGRESS` / `No-Go`; mutagen GPL distribution, BPE attribution/NOTICE, real-Vault boundary, at-most-once best-effort risk signature, and final PO/TL/QA Go-No-Go remain open.
