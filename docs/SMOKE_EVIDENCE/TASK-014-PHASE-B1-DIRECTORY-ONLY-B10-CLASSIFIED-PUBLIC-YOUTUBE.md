# TASK-014 Phase B-1 — B10-classified directory-only public YouTube evidence

- Date: `2026-07-29`
- Source branch: `codex/task-014-phase-b1-directory-only-b10-execution`
- Pre-execution source HEAD: `f00aa9cffa25dcb9b7165edf21a4d476263c1dc5`
- Fixed video ID: `eIho2S0ZahI`
- Result: `FAIL — INVALID_RESPONSE`
- Release decision: `No-Go` unchanged; TASK-014 remains `IN_PROGRESS` and
  TASK-014B10 remains `DONE`.

## Preconditions

- Branch, HEAD, index, and tracked worktree matched the fixed assignment and
  were clean.
- Dynamic main authorization matched
  `80aff83fc033a8bd2950108cad2e34feea5d396f`; the formal execution package
  matched the package authorized by that commit.
- `uv lock --check`, `uv sync --locked --offline`, and the second
  `uv lock --check` each ran exactly once, in that order, and passed. No
  download or network indication appeared, and `uv.lock` remained unchanged.
- The fixed absolute launcher was statically verified as a regular executable
  file. Its launcher body, project script metadata, and installed entry-point
  metadata all mapped `youtube-intel` to `youtube_intel.cli:main`.
- A fresh temporary parent was created. Its `smoke-root` child did not exist as
  a file, directory, or symbolic link before the call. No temporary absolute
  path is retained in this evidence.

## Safe execution summary

| Field | Actual result |
|---|---|
| Product call | `RUN — exactly once` |
| Exit code | `1` |
| `metadata` | `1` |
| `enumerate` | `1` |
| `read` | `0` |
| Safe error code | `INVALID_RESPONSE` |
| `directory_diagnostic` | `directory_shape_unknown` |
| `directory_origin` | `directory_origin_mapping` |
| `directory_fingerprint` | `directory_fingerprint_unknown` |
| `content_availability` | 未产生；ADR-020 `CONTENT_UNAVAILABLE` 出口未满足，不作推断 |
| `directory_key_names` | 未产生；不保存或推断任何键名 |
| Retry | `0` |

The `metadata=1 / enumerate=1 / read=0` ceiling was respected. No subtitle body
was read. Because no B10 `content_availability` value was produced, this
evidence does not classify the result as video-unavailable,
environment-restricted, extractor-compatibility, or unknown. The safe action is
to stop without retry and preserve `No-Go`; no cause is inferred from the B6/B7
diagnostics.

## Prohibited-action check

- No second product call, retry, alternate video ID, additional ID, loop,
  concurrency, alternate launcher, module invocation, PATH change, venv
  activation, help call, or extra product diagnostic was performed.
- No login, authentication material, credential source, media download,
  subtitle-body download, ffmpeg, model, Ollama, OpenAI, paid/cloud service,
  real Vault, user note, user data, launchd action, or other real resource was
  accessed.
- The sole real-resource action was the one authorized directory-only YouTube
  product call. No raw response, raw stdout/stderr, URL, title, language, track,
  field value, exception text, payload, credential material, or temporary path
  is retained here.
- No product code, test, dependency, lockfile, Schema/migration, configuration,
  CLI, logging schema, ADR, task state, or control-plane file was changed.

## Scope and reuse

- Reuse decision: `DIRECT` — the integrated B4 directory-only entry, B5 safe
  summary, B6/B7/B8 fixed diagnostics, B10 fixed availability outlet, locked
  `youtube_intel.cli:main` console entry, and existing release-evidence
  documents were used without modification.
- No dependency, third-party source, or license record changed. Existing locked
  `yt-dlp==2026.7.4` reuse and license evidence remains in
  `docs/REUSE_REGISTER.md` and the release materials.
- The evidence-only change is limited to this file,
  `docs/RELEASE_CHECKLIST.md`, and `handoffs/TASK-014.md`.
